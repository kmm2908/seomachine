#!/usr/bin/env python3
"""
Backfill CSS classes on already-published WordPress posts.

Fetches posts via REST API, injects heading/text classes into Elementor HTML
widget content, and updates the post in place. No content regeneration.

Class map:
  h1 → hdr-xl | h2 → hdr-l | h3 → hdr-m | h4 → hdr-s | h5 → hdr-xs
  p  → txt-m  | small → txt-s

Elements that already have a class attribute are left untouched (preserves
intentional overrides like FAQ <h2 class="hdr-m">).

Usage:
    python3 src/publishing/update_post_classes.py --abbr sdy --type service
    python3 src/publishing/update_post_classes.py --abbr gtm --type location
    python3 src/publishing/update_post_classes.py --abbr sdy --type all
    python3 src/publishing/update_post_classes.py --abbr sdy --type service --dry-run
"""

import argparse
import json
import re
import sys
import urllib3
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

import requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ELEMENT_CLASSES = {
    'h1': 'hdr-xl',
    'h2': 'hdr-l',
    'h3': 'hdr-m',
    'h4': 'hdr-s',
    'h5': 'hdr-xs',
    'p':  'txt-m',
    'small': 'txt-s',
}

CONTENT_TYPE_MAP = {
    'service':  'seo_service',
    'location': 'seo_location',
    'pillar':   'seo_pillar',
    'topical':  'seo_topical',
    'blog':     'posts',
    'comp-alt': 'seo_comp_alt',
    'problem':  'seo_problem',
}


def inject_classes(html: str) -> str:
    """Inject CSS classes into heading and paragraph tags that have no existing class."""
    def _replace(m, cls):
        tag, attrs, content = m.group(1), m.group(2), m.group(3)
        if re.search(r'\bclass="', attrs):
            return f'<{tag}{attrs}>{content}</{tag}>'  # already classed — leave alone
        return f'<{tag} class="{cls}"{attrs}>{content}</{tag}>'

    for tag, cls in ELEMENT_CLASSES.items():
        html = re.sub(
            rf'<({tag})((?:\s[^>]*)?)>(.*?)</{tag}>',
            lambda m, c=cls: _replace(m, c),
            html, flags=re.IGNORECASE | re.DOTALL
        )
    return html


def walk_elementor(elements: list) -> bool:
    """Recursively walk Elementor elements, injecting classes into HTML widgets.
    Returns True if any changes were made."""
    changed = False
    for el in elements:
        if el.get('elType') == 'widget' and el.get('widgetType') == 'html':
            original = el.get('settings', {}).get('html', '')
            updated = inject_classes(original)
            if updated != original:
                el['settings']['html'] = updated
                changed = True
        if 'elements' in el:
            if walk_elementor(el['elements']):
                changed = True
    return changed


def fetch_all_posts(session, base_url: str, endpoint: str) -> list:
    posts = []
    page = 1
    while True:
        r = session.get(
            f"{base_url}/wp-json/wp/v2/{endpoint}",
            params={'per_page': 100, 'page': page, 'context': 'edit', 'status': 'any'},
        )
        if r.status_code == 400:
            break
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def process_post(session, base_url: str, endpoint: str, post: dict, dry_run: bool) -> str:
    """Process one post. Returns 'updated', 'skipped', or 'no-elementor'."""
    post_id = post['id']
    title = post.get('title', {}).get('rendered', f'ID {post_id}')
    elementor_data_raw = post.get('meta', {}).get('_elementor_data', '')

    if not elementor_data_raw:
        # Non-Elementor post — update raw content instead
        raw_content = post.get('content', {}).get('raw', '')
        if not raw_content:
            return 'skipped'
        updated = inject_classes(raw_content)
        if updated == raw_content:
            return 'skipped'
        if not dry_run:
            r = session.patch(
                f"{base_url}/wp-json/wp/v2/{endpoint}/{post_id}",
                json={'content': updated},
            )
            r.raise_for_status()
        return 'updated'

    try:
        elements = json.loads(elementor_data_raw)
    except json.JSONDecodeError:
        return 'skipped'

    changed = walk_elementor(elements)
    if not changed:
        return 'skipped'

    if not dry_run:
        r = session.patch(
            f"{base_url}/wp-json/wp/v2/{endpoint}/{post_id}",
            json={'meta': {'_elementor_data': json.dumps(elements, ensure_ascii=False)}},
        )
        r.raise_for_status()

    return 'updated'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--abbr', required=True)
    parser.add_argument('--type', required=True, help='service, location, blog, comp-alt, problem, pillar, topical, or "all"')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    config_path = ROOT / 'clients' / args.abbr.lower() / 'config.json'
    config = json.loads(config_path.read_text())
    wp = config['wordpress']
    base_url = wp['url'].rstrip('/')
    verify_ssl = not ('.local' in base_url or 'staging' in base_url)

    session = requests.Session()
    session.auth = (wp['username'], wp['app_password'])
    session.verify = verify_ssl

    types = list(CONTENT_TYPE_MAP.keys()) if args.type == 'all' else [args.type]

    if args.dry_run:
        print('DRY RUN — no changes will be written\n')

    total_updated = total_skipped = 0

    for content_type in types:
        endpoint = CONTENT_TYPE_MAP.get(content_type)
        if not endpoint:
            print(f'Unknown type: {content_type}')
            continue

        posts = fetch_all_posts(session, base_url, endpoint)
        if not posts:
            print(f'  {content_type}: no posts found')
            continue

        updated = skipped = 0
        for post in posts:
            result = process_post(session, base_url, endpoint, post, args.dry_run)
            title = post.get('title', {}).get('rendered', f"ID {post['id']}")
            if result == 'updated':
                print(f'  ✓ [{content_type}] {title}')
                updated += 1
            else:
                skipped += 1

        print(f'  → {content_type}: {updated} updated, {skipped} skipped')
        total_updated += updated
        total_skipped += skipped

    print(f'\nDone — {total_updated} updated, {total_skipped} skipped')


if __name__ == '__main__':
    main()
