"""
WordPress Publisher Module

Publishes draft articles to WordPress as draft posts via the REST API.
Supports Yoast SEO meta fields (title, description, focus keyphrase).
"""

import os
import re
import socket
import ssl
import subprocess
import time
import urllib3
import requests
from requests.adapters import HTTPAdapter
from typing import Dict, Optional, List, Tuple
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class _SSHTunnelAdapter(HTTPAdapter):
    """HTTPAdapter that uses the real domain for SSL SNI while connecting to an SSH tunnel IP."""

    def __init__(self, real_hostname: str, *args, **kwargs):
        self._real_hostname = real_hostname
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, num_pools, maxsize, block=False):
        self.poolmanager = urllib3.PoolManager(
            num_pools=num_pools,
            maxsize=maxsize,
            block=block,
            server_hostname=self._real_hostname,
            cert_reqs=ssl.CERT_NONE,
            assert_hostname=False,
        )


class WordPressPublisher:
    """WordPress REST API client for publishing drafts"""

    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        app_password: Optional[str] = None,
        ssh_config: Optional[dict] = None,
    ):
        """
        Initialize WordPress publisher

        Args:
            url: WordPress site URL (defaults to env var WORDPRESS_URL)
            username: WordPress username (defaults to env var WORDPRESS_USERNAME)
            app_password: Application password (defaults to env var WORDPRESS_APP_PASSWORD)
            ssh_config: Optional SSH config dict with keys: user, host, port, key, wp_path.
                        When present with wp_path, publish_html_content() routes through
                        WP-CLI over SSH, bypassing SiteGround CDN/WAF bot protection.
        """
        real_url = (url or os.getenv('WORDPRESS_URL', '')).rstrip('/')
        self.username = username or os.getenv('WORDPRESS_USERNAME')
        self.app_password = app_password or os.getenv('WORDPRESS_APP_PASSWORD')

        if not real_url:
            raise ValueError("WORDPRESS_URL must be set")
        if not self.username or not self.app_password:
            raise ValueError("WORDPRESS_USERNAME and WORDPRESS_APP_PASSWORD must be set")

        self._display_url = real_url  # used for edit URLs shown to the user
        self._ssh_config = ssh_config or {}

        self.url = real_url
        self.session = requests.Session()
        self.session.auth = (self.username, self.app_password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'SEOMachine/1.0 (WordPress Content Publisher)'
        })
        if '.local' in self.url or 'staging' in self.url:
            self.session.verify = False

        self.api_base = f"{self.url}/wp-json/wp/v2"

        # Cache for categories and tags
        self._categories_cache: Optional[Dict[str, int]] = None
        self._tags_cache: Optional[Dict[str, int]] = None

    @classmethod
    def from_config(cls, wp_config: dict, ssh_config: Optional[dict] = None) -> 'WordPressPublisher':
        """Create a publisher instance from a client config dict.

        Pass ssh_config to route all requests via SSH tunnel (bypasses SiteGround CDN/WAF).
        """
        return cls(
            url=wp_config.get('url'),
            username=wp_config.get('username'),
            app_password=wp_config.get('app_password'),
            ssh_config=ssh_config,
        )

    # ------------------------------------------------------------------ #
    # WP-CLI / SSH publish path                                           #
    # Used when direct HTTP is blocked (e.g. SiteGround CDN bot filter)  #
    # ------------------------------------------------------------------ #

    def _ssh_run(self, cmd: str, timeout: int = 30) -> tuple:
        """Run a shell command on the remote server. Returns (stdout, returncode)."""
        cfg = self._ssh_config
        key = str(Path(cfg['key'].replace('~', str(Path.home()))).resolve())
        result = subprocess.run(
            ['ssh', '-i', key, '-p', str(cfg.get('port', 22)),
             '-o', 'StrictHostKeyChecking=no', '-o', 'BatchMode=yes',
             f"{cfg['user']}@{cfg['host']}", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout.strip(), result.returncode

    def _scp_put(self, local_path: str, remote_path: str, timeout: int = 60):
        """Copy a local file to the remote server via SCP."""
        cfg = self._ssh_config
        key = str(Path(cfg['key'].replace('~', str(Path.home()))).resolve())
        subprocess.run(
            ['scp', '-i', key, '-P', str(cfg.get('port', 22)),
             '-o', 'StrictHostKeyChecking=no',
             local_path, f"{cfg['user']}@{cfg['host']}:{remote_path}"],
            check=True, capture_output=True, timeout=timeout,
        )

    def _publish_via_wpcli(
        self,
        title: str,
        slug: str,
        post_type: str,
        excerpt: str,
        html_content: str,
        elementor_template_path: Optional[str] = None,
        featured_image_path: Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict:
        """Publish a post via WP-CLI over SSH.

        Workflow:
          1. Create bare WP draft post via wp post create
          2. Upload images via SCP + wp media import; rewrite src URLs in content
          3. Inject into Elementor template (local); transfer JSON via SCP
          4. Apply Elementor data + meta via wp eval / wp post meta update
          5. Clean up temp files
        """
        import json as _json
        import tempfile

        wp_path = self._ssh_config.get('wp_path', '')
        if not wp_path:
            raise ValueError("ssh_config must include 'wp_path' for WP-CLI publishing")
        wp = f"wp --path={wp_path} --allow-root"
        ts = int(time.time())
        remote_dir = f'/tmp/seomachine_{ts}'

        self._ssh_run(f'mkdir -p {remote_dir}')

        # 1. Create the bare draft post
        title_safe = title.replace("'", "'\\''")
        excerpt_safe = excerpt.replace("'", "'\\''")
        create_cmd = (
            f"{wp} post create "
            f"--post_type='{post_type}' "
            f"--post_status=draft "
            f"--post_title='{title_safe}' "
            f"--post_slug='{slug}' "
            f"--post_content='' "
            f"--post_excerpt='{excerpt_safe}' "
            f"--porcelain"
        )
        post_id_str, rc = self._ssh_run(create_cmd, timeout=30)
        if rc != 0 or not post_id_str.strip().isdigit():
            raise RuntimeError(f"wp post create failed (rc={rc}): {post_id_str}")
        post_id = int(post_id_str.strip())
        print(f"    → WP-CLI created draft post {post_id}")

        # 2. Upload images; rewrite src URLs in content
        featured_media_id = None
        if featured_image_path and Path(featured_image_path).exists():
            article_dir = Path(featured_image_path).parent
            local_imgs = re.findall(r'<img[^>]+src="([^"]+)"', html_content)
            for src in local_imgs:
                if src.startswith('http'):
                    continue
                local_path = article_dir / src
                if not local_path.exists():
                    continue
                remote_img = f'{remote_dir}/{local_path.name}'
                try:
                    self._scp_put(str(local_path), remote_img)
                    img_title = local_path.stem
                    flag = '--featured_image' if local_path.name == Path(featured_image_path).name else ''
                    out, rc = self._ssh_run(
                        f"{wp} media import '{remote_img}' --post_id={post_id} "
                        f"--title='{img_title}' {flag} --porcelain",
                        timeout=30,
                    )
                    if rc == 0 and out.strip().isdigit():
                        media_id = int(out.strip())
                        if flag:
                            featured_media_id = media_id
                        # Resolve absolute URL for src replacement
                        url_out, _ = self._ssh_run(
                            f"{wp} post get {media_id} --field=guid"
                        )
                        if url_out:
                            html_content = html_content.replace(f'src="{src}"', f'src="{url_out.strip()}"')
                            # Replace schema token with banner URL
                            if flag:
                                html_content = html_content.replace('[BANNER_IMAGE_URL]', url_out.strip())
                        print(f"    → WP-CLI imported {local_path.name} → media {media_id}")
                except Exception as e:
                    print(f"    Warning: image upload failed ({local_path.name}) — {e}")
        html_content = html_content.replace('[BANNER_IMAGE_URL]', '')

        # 3. Resolve / create category
        if category:
            cat_check, rc = self._ssh_run(
                f"{wp} term get category '{category.replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}' "
                f"--field=term_id 2>/dev/null"
            )
            if rc != 0 or not cat_check.strip().isdigit():
                cat_check, _ = self._ssh_run(
                    f"{wp} term create category '{category.replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}' --porcelain"
                )
            if cat_check.strip().isdigit():
                cat_id = int(cat_check.strip())
                self._ssh_run(f"{wp} post term set {post_id} category {cat_id}")

        # 4. Inject into Elementor template and apply via wp eval
        if elementor_template_path and Path(elementor_template_path).exists():
            template_dict = self._inject_elementor(html_content, elementor_template_path)
            elementor_json = _json.dumps(template_dict, ensure_ascii=False)
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w', encoding='utf-8') as f:
                f.write(elementor_json)
                local_json = f.name
            remote_json = f'{remote_dir}/elementor.json'
            try:
                self._scp_put(local_json, remote_json)
                self._ssh_run(
                    f"{wp} eval \"update_post_meta({post_id}, '_elementor_data', "
                    f"wp_slash(file_get_contents('{remote_json}')));\""
                )
                self._ssh_run(
                    f"{wp} post meta update {post_id} _elementor_edit_mode 'builder'"
                )
                print(f"    → WP-CLI applied Elementor data")
            finally:
                Path(local_json).unlink(missing_ok=True)
        else:
            # Non-Elementor: update post content directly
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as f:
                f.write(html_content)
                local_html = f.name
            remote_html = f'{remote_dir}/content.html'
            try:
                self._scp_put(local_html, remote_html)
                self._ssh_run(
                    f"{wp} eval \"wp_update_post(['ID'=>{post_id},"
                    f"'post_content'=>file_get_contents('{remote_html}')]);\" "
                )
            finally:
                Path(local_html).unlink(missing_ok=True)

        # 5. Clean up temp files
        self._ssh_run(f'rm -rf {remote_dir}')

        edit_url = f"{self._display_url}/wp-admin/post.php?post={post_id}&action=edit"
        return {
            'post_id': post_id,
            'post_type': post_type,
            'edit_url': edit_url,
            'view_url': '',
            'title': title,
            'slug': slug,
        }

    def _parse_frontmatter(self, content: str) -> dict:
        """Extract YAML-style frontmatter fields (--- key: value --- block)."""
        match = re.match(r'^---\n(.+?)\n---', content, re.DOTALL)
        if not match:
            return {}
        fields = {}
        for line in match.group(1).splitlines():
            if ':' in line:
                key, _, value = line.partition(':')
                fields[key.strip().lower().replace(' ', '_')] = value.strip()
        return fields

    def _find_first_image(self, content: str, base_dir: Optional[Path] = None) -> Optional[str]:
        """Find the first local image path referenced in markdown content."""
        for match in re.findall(r'!\[.*?\]\(([^)]+)\)', content):
            if match.startswith('http'):
                continue
            candidate = Path(match)
            if base_dir:
                candidate = base_dir / match
            if candidate.exists():
                return str(candidate)
        return None

    def upload_media(self, image_path: str) -> tuple:
        """Upload an image to the WordPress media library. Returns (media_id, source_url)."""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        suffix = path.suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png', '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        content_type = mime_types.get(suffix, 'image/jpeg')

        with open(path, 'rb') as f:
            response = self.session.post(
                f"{self.api_base}/media",
                headers={
                    'Content-Disposition': f'attachment; filename="{path.name}"',
                    'Content-Type': content_type,
                },
                data=f,
            )
        response.raise_for_status()
        data = response.json()
        return data['id'], data['source_url']

    def set_featured_image(self, post_id: int, media_id: int, post_type: str = 'posts') -> None:
        """Set the featured image (thumbnail) on a post."""
        response = self.session.post(
            f"{self.api_base}/{post_type}/{post_id}",
            json={'featured_media': media_id},
        )
        response.raise_for_status()

    def parse_draft_file(self, file_path: str) -> Dict:
        """
        Parse a markdown draft file and extract metadata and content

        Args:
            file_path: Path to the markdown file

        Returns:
            Dict with keys: title, meta_title, meta_description, target_keyword,
                           secondary_keywords, slug, category, tags, content
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Draft file not found: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Try YAML frontmatter first, fall back to **Field**: value format
        fm = self._parse_frontmatter(content)

        # Extract H1 title
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = h1_match.group(1).strip() if h1_match else fm.get('title', '')

        # Extract metadata fields — prefer frontmatter, then **Field**: value
        def extract_field(field_name: str, fm_key: str = '') -> str:
            fm_key = fm_key or field_name.lower().replace(' ', '_')
            if fm.get(fm_key):
                return fm[fm_key]
            pattern = rf'\*\*{field_name}\*\*:\s*(.+?)(?:\n|$)'
            match = re.search(pattern, content, re.IGNORECASE)
            return match.group(1).strip() if match else ''

        meta_title = extract_field('Meta Title', 'meta_title')
        meta_description = extract_field('Meta Description', 'meta_description')
        target_keyword = extract_field('Target Keyword', 'target_keyword')
        secondary_keywords = extract_field('Secondary Keywords', 'secondary_keywords')
        category = extract_field('Category', 'category')
        tags = extract_field('Tags', 'tags')
        featured_image = extract_field('Featured Image', 'featured_image')

        # Extract URL slug - handle both formats
        slug = ''
        slug_match = re.search(r'\*\*URL Slug\*\*:\s*/?(?:blog/)?([^\s/]+)/?', content, re.IGNORECASE)
        if slug_match:
            slug = slug_match.group(1).strip()
        else:
            # Generate from title if not specified
            slug = re.sub(r'[^\w\s-]', '', title.lower())
            slug = re.sub(r'[\s_]+', '-', slug)

        # Remove metadata section from content for body
        # Content starts after the metadata block (after the first ---)
        body_content = content

        # Remove the H1 title
        body_content = re.sub(r'^#\s+.+\n', '', body_content, count=1)

        # Remove metadata lines
        metadata_patterns = [
            r'\*\*Meta Title\*\*:.+\n?',
            r'\*\*Meta Description\*\*:.+\n?',
            r'\*\*Target Keyword\*\*:.+\n?',
            r'\*\*Secondary Keywords\*\*:.+\n?',
            r'\*\*URL Slug\*\*:.+\n?',
            r'\*\*Category\*\*:.+\n?',
            r'\*\*Tags\*\*:.+\n?',
            r'\*\*Internal Links\*\*:.+\n?',
            r'\*\*External Links\*\*:.+\n?',
            r'\*\*Word Count\*\*:.+\n?',
        ]
        for pattern in metadata_patterns:
            body_content = re.sub(pattern, '', body_content, flags=re.IGNORECASE)

        # Remove leading/trailing horizontal rules and whitespace
        body_content = re.sub(r'^[\s\-]*\n', '', body_content)
        body_content = body_content.strip()

        return {
            'title': title,
            'meta_title': meta_title or title,
            'meta_description': meta_description,
            'target_keyword': target_keyword,
            'secondary_keywords': secondary_keywords,
            'slug': slug,
            'category': category,
            'tags': tags,
            'featured_image': featured_image,
            'content': body_content
        }

    def markdown_to_html(self, markdown_content: str) -> str:
        """
        Convert markdown to HTML for WordPress

        Args:
            markdown_content: Markdown formatted content

        Returns:
            HTML formatted content
        """
        try:
            import markdown
            md = markdown.Markdown(extensions=['extra', 'nl2br', 'sane_lists'])
            return md.convert(markdown_content)
        except ImportError:
            # Fallback: basic markdown conversion
            html = markdown_content

            # Convert headers
            html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
            html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
            html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

            # Convert bold and italic
            html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
            html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

            # Convert links
            html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

            # Convert unordered lists
            html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

            # Wrap paragraphs
            paragraphs = html.split('\n\n')
            wrapped = []
            for p in paragraphs:
                p = p.strip()
                if p and not p.startswith('<'):
                    wrapped.append(f'<p>{p}</p>')
                else:
                    wrapped.append(p)
            html = '\n\n'.join(wrapped)

            return html

    def get_categories(self) -> Dict[str, int]:
        """Get all categories as name->ID mapping"""
        if self._categories_cache is not None:
            return self._categories_cache

        categories = {}
        page = 1
        while True:
            response = self.session.get(
                f"{self.api_base}/categories",
                params={'per_page': 100, 'page': page}
            )
            response.raise_for_status()
            items = response.json()
            if not items:
                break
            for cat in items:
                categories[cat['name'].lower()] = cat['id']
            page += 1

        self._categories_cache = categories
        return categories

    def get_tags(self) -> Dict[str, int]:
        """Get all tags as name->ID mapping"""
        if self._tags_cache is not None:
            return self._tags_cache

        tags = {}
        page = 1
        while True:
            response = self.session.get(
                f"{self.api_base}/tags",
                params={'per_page': 100, 'page': page}
            )
            response.raise_for_status()
            items = response.json()
            if not items:
                break
            for tag in items:
                tags[tag['name'].lower()] = tag['id']
            page += 1

        self._tags_cache = tags
        return tags

    def get_or_create_category(self, name: str) -> int:
        """Get category ID, creating if it doesn't exist"""
        categories = self.get_categories()
        name_lower = name.lower().strip()

        if name_lower in categories:
            return categories[name_lower]

        # Create new category
        response = self.session.post(
            f"{self.api_base}/categories",
            json={'name': name.strip()}
        )
        response.raise_for_status()
        new_cat = response.json()
        self._categories_cache[name_lower] = new_cat['id']
        return new_cat['id']

    def get_or_create_tag(self, name: str) -> int:
        """Get tag ID, creating if it doesn't exist"""
        tags = self.get_tags()
        name_lower = name.lower().strip()

        if name_lower in tags:
            return tags[name_lower]

        # Create new tag
        response = self.session.post(
            f"{self.api_base}/tags",
            json={'name': name.strip()}
        )
        response.raise_for_status()
        new_tag = response.json()
        self._tags_cache[name_lower] = new_tag['id']
        return new_tag['id']

    @staticmethod
    def _wrap_schema_block(content: str) -> str:
        """
        Find the <!-- SCHEMA --> block in HTML content, remove it from its
        current position, wrap it in a Gutenberg wp:html block (which preserves
        <script> tags), and append it at the end of the content.

        WordPress strips <script> tags from regular post content but preserves
        them inside Custom HTML (wp:html) blocks.
        """
        schema_pattern = re.compile(
            r'<!-- SCHEMA -->\s*(<script[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>)\s*',
            re.DOTALL | re.IGNORECASE
        )
        match = schema_pattern.search(content)
        if not match:
            return content

        script_tag = match.group(1).strip()
        # Remove the schema block from its original position
        content = schema_pattern.sub('', content).rstrip()
        # Append as a Gutenberg Custom HTML block
        gutenberg_block = f'\n\n<!-- wp:html -->\n{script_tag}\n<!-- /wp:html -->'
        return content + gutenberg_block

    def create_draft(
        self,
        title: str,
        content: str,
        slug: str,
        excerpt: str = '',
        category_ids: Optional[List[int]] = None,
        tag_ids: Optional[List[int]] = None,
        post_type: str = 'posts'
    ) -> Dict:
        """
        Create a WordPress draft post, page, or custom post type

        Args:
            title: Post title
            content: HTML content
            slug: URL slug
            excerpt: Post excerpt
            category_ids: List of category IDs (posts only)
            tag_ids: List of tag IDs (posts only)
            post_type: WordPress post type endpoint ('posts', 'pages', or custom type)

        Returns:
            WordPress post response with id, link, etc.
        """
        content = self._wrap_schema_block(content)

        post_data = {
            'title': title,
            'content': content,
            'slug': slug,
            'status': 'draft',
            'excerpt': excerpt
        }

        # Categories and tags only apply to posts
        if post_type == 'posts':
            if category_ids:
                post_data['categories'] = category_ids
            if tag_ids:
                post_data['tags'] = tag_ids

        response = self.session.post(
            f"{self.api_base}/{post_type}",
            json=post_data
        )
        response.raise_for_status()
        return response.json()

    def set_yoast_meta(
        self,
        post_id: int,
        meta_title: str,
        meta_description: str,
        focus_keyphrase: str,
        post_type: str = 'posts'
    ) -> Dict:
        """
        Set Yoast SEO meta fields on a post, page, or custom post type

        Requires the SEO Machine Yoast REST plugin to be installed:
        wp-content/mu-plugins/seo-machine-yoast-rest.php

        Args:
            post_id: WordPress post ID
            meta_title: SEO title
            meta_description: Meta description
            focus_keyphrase: Focus keyphrase (target keyword)
            post_type: WordPress post type endpoint ('posts', 'pages', or custom type)

        Returns:
            Updated post response
        """
        # Use the seo_meta field provided by our mu-plugin
        yoast_data = {
            'seo_meta': {
                'seo_title': meta_title,
                'meta_description': meta_description,
                'focus_keyphrase': focus_keyphrase
            }
        }

        response = self.session.post(
            f"{self.api_base}/{post_type}/{post_id}",
            json=yoast_data
        )
        response.raise_for_status()
        return response.json()

    # ── Elementor template injection ──────────────────────────────────────────

    def _find_html_widget(self, elements: list) -> Optional[dict]:
        """Depth-first search for the HTML injection widget.

        Primary: first widget where widgetType == 'html' and settings.html
        contains 'Paste HTML Here'. Fallback: first html widget anywhere.
        """
        # First pass: look for the marked widget
        result = self._find_html_widget_marked(elements)
        if result:
            return result
        # Fallback: first html widget
        return self._find_html_widget_first(elements)

    def _find_html_widget_marked(self, elements: list, marker: str = "Paste HTML Here") -> Optional[dict]:
        for el in elements:
            if el.get("elType") == "widget" and el.get("widgetType") == "html":
                if marker in el.get("settings", {}).get("html", ""):
                    return el
            result = self._find_html_widget_marked(el.get("elements", []), marker)
            if result:
                return result
        return None

    def _find_html_widget_first(self, elements: list) -> Optional[dict]:
        for el in elements:
            if el.get("elType") == "widget" and el.get("widgetType") == "html":
                return el
            result = self._find_html_widget_first(el.get("elements", []))
            if result:
                return result
        return None

    def _inject_elementor(self, html_content: str, template_path: str) -> dict:
        """Load Elementor template JSON and inject article HTML into the HTML widget(s).

        Two-section mode (S1/S2 markers): Section 1 body goes into <!-- S1 CONTENT -->,
        Section 2 FAQ + schema go into <!-- S2 CONTENT -->.
        Single-widget mode (legacy / GTM): all content injected into one widget.
        Schema <script> is appended directly — Elementor HTML widgets preserve <script> tags.
        """
        import json as _json
        template = _json.loads(Path(template_path).read_text(encoding="utf-8"))

        # Split schema block from article HTML
        schema_pattern = re.compile(
            r'<!--\s*SCHEMA\s*-->\s*(<script[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>)',
            re.DOTALL | re.IGNORECASE,
        )
        schema_match = schema_pattern.search(html_content)
        article_html = schema_pattern.sub("", html_content).strip()
        schema_script = schema_match.group(1).strip() if schema_match else ""

        # Remove the first <h2> — template renders the page title via its own widget
        article_html = re.sub(r'<h2[^>]*>.*?</h2>\s*', '', article_html, count=1,
                               flags=re.DOTALL | re.IGNORECASE)

        # Ensure the h1 title widget in the template carries the hdr-xl class.
        # Walk the template and add css_classes to any heading widget with header_size 'h1'.
        def _add_h1_class(nodes: list) -> None:
            for node in nodes:
                if node.get('widgetType') == 'heading':
                    s = node.setdefault('settings', {})
                    if s.get('header_size') == 'h1':
                        existing = s.get('css_classes', '')
                        if 'hdr-xl' not in existing:
                            s['css_classes'] = ('hdr-xl ' + existing).strip()
                _add_h1_class(node.get('elements', []))
        _add_h1_class(template if isinstance(template, list) else [template])

        def fix_list_spacing(html: str) -> str:
            html = html.replace('<ul>', '<ul style="line-height: 1.8; margin: 0.5em 0 1em;">')
            html = html.replace('<li>', '<li style="margin-bottom: 0.4em;">')
            return html

        # Two-section mode: look for S1 and S2 markers
        w_s1 = self._find_html_widget_marked(template, "<!-- S1 CONTENT -->")
        w_s2 = self._find_html_widget_marked(template, "<!-- S2 CONTENT -->")

        if w_s1 and w_s2:
            # Split on the SECTION 2 FAQ comment
            split_pattern = re.compile(r'<!--\s*SECTION\s*2\s*FAQ\s*-->', re.IGNORECASE)
            parts = split_pattern.split(article_html, maxsplit=1)
            section1_html = fix_list_spacing(parts[0].strip())
            section2_html = fix_list_spacing(parts[1].strip()) if len(parts) > 1 else ""
            w_s1["settings"]["html"] = section1_html
            w_s2["settings"]["html"] = section2_html + ("\n\n" + schema_script if schema_script else "")
        else:
            # Legacy single-widget mode (GTM template)
            article_html = fix_list_spacing(article_html)
            widget = self._find_html_widget(template)
            if not widget:
                raise RuntimeError("No HTML widget found in Elementor template. Check elementor-template.json.")
            widget["settings"]["html"] = article_html + ("\n\n" + schema_script if schema_script else "")

        return template

    def _create_elementor_page(
        self, title: str, template_dict: dict, slug: str, excerpt: str = "", post_type: str = "seo_location",
        category_ids: Optional[List[int]] = None,
    ) -> dict:
        """Create a WordPress post/page/CPT pre-populated with an Elementor layout."""
        import json as _json
        type_endpoints = {'post': 'posts', 'page': 'pages'}
        endpoint = type_endpoints.get(post_type, post_type)
        post_data = {
            "title": title,
            "slug": slug,
            "status": "draft",
            "excerpt": excerpt,
            "meta": {
                "_elementor_data": _json.dumps(template_dict, ensure_ascii=False),
                "_elementor_edit_mode": "builder",
            },
        }
        if category_ids:
            post_data["categories"] = category_ids
        response = self.session.post(f"{self.api_base}/{endpoint}", json=post_data)
        response.raise_for_status()
        return response.json()

    def _upload_and_replace_images(
        self, html_content: str, article_dir: Path
    ) -> tuple:
        """Upload all local <img> files to WP media library and rewrite src to absolute URLs.

        Returns (updated_html, banner_media_id) where banner_media_id is the ID of the
        first image uploaded (used as the featured image).
        """
        local_srcs = re.findall(r'<img[^>]+src="([^"]+)"', html_content)
        featured_media_id = None

        for src in local_srcs:
            if src.startswith('http'):
                continue
            local_path = article_dir / src
            if not local_path.exists():
                print(f"    Warning: image not found locally — {src}")
                continue
            try:
                media_id, media_url = self.upload_media(str(local_path))
                html_content = html_content.replace(f'src="{src}"', f'src="{media_url}"')
                print(f"    → uploaded {src} → {media_url}")
                if featured_media_id is None:
                    featured_media_id = media_id
            except Exception as e:
                print(f"    Warning: failed to upload {src} — {e}")

        return html_content, featured_media_id

    def publish_html_content(
        self,
        html_content: str,
        slug: str,
        post_type: str = 'post',
        meta_title: str = '',
        meta_description: str = '',
        focus_keyphrase: str = '',
        featured_image_path: Optional[str] = None,
        elementor_template_path: Optional[str] = None,
        excerpt: str = '',
        category: str = '',
    ) -> Dict:
        """
        Publish raw HTML content (as produced by the batch runner agents) to WordPress.

        Extracts the post title from the first <h2> tag. The <!-- SCHEMA --> block,
        if present, is automatically wrapped in a Gutenberg wp:html block by create_draft.

        Args:
            html_content: Raw HTML string with <!-- SECTION 1 -->, <!-- SECTION 2 FAQ -->,
                          and optionally <!-- SCHEMA --> blocks.
            slug: URL slug for the post.
            post_type: 'post', 'page', or custom post type.
            meta_title: Yoast SEO title (optional).
            meta_description: Yoast meta description (optional).
            focus_keyphrase: Yoast focus keyphrase (optional).
            featured_image_path: Local path to an image to set as featured image (optional).

        Returns:
            Dict with post_id, edit_url, view_url, title, slug.
        """
        type_endpoints = {'post': 'posts', 'posts': 'posts', 'page': 'pages', 'pages': 'pages'}
        api_endpoint = type_endpoints.get(post_type.lower(), post_type.lower())

        # Extract title from first <h2> tag in the content
        h2_match = re.search(r'<h2[^>]*>(.*?)</h2>', html_content, re.IGNORECASE | re.DOTALL)
        title = re.sub(r'<[^>]+>', '', h2_match.group(1)).strip() if h2_match else slug.replace('-', ' ').title()
        # Titles must not contain commas or full stops
        title = title.replace(',', '').replace('.', '')

        # Inject heading classes for stylesheet targeting
        element_classes = {
            'h1': 'hdr-xl', 'h2': 'hdr-l', 'h3': 'hdr-m', 'h4': 'hdr-s', 'h5': 'hdr-xs',
            'p': 'txt-m', 'small': 'txt-s',
        }
        def _inject_element_class(m, cls):
            tag, attrs, content = m.group(1), m.group(2), m.group(3)
            class_match = re.search(r'\bclass="([^"]*)"', attrs)
            if class_match:
                return f'<{tag}{attrs}>{content}</{tag}>'  # already has a class — respect it
            attrs = f' class="{cls}"' + attrs
            return f'<{tag}{attrs}>{content}</{tag}>'
        for tag, cls in element_classes.items():
            html_content = re.sub(
                rf'<({tag})((?:\s[^>]*)?)>(.*?)</{tag}>',
                lambda m, c=cls: _inject_element_class(m, c),
                html_content, flags=re.IGNORECASE | re.DOTALL
            )

        # WP-CLI path: route through SSH when direct HTTP is blocked (e.g. SiteGround CDN)
        if self._ssh_config.get('wp_path'):
            return self._publish_via_wpcli(
                title=title,
                slug=slug,
                post_type=post_type,
                excerpt=excerpt or meta_description or '',
                html_content=html_content,
                elementor_template_path=elementor_template_path,
                featured_image_path=featured_image_path,
                category=category,
            )

        # Upload all local images and rewrite their src to absolute WordPress URLs
        # before creating the draft, so the post content has working image URLs.
        featured_media_id = None
        if featured_image_path:
            try:
                article_dir = Path(featured_image_path).parent
                html_content, featured_media_id = self._upload_and_replace_images(
                    html_content, article_dir
                )
                # Inject the banner URL into the schema [BANNER_IMAGE_URL] token.
                # The first https:// src in the content is the banner (injected first).
                banner_match = re.search(r'src="(https://[^"]+)"', html_content)
                if banner_match:
                    html_content = html_content.replace('[BANNER_IMAGE_URL]', banner_match.group(1))
            except Exception as e:
                print(f"    Warning: image upload failed — {e}")
        # Clear any unfilled token (e.g. when no images are generated)
        html_content = html_content.replace('[BANNER_IMAGE_URL]', '')

        # Resolve category if provided (auto-creates in WordPress if it doesn't exist)
        category_ids = []
        if category:
            category_ids = [self.get_or_create_category(category)]

        # Elementor path: inject HTML into the saved template layout
        if elementor_template_path and Path(elementor_template_path).exists():
            modified_template = self._inject_elementor(html_content, elementor_template_path)
            post = self._create_elementor_page(
                title, modified_template, slug,
                excerpt=excerpt or meta_description,
                post_type=post_type,
                category_ids=category_ids or None,
            )
        else:
            post = self.create_draft(
                title=title,
                content=html_content,
                slug=slug,
                excerpt=excerpt or meta_description,
                post_type=api_endpoint,
                category_ids=category_ids or None,
            )
        post_id = post['id']

        if meta_title or meta_description or focus_keyphrase:
            self.set_yoast_meta(
                post_id=post_id,
                meta_title=meta_title or title,
                meta_description=meta_description,
                focus_keyphrase=focus_keyphrase,
                post_type=api_endpoint,
            )

        if featured_media_id:
            try:
                featured_endpoint = api_endpoint
                self.set_featured_image(post_id, featured_media_id, featured_endpoint)
            except Exception as e:
                print(f"    Warning: could not set featured image — {e}")

        edit_url = f"{self._display_url}/wp-admin/post.php?post={post_id}&action=edit"
        return {
            'post_id': post_id,
            'post_type': post_type,
            'edit_url': edit_url,
            'view_url': post.get('link', ''),
            'title': title,
            'slug': slug,
        }

    def publish_draft(self, file_path: str, post_type: str = 'post') -> Dict:
        """
        Publish a draft file to WordPress as a post, page, or custom post type

        Args:
            file_path: Path to the markdown draft file
            post_type: Content type - 'post', 'page', or custom post type (e.g., 'compare')

        Returns:
            Dict with post_id, edit_url, view_url, and status information
        """
        # Map friendly names to REST API endpoints
        type_endpoints = {
            'post': 'posts',
            'posts': 'posts',
            'page': 'pages',
            'pages': 'pages',
        }
        # Use the mapping, or assume custom post types use plural form
        api_endpoint = type_endpoints.get(post_type.lower(), post_type.lower())

        # Parse the draft file
        draft = self.parse_draft_file(file_path)

        # Convert content to HTML
        html_content = self.markdown_to_html(draft['content'])
        word_count = len(draft['content'].split())

        # Process categories (only for posts)
        category_ids = []
        if api_endpoint == 'posts' and draft['category']:
            cat_names = [c.strip() for c in draft['category'].split(',')]
            for cat_name in cat_names:
                if cat_name:
                    category_ids.append(self.get_or_create_category(cat_name))

        # Process tags (only for posts)
        tag_ids = []
        if api_endpoint == 'posts' and draft['tags']:
            tag_names = [t.strip() for t in draft['tags'].split(',')]
            for tag_name in tag_names:
                if tag_name:
                    tag_ids.append(self.get_or_create_tag(tag_name))

        # Create the draft
        post = self.create_draft(
            title=draft['title'],
            content=html_content,
            slug=draft['slug'],
            excerpt=draft['meta_description'],
            category_ids=category_ids if category_ids else None,
            tag_ids=tag_ids if tag_ids else None,
            post_type=api_endpoint
        )

        post_id = post['id']

        # Set Yoast meta
        if draft['meta_title'] or draft['meta_description'] or draft['target_keyword']:
            self.set_yoast_meta(
                post_id=post_id,
                meta_title=draft['meta_title'],
                meta_description=draft['meta_description'],
                focus_keyphrase=draft['target_keyword'],
                post_type=api_endpoint
            )

        # Set featured image — use frontmatter field first, then first image in body
        image_path = draft.get('featured_image') or self._find_first_image(
            draft['content'], base_dir=Path(file_path).parent
        )
        if image_path:
            try:
                media_id, _ = self.upload_media(image_path)
                self.set_featured_image(post_id, media_id, api_endpoint)
            except Exception as e:
                print(f"    Warning: image upload failed — {e}")

        # Build edit URL
        edit_url = f"{self._display_url}/wp-admin/post.php?post={post_id}&action=edit"

        return {
            'post_id': post_id,
            'post_type': post_type,
            'edit_url': edit_url,
            'view_url': post.get('link', ''),
            'title': draft['title'],
            'slug': draft['slug'],
            'word_count': word_count,
            'categories': [c.strip() for c in draft['category'].split(',')] if draft['category'] else [],
            'tags': [t.strip() for t in draft['tags'].split(',')] if draft['tags'] else [],
            'meta': {
                'title': draft['meta_title'],
                'description': draft['meta_description'],
                'focus_keyphrase': draft['target_keyword']
            }
        }


def main():
    """CLI entry point for testing"""
    import sys
    import argparse
    from dotenv import load_dotenv

    # Load environment variables
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)

    parser = argparse.ArgumentParser(description='Publish a draft to WordPress')
    parser.add_argument('file_path', help='Path to the markdown draft file')
    parser.add_argument(
        '--type', '-t',
        default='post',
        help='Content type: post, page, or custom post type (default: post)'
    )
    args = parser.parse_args()

    try:
        publisher = WordPressPublisher()
        result = publisher.publish_draft(args.file_path, post_type=args.type)

        type_label = result['post_type'].title()
        print(f"\n✓ Parsed draft file")
        print(f"✓ Converted {result['word_count']:,} words to HTML")
        print(f"✓ Created WordPress {type_label} draft (ID: {result['post_id']})")
        print(f"✓ Set Yoast meta (title, description, focus keyphrase)")

        if result['categories']:
            print(f"✓ Assigned categories: {', '.join(result['categories'])}")
        if result['tags']:
            print(f"✓ Assigned tags: {', '.join(result['tags'])}")

        print(f"\nDraft published to WordPress!")
        print(f"Edit URL: {result['edit_url']}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"WordPress API Error: {e}")
        print(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
        sys.exit(1)
    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
