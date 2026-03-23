"""
Geo Batch Runner
================
Standalone Python script that reads locations/topics from a Google Sheet
and generates content for any business client using the Anthropic Claude API.

Supports multiple content types: service, location, pillar, topical, blog.

Usage:
    python3 geo_batch_runner.py             # process all "Write Now" rows
    python3 geo_batch_runner.py A2:E5       # process a specific range only
    python3 geo_batch_runner.py --publish   # also publish each file to WordPress

Requirements:
    pip install anthropic python-dotenv google-api-python-client google-auth

Environment variables (in .env at project root):
    ANTHROPIC_API_KEY           - Anthropic API key
    GEO_LOCATIONS_SHEET_ID      - Google Sheet ID
    GA4_CREDENTIALS_PATH        - Path to service account JSON
    GEO_EMAIL_*                 - SMTP email settings (optional)
"""

import argparse
import json
import os
import re
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv

# ── Project root and .env ────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.resolve()
load_dotenv(ROOT / '.env')

# ── Import shared Google Sheets helpers ──────────────────────────────────────
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))
from google_sheets import (
    read_pending, update_status, update_cost, update_file_path,
    send_email, IMAGES_PENDING_VALUE,
)
from wikipedia import WikipediaResearcher

# ── Paths ────────────────────────────────────────────────────────────────────
CONTENT_DIR = ROOT / 'content'
CONTEXT_DIR = ROOT / 'context'
AGENTS_DIR = ROOT / '.claude' / 'agents'
CLIENTS_DIR = ROOT / 'clients'

# ── Content type → agent file mapping ────────────────────────────────────────
CONTENT_TYPE_AGENTS = {
    'service':  'service-page-writer.md',
    'location': 'location-page-writer.md',
    'topical':  'topical-writer.md',
    'blog':     'blog-post-writer.md',
    'pillar':   'pillar-page-writer.md',
}

# ── Claude model and pricing ─────────────────────────────────────────────────
MODEL = 'claude-sonnet-4-6'
# Sonnet 4.6 pricing: $3.00 input / $15.00 output per 1M tokens
INPUT_COST_PER_M = 3.00
OUTPUT_COST_PER_M = 15.00


def load_file(path: Path) -> str:
    """Read a file, return empty string if missing."""
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ''


def slugify(text: str) -> str:
    """Convert a string to a URL-safe filename slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text.strip())
    text = re.sub(r'-+', '-', text)
    return text[:80].rstrip('-')


def load_business_config(abbreviation: str) -> dict:
    """Load business config JSON from clients/[abbr]/config.json. Raises clear error if not found."""
    path = CLIENTS_DIR / abbreviation.lower() / 'config.json'
    if not path.exists():
        raise FileNotFoundError(
            f"No client config found for '{abbreviation}'. "
            f"Expected: {path}. Run /new-client to set one up."
        )
    return json.loads(path.read_text(encoding='utf-8'))


def build_system_prompt(abbreviation: str, content_type: str,
                        business_config: Optional[dict] = None) -> str:
    """Build the system prompt from the relevant agent + client context files."""
    agent_file = CONTENT_TYPE_AGENTS.get(content_type, 'blog-post-writer.md')
    agent = load_file(AGENTS_DIR / agent_file)

    # Load client-specific context files
    client_dir = CLIENTS_DIR / abbreviation.lower()
    brand_voice = load_file(client_dir / 'brand-voice.md')
    seo_guidelines = load_file(client_dir / 'seo-guidelines.md')
    internal_links = load_file(client_dir / 'internal-links-map.md')

    # Load global context files
    style_guide = load_file(CONTEXT_DIR / 'style-guide.md')

    parts = [
        "You are running as a standalone automation script. Follow these instructions precisely.\n",
    ]

    if business_config:
        parts.append(f"\n\n## Business Context\n\n```json\n{json.dumps(business_config, indent=2)}\n```")

    parts.append(agent)

    if brand_voice:
        parts.append(f"\n\n## Brand Voice\n\n{brand_voice}")
    if style_guide:
        parts.append(f"\n\n## Style Guide\n\n{style_guide}")
    if seo_guidelines:
        parts.append(f"\n\n## SEO Guidelines\n\n{seo_guidelines}")
    if internal_links:
        parts.append(f"\n\n## Internal Links Map\n\n{internal_links}")

    parts.append(
        "\n\n## Output Instructions\n\n"
        "Your ENTIRE response must be the HTML content — nothing else. "
        "Start your response with `<!-- SECTION 1 -->` on its own line. "
        "Output all three sections: <!-- SECTION 1 -->, <!-- SECTION 2 FAQ -->, and <!-- SCHEMA -->. "
        "Do not include any frontmatter, markdown, explanation, preamble, or commentary. "
        "Do not wrap the output in a code block. "
        "The output is written directly to a file and pasted into a page template. "
        "Any text outside the HTML will corrupt the output."
    )

    return '\n'.join(parts)


def build_wiki_block(wiki_data: Optional[dict]) -> str:
    """Return a formatted Wikipedia research block to inject into prompts, or empty string."""
    if not wiki_data or not wiki_data.get('found'):
        return ''
    entities = ', '.join(wiki_data['related_entities'][:10])
    return (
        f"\n## Wikipedia Research: {wiki_data['title']}\n"
        f"Source: {wiki_data['url']}\n"
        f"Summary: {wiki_data['summary']}\n"
        f"Related entities from Wikipedia: {entities}\n\n"
        f"Use this as a factual basis for local detail. Include the Wikipedia URL as an outbound "
        f"authority link in the 'About This Area' section — place it naturally within a sentence.\n"
    )


def build_service_prompt(topic: str, business_config: Optional[dict] = None) -> str:
    """User prompt for service page content."""
    today = date.today().isoformat()
    business_name = business_config.get('name', '') if business_config else ''
    services = business_config.get('services', []) if business_config else []
    return f"""Write a service page for the following:

