#!/usr/bin/env python3
"""
Inject an Elementor template reference into existing WordPress posts.

Prepends a Shortcode widget containing [elementor-template id="N"] to the top
of _elementor_data so the template renders dynamically at the top of every post.
Skips posts that already contain the reference.

Usage:
    python3 src/publishing/inject_elementor_template.py --template-id 22698
    python3 src/publishing/inject_elementor_template.py --template-id 22698 --dry-run
    python3 src/publishing/inject_elementor_template.py --template-id 22698 --post-id 12345
    python3 src/publishing/inject_elementor_template.py --template-id 22698 --abbr gtm
"""

import argparse
import json
import sys
import urllib3
import uuid
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

import requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def make_template_container(template_id: int) -> dict:
    """Build an Elementor container with a shortcode widget referencing the template."""
    return {
        'id': uuid.uuid4().hex[:8],
        'elType': 'container',
        'settings': {
            'content_width': 'full',
            '_title': f'Template {template_id}',
        },
        'elements': [
            {
                'id': uuid.uuid4().hex[:8],
                'elType': 'widget',
                'widgetType': 'shortcode',
                'settings': {
                    'shortcode': f'[elementor-template id="{template_id}"]',
                },
                'elements': [],
            }
        ],
    }


def already_injected(elements: list, template_id: int) -> bool:
    """Check parsed elements list for an existing template reference."""
    shortcode = f'[elementor-template id="{template_id}"]'
    for el in elements:
        if el.get('settings', {}).get('shortcode') == shortcode:
            return True
        if el.get('settings', {}).get('_title') == f'Template {template_id}':
            return True
        if el.get('elements') and already_injected(el['elements'], template_id):
            return True
    return False


def fetch_all_posts(session, base_url: str, endpoint: str) -> list:
    posts = []
    page = 1
    while True:
        r = session.get(
            f'{base_url}/wp-json/wp/v2/{endpoint}',
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


def process_post(session, base_url: str, endpoint: str, post: dict, template_id: int, dry_run: bool) -> str:
    """Returns 'updated-elementor', 'updated-content', 'skipped', or 'error'."""
    post_id = post['id']
    elementor_data_raw = post.get('meta', {}).get('_elementor_data', '')
    shortcode = f'[elementor-template id="{template_id}"]'

    # --- Elementor post ---
    if elementor_data_raw:
        try:
            elements = json.loads(elementor_data_raw)
        except json.JSONDecodeError:
            return 'error'
        if not isinstance(elements, list):
            return 'error'
        # Remove any duplicate template containers, keep at most one
        title = f'Template {template_id}'
        non_template = [e for e in elements if not (isinstance(e.get('settings'), dict) and e['settings'].get('_title') == title)]
        already_present = len(elements) != len(non_template)
        if already_present:
            # Keep exactly one at the top, drop extras
            elements = [make_template_container(template_id)] + non_template
            if not dry_run:
                r = session.patch(
                    f'{base_url}/wp-json/wp/v2/{endpoint}/{post_id}',
                    json={'meta': {'_elementor_data': json.dumps(elements, ensure_ascii=False)}},
                )
                r.raise_for_status()
            return 'deduped'
        elements.insert(0, make_template_container(template_id))
        if not dry_run:
            r = session.patch(
                f'{base_url}/wp-json/wp/v2/{endpoint}/{post_id}',
                json={'meta': {'_elementor_data': json.dumps(elements, ensure_ascii=False)}},
            )
            r.raise_for_status()
        return 'updated-elementor'

    # --- Standard content post ---
    raw_content = post.get('content', {}).get('raw', '')
    if shortcode in raw_content:
        return 'skipped'
    updated_content = shortcode + '\n\n' + raw_content
    if not dry_run:
        r = session.patch(
            f'{base_url}/wp-json/wp/v2/{endpoint}/{post_id}',
            json={'content': updated_content},
        )
        r.raise_for_status()
    return 'updated-content'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--abbr', default='gtb', help='Client abbreviation (default: gtb)')
    parser.add_argument('--template-id', type=int, required=True, help='Elementor template ID to inject')
    parser.add_argument('--post-id', type=int, help='Run on a single post ID only')
    parser.add_argument('--dry-run', action='store_true', help='Print what would change, no writes')
    args = parser.parse_args()

    config_path = ROOT / 'clients' / args.abbr.lower() / 'config.json'
    config = json.loads(config_path.read_text())
    wp = config['wordpress']
    base_url = wp['url'].rstrip('/')
    verify_ssl = not ('.local' in base_url or 'staging' in base_url)

    session = requests.Session()
    session.auth = (wp['username'], wp['app_password'])
    session.verify = verify_ssl

    endpoint = 'posts'  # blog posts use standard WP post type

    if args.dry_run:
        print('DRY RUN — no changes will be written\n')

    if args.post_id:
        r = session.get(f'{base_url}/wp-json/wp/v2/{endpoint}/{args.post_id}?context=edit')
        r.raise_for_status()
        posts = [r.json()]
    else:
        posts = fetch_all_posts(session, base_url, endpoint)

    updated_el = updated_ct = deduped = skipped = errors = 0
    for post in posts:
        title = post.get('title', {}).get('rendered', f"ID {post['id']}")
        status = post.get('status', '?')
        result = process_post(session, base_url, endpoint, post, args.template_id, args.dry_run)
        if result == 'updated-elementor':
            print(f'  ✓ [elementor] [{status}] {title}')
            updated_el += 1
        elif result == 'updated-content':
            print(f'  ✓ [content]   [{status}] {title}')
            updated_ct += 1
        elif result == 'deduped':
            print(f'  ⚑ [deduped]   [{status}] {title}')
            deduped += 1
        elif result == 'skipped':
            print(f'  · [{status}] {title} — already done')
            skipped += 1
        else:
            print(f'  ✗ [{status}] {title} — error')
            errors += 1

    print(f'\nDone — {updated_el} elementor, {updated_ct} content, {deduped} deduped, {skipped} already done, {errors} errors')


if __name__ == '__main__':
    main()