Service/Topic: {topic}
Business: {business_name}
Services offered: {', '.join(services)}
Today's date: {today}

Steps you must follow:

1. Use the web_search tool to research this service:
   - "{topic} Glasgow benefits"
   - "{topic} what to expect"

2. Write a 550-700 word service page following the structure in your instructions:
   Section 1 (Hook → What Is It → Benefits → Who It's For → What to Expect → Trust Signals)
   Section 2 (FAQ — 4-6 questions about this service)

3. Output three HTML sections starting with <!-- SECTION 1 -->. No frontmatter, no markdown."""


def build_location_prompt(topic: str, business_config: Optional[dict] = None,
                          wiki_data: Optional[dict] = None) -> str:
    """User prompt for location/area page content. Handles both district names and postcode/address inputs."""
    today = date.today().isoformat()
    wiki_block = build_wiki_block(wiki_data)

    # Detect postcode or multi-word address input — tighten word count and search queries
    is_precise = bool(re.search(r'\b[Gg]\d+\s?\d*[A-Za-z]{0,2}\b', topic)) or len(topic.split()) > 4
    word_count = "minimum 450" if is_precise else "minimum 550"
    search_queries = (
        f'   - "{topic} transport subway bus routes"\n'
        f'   - "{topic} Glasgow landmarks businesses workers"\n'
        f'   - "{topic} Glasgow area facts"'
        if is_precise else
        f'   - "{topic} area Glasgow facts"\n'
        f'   - "{topic} Glasgow businesses residents"\n'
        f'   - "{topic} Glasgow transport links"'
    )

    return f"""Write a location page for the following:

Location: {topic}
Today's date: {today}
{wiki_block}
Steps you must follow:

1. Use the web_search tool to research this location:
{search_queries}

2. Write a {word_count} word location page following the structure in your instructions:
   Section 1 (Area Intro → Why This Business → Services → Getting Here → Trust Signals)
   Section 2 (FAQ — 4-5 questions for someone booking from this location)

3. Output three HTML sections starting with <!-- SECTION 1 -->. No frontmatter, no markdown."""


def build_topical_prompt(topic: str, business_config: Optional[dict] = None,
                         wiki_data: Optional[dict] = None) -> str:
    """User prompt for topical/informational content."""
    today = date.today().isoformat()
    wiki_block = build_wiki_block(wiki_data)
    if wiki_data and wiki_data.get('found'):
        # For topical content the Wikipedia link is a citation, not an area link
        wiki_block = wiki_block.replace(
            "Use this as a factual basis for local detail. Include the Wikipedia URL as an outbound "
            "authority link in the 'About This Area' section — place it naturally within a sentence.",
            "Use this as a reference source for background and related entities. Include the Wikipedia "
            "URL as an outbound authority citation — place it naturally within the article body."
        )
    return f"""Write an informational article on the following topic:

Topic: {topic}
Today's date: {today}
{wiki_block}
Steps you must follow:

1. Use the web_search tool to research this topic:
   - "{topic} benefits research"
   - "{topic} how it works"
   - "{topic} FAQ"

2. Write a 650-900 word informational article following the structure in your instructions.
   Base your content on research findings — cite specific facts where possible.
   Section 1 (Introduction → Main sections → Practical advice)
   Section 2 (FAQ — 4-6 follow-up questions)

3. Output three HTML sections starting with <!-- SECTION 1 -->. No frontmatter, no markdown."""


def build_blog_prompt(topic: str, business_config: Optional[dict] = None) -> str:
    """User prompt for blog post content."""
    today = date.today().isoformat()
    return f"""Write a blog post on the following topic:

Topic: {topic}
Today's date: {today}

Steps you must follow:

1. Use the web_search tool if helpful to find relevant facts or angles:
   - "{topic}"

2. Write a 900-1500 word blog post following the structure in your instructions.
   Keep the tone conversational and engaging.
   Section 1 (Hook intro → body sections with H3 subheadings → closing paragraph)
   Section 2 (FAQ — 4-5 questions related to the topic)

3. Output three HTML sections starting with <!-- SECTION 1 -->. No frontmatter, no markdown."""


PROMPT_BUILDERS = {
    'service':  build_service_prompt,
    'location': build_location_prompt,
    'topical':  build_topical_prompt,
    'blog':     build_blog_prompt,
}


def build_user_prompt(topic: str, content_type: str,
                      business_config: Optional[dict] = None,
                      wiki_data: Optional[dict] = None) -> str:
    """Build the user prompt for the given content type."""
    builder = PROMPT_BUILDERS.get(content_type, build_blog_prompt)
    # Only geo, location, and topical support wiki_data
    if content_type in ('location', 'topical'):
        return builder(topic, business_config, wiki_data)
    return builder(topic, business_config)


def write_content_file(topic: str, content: str, abbreviation: str,
                       content_type: str) -> Path:
    """Save content to content/[abbr]/[type]/[slug]-[date]/ and return the file path."""
    slug = slugify(topic)
    today = date.today().isoformat()
    article_dir = CONTENT_DIR / abbreviation.lower() / content_type / f"{slug}-{today}"
    article_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{slug}-{today}.html"
    filepath = article_dir / filename
    filepath.write_text(content, encoding='utf-8')
    return filepath


def extract_word_count(content: str) -> int:
    """Estimate word count from HTML content (strips tags and comments)."""
    text = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def run_quality_check(content: str) -> None:
    """Run engagement and readability checks on generated content."""
    try:
        from engagement_analyzer import EngagementAnalyzer
        from readability_scorer import ReadabilityScorer

        plain = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        # Preserve paragraph breaks before stripping tags
        plain = re.sub(r'</p>', '\n\n', plain, flags=re.IGNORECASE)
        plain = re.sub(r'<br\s*/?>', '\n', plain, flags=re.IGNORECASE)
        plain = re.sub(r'<[^>]+>', ' ', plain)
        plain = re.sub(r'\n[ \t]+', '\n', plain)
        plain = re.sub(r' +', ' ', plain).strip()

        eng = EngagementAnalyzer().analyze(plain)
        read = ReadabilityScorer().analyze(plain)

        eng_score = f"{eng['passed_count']}/{eng['total_criteria']}"
        read_score = read.get('overall_score', 0)
        grade = read.get('grade', '?').split(' ')[0]

        issues = [k for k, passed in eng['scores'].items() if not passed]
        issue_str = f"  ⚠ fix: {', '.join(issues)}" if issues else ""

        print(f"    → Quality: engagement {eng_score} | readability {read_score:.0f}/100 ({grade}){issue_str}")
    except Exception as qe:
        print(f"    → Quality check skipped: {qe}")


def calculate_cost(usage) -> float:
    """Calculate USD cost from an API usage object."""
    input_tokens = getattr(usage, 'input_tokens', 0) or 0
    output_tokens = getattr(usage, 'output_tokens', 0) or 0
    return (input_tokens / 1_000_000 * INPUT_COST_PER_M) + \
           (output_tokens / 1_000_000 * OUTPUT_COST_PER_M)


def generate_content(topic: str, abbreviation: str, content_type: str,
                     client: anthropic.Anthropic,
                     business_config: Optional[dict] = None):
    """Call Claude API to research and write content.
    Returns (content: str, cost_usd: float).
    """
    system_prompt = build_system_prompt(abbreviation, content_type, business_config)

    wiki_data = None
    if content_type in ('location', 'topical'):
        wiki_data = WikipediaResearcher().research(topic)
        if wiki_data.get('found'):
            print(f"    Wikipedia: found '{wiki_data['title']}' — {wiki_data['url']}")
        else:
            print(f"    Wikipedia: no page found for '{topic}'")

    user_prompt = build_user_prompt(topic, content_type, business_config, wiki_data=wiki_data)

    # Retry once on rate limit (wait 70 seconds then retry)
    for attempt in range(2):
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=4096,
                system=system_prompt,
                tools=[
                    {"type": "web_search_20260209", "name": "web_search"},
                ],
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
            ) as stream:
                final = stream.get_final_message()
            break
        except anthropic.RateLimitError:
            if attempt == 0:
                print("    Rate limited — waiting 70 seconds before retry...")
                time.sleep(70)
            else:
                raise

    cost_usd = calculate_cost(final.usage)

    # Find the text block that is the actual markdown (starts with ---)
    # Fall back to the last text block if none starts with frontmatter
    text_blocks = [
        block.text.strip()
        for block in final.content
        if block.type == 'text' and block.text.strip()
    ]

    if not text_blocks:
        raise ValueError("No text content in response")

    # Prefer the block that starts with the Section 1 HTML comment
    for block in text_blocks:
        if block.startswith('<!-- SECTION 1 -->'):
            return block, cost_usd

    # Fall back: find any block containing the section marker, strip any preamble before it
    for block in text_blocks:
        if '<!-- SECTION 1 -->' in block:
            return block[block.index('<!-- SECTION 1 -->'):], cost_usd

    # Last resort: return the longest text block, still stripping any preamble
    longest = max(text_blocks, key=len)
    if '<!-- SECTION 1 -->' in longest:
        return longest[longest.index('<!-- SECTION 1 -->'):], cost_usd
    return longest, cost_usd


def run_batch(sheet_range: Optional[str] = None, publish: bool = False) -> None:
    """Main batch runner."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Read queued locations from Sheet
    print("Reading Google Sheet...")
    try:
        locations = read_pending(sheet_range)
    except Exception as e:
        print(f"ERROR reading sheet: {e}")
        sys.exit(1)

    if not locations:
        print('No locations queued. Set rows to "Write Now" in the Google Sheet to queue them.')
        return

    total = len(locations)
    print(f"Found {total} item{'s' if total != 1 else ''} queued.\n")

    written_files = []
    failures = []
    total_cost_usd = 0.0

    for i, loc in enumerate(locations, 1):
        row = loc['row']
        address = loc['address']
        abbreviation = loc.get('business', '').strip()
        content_type = loc.get('content_type', 'blog').strip().lower() or 'blog'
        item_status = loc.get('status', 'Write Now')

        # ── Images o/s: retry image generation only ───────────────────────────
        if item_status.lower() == IMAGES_PENDING_VALUE.lower():
            print(f"[{i}/{total}] Retrying images [{content_type}]: {address} [{abbreviation}]...")
            file_path_rel = loc.get('file_path', '').strip()
            if not file_path_rel:
                print(f"    → No file path recorded — resetting to 'Write Now'")
                update_status(row, 'Write Now')
            else:
                filepath = ROOT / file_path_rel
                if not filepath.exists():
                    print(f"    → File not found: {file_path_rel} — resetting to 'Write Now'")
                    update_status(row, 'Write Now')
                    update_file_path(row, '')
                else:
                    html_content = filepath.read_text(encoding='utf-8')
                    try:
                        sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))
                        from image_generator import ImageGenerator
                        img_cost = ImageGenerator().generate_for_post(
                            html_content, address, filepath, content_type
                        )
                        total_cost_usd += img_cost
                        print(f"    → Images: generated (+${img_cost:.2f})")
                        try:
                            update_cost(row, f"${img_cost:.4f}")
                        except Exception:
                            pass
                        if publish:
                            try:
                                business_config = load_business_config(abbreviation)
                                wp_config = business_config.get('wordpress')
                                if wp_config:
                                    from wordpress_publisher import WordPressPublisher
                                    publisher = WordPressPublisher.from_config(wp_config)
                                    post_type = wp_config.get('content_type_map', {}).get(
                                        content_type, wp_config.get('default_post_type', 'post')
                                    )
                                    banner_candidates = list(filepath.parent.glob('*-banner.jpg'))
                                    featured_image = str(banner_candidates[0]) if banner_candidates else None
                                    elementor_template = CLIENTS_DIR / abbreviation.lower() / 'elementor-template.json'
                                    result = publisher.publish_html_content(
                                        html_content=html_content,
                                        slug=slugify(address),
                                        post_type=post_type,
                                        featured_image_path=featured_image,
                                        elementor_template_path=str(elementor_template) if elementor_template.exists() else None,
                                        excerpt=address,
                                    )
                                    print(f"    → Published WP draft (ID: {result['post_id']}): {result['edit_url']}")
                            except Exception as e:
                                print(f"    → WP publish failed: {e}")
                        update_status(row, 'DONE')
                        update_file_path(row, '')
                        written_files.append(str(filepath.relative_to(ROOT)))
                        print(f"[{i}/{total}] ✓ Images done: {filepath.relative_to(ROOT)}")
                    except Exception as img_err:
                        print(f"    → Images: still failing — {img_err}")
                        # Leave as 'Images o/s' for next run
            if i < total:
                time.sleep(65)
            continue

        # ── Write Now: full content + image + publish pipeline ────────────────
        print(f"[{i}/{total}] Writing [{content_type}]: {address} [{abbreviation or 'no business set'}]...")

        try:
            if not abbreviation:
                raise ValueError(
                    "No business abbreviation in Column D. "
                    "Add the client abbreviation (e.g. GTM) to Column D in the Sheet."
                )

            if content_type not in CONTENT_TYPE_AGENTS:
                raise ValueError(
                    f"Unknown content type '{content_type}'. "
                    f"Valid types: {', '.join(CONTENT_TYPE_AGENTS.keys())}"
                )

            business_config = load_business_config(abbreviation)
            content, cost_usd = generate_content(
                address, abbreviation, content_type, client, business_config
            )

            if not content or len(content) < 100:
                raise ValueError("Generated content is too short or empty")

            # Replace schema tokens: date (full ISO 8601 with timezone), business fields
            today_iso = datetime.now().strftime('%Y-%m-%dT12:00:00+00:00')
            schema_cfg = business_config.get('schema', {})
            content = content.replace('[DATE]', today_iso)
            content = content.replace('[BUSINESS_PHONE]', business_config.get('phone', ''))
            content = content.replace('[BUSINESS_URL]', business_config.get('website', ''))
            content = content.replace('[BUSINESS_PRICE_RANGE]', schema_cfg.get('price_range', ''))
            content = content.replace('[BUSINESS_LOGO]', schema_cfg.get('logo_url', ''))

            filepath = write_content_file(address, content, abbreviation, content_type)
            word_count = extract_word_count(content)

            # Generate images if provider is configured
            images_ok = True
            if os.getenv('IMAGE_API_PROVIDER') == 'gemini':
                try:
                    from image_generator import ImageGenerator
                    img_cost = ImageGenerator().generate_for_post(content, address, filepath, content_type)
                    cost_usd += img_cost
                    content = filepath.read_text(encoding='utf-8')  # reload with injected img tags
                    print(f"    → Images: 3 generated (+${img_cost:.2f})")
                except Exception as img_err:
                    images_ok = False
                    print(f"    → Images: failed — {img_err}")

            # If publishing and images failed, defer — mark 'Images o/s', don't publish
            if not images_ok and publish:
                update_status(row, IMAGES_PENDING_VALUE)
                update_file_path(row, str(filepath.relative_to(ROOT)))
                try:
                    update_cost(row, f"${cost_usd:.4f}")
                except Exception:
                    pass
                total_cost_usd += cost_usd
                written_files.append(str(filepath.relative_to(ROOT)))
                print(f"[{i}/{total}] ✓ Written (Images o/s): {filepath.relative_to(ROOT)} ({word_count} words, ${cost_usd:.4f})")
                run_quality_check(content)
                if i < total:
                    time.sleep(65)
                continue

            # Mark DONE and record cost in Column C immediately after saving
            update_status(row, 'DONE')
            cost_str = f"${cost_usd:.4f}"
            try:
                update_cost(row, cost_str)
            except Exception:
                pass  # Cost tracking is non-critical

            total_cost_usd += cost_usd
            written_files.append(str(filepath.relative_to(ROOT)))
            print(f"[{i}/{total}] ✓ Written: {filepath.relative_to(ROOT)} ({word_count} words, {cost_str})")
            run_quality_check(content)

            # Optionally publish to WordPress
            if publish:
                wp_config = business_config.get('wordpress')
                if wp_config:
                    try:
                        sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))
                        from wordpress_publisher import WordPressPublisher
                        publisher = WordPressPublisher.from_config(wp_config)
                        content_type_map = wp_config.get('content_type_map', {})
                        post_type = content_type_map.get(content_type, wp_config.get('default_post_type', 'post'))
                        slug = slugify(address)
                        # Find banner image — filename is keyword-rich (e.g. slug-banner.jpg)
                        banner_candidates = list(filepath.parent.glob('*-banner.jpg'))
                        featured_image = str(banner_candidates[0]) if banner_candidates else None
                        # Use Elementor template if one has been fetched for this client
                        elementor_template = CLIENTS_DIR / abbreviation.lower() / 'elementor-template.json'
                        elementor_template_path = str(elementor_template) if elementor_template.exists() else None
                        result = publisher.publish_html_content(
                            html_content=content,
                            slug=slug,
                            post_type=post_type,
                            featured_image_path=featured_image,
                            elementor_template_path=elementor_template_path,
                            excerpt=address,
                        )
                        print(f"    → Published WP draft (ID: {result['post_id']}): {result['edit_url']}")
                    except Exception as e:
                        print(f"    → WP publish failed: {e}")
                else:
                    print(f"    → Skipping WP publish: no wordpress config in {abbreviation}.json")

        except Exception as e:
            reason = str(e) or type(e).__name__
            failures.append({'address': address, 'reason': reason})
            print(f"[{i}/{total}] ✗ Failed: {address} — {reason}")
            print(f"    Full traceback:\n{traceback.format_exc()}")
            # Do NOT update Sheet — leave as "Write Now" for retry

        # Pause between requests to stay under the rate limit
        if i < total:
            time.sleep(65)

    # ── Summary email ─────────────────────────────────────────────────────────
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    email_lines = [
        f"Content Batch Complete",
        f"Completed: {now}",
        f"",
        f"Total processed: {total}",
        f"Successfully written: {len(written_files)}",
        f"Failed: {len(failures)}",
        f"Total API cost: ${total_cost_usd:.4f}",
        f"",
    ]

    if written_files:
        email_lines.append("Written files:")
        for f in written_files:
            email_lines.append(f"  {f}")
        email_lines.append("")

    if failures:
        email_lines.append('Failed (still queued as "Write Now"):')
        for fail in failures:
            email_lines.append(f"  {fail['address']} — {fail['reason']}")
        email_lines.append("")

    email_body = '\n'.join(email_lines)
    subject = f"Content Batch Complete — {len(written_files)} item{'s' if len(written_files) != 1 else ''} written"

    try:
        send_email(subject, email_body)
        email_status = f"Summary email sent to: {os.getenv('GEO_EMAIL_TO', '')}"
    except Exception as e:
        email_status = f"Email skipped: {e}"

    # ── Terminal summary ──────────────────────────────────────────────────────
    print()
    print("Batch complete")
    print("─" * 40)
    print(f"Total processed:      {total}")
    print(f"Successfully written: {len(written_files)}")
    print(f"Failed:               {len(failures)}")
    print(f"Total API cost:       ${total_cost_usd:.4f}")
    print("─" * 40)

    if written_files:
        print("Written files:")
        for f in written_files:
            print(f"  {f}")

    if failures:
        print()
        print('Failed (still queued in sheet as "Write Now"):')
        for fail in failures:
            print(f"  {fail['address']} — {fail['reason']}")

    print("─" * 40)
    print(email_status)


def main():
    parser = argparse.ArgumentParser(
        description='Generate content from Google Sheet queue'
    )
    parser.add_argument(
        'range',
        nargs='?',
        default=None,
        help='Optional sheet range e.g. A2:E5 (default: all rows)',
    )
    parser.add_argument(
        '--publish',
        action='store_true',
        default=False,
        help='Publish each generated file to WordPress as a draft',
    )
    args = parser.parse_args()
    run_batch(args.range, publish=args.publish)


if __name__ == '__main__':
    main()
