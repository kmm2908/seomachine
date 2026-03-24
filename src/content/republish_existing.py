"""
Republish Existing HTML Files to WordPress
===========================================
Re-publishes already-generated HTML files without regenerating content.
Use this when posts need to be re-created in WordPress (e.g. after enabling
Elementor support for custom post types).

Usage:
    python3 republish_existing.py                    # republish all gtm location files
    python3 republish_existing.py --abbr gtm         # specific client
    python3 republish_existing.py --type location    # specific content type
    python3 republish_existing.py --type service     # service pages

The script discovers HTML files under content/[abbr]/[type]/ and publishes
each one using the same Elementor template injection as the batch runner.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))

from wordpress_publisher import WordPressPublisher

CLIENTS_DIR = ROOT / 'clients'
CONTENT_DIR = ROOT / 'content'


def load_client_config(abbr: str) -> dict:
    config_path = CLIENTS_DIR / abbr / 'config.json'
    with open(config_path) as f:
        return json.load(f)


def republish(abbr: str = 'gtm', content_type: str = 'location'):
    config = load_client_config(abbr)
    wp_config = config.get('wordpress')
    if not wp_config:
        print(f"No wordpress config found for {abbr}")
        return

    content_type_map = wp_config.get('content_type_map', {})
    post_type = content_type_map.get(content_type, wp_config.get('default_post_type', 'post'))

    elementor_template = CLIENTS_DIR / abbr / 'elementor-template.json'
    elementor_template_path = str(elementor_template) if elementor_template.exists() else None

    html_files = sorted((CONTENT_DIR / abbr / content_type).glob('**/*.html'))
    if not html_files:
        print(f"No HTML files found in content/{abbr}/{content_type}/")
        return

    print(f"Found {len(html_files)} file(s) to publish as {post_type}:\n")

    publisher = WordPressPublisher.from_config(wp_config)

    for i, html_path in enumerate(html_files, 1):
        slug = html_path.stem.rsplit('-', 3)[0]  # strip -YYYY-MM-DD suffix
        excerpt = slug.replace('-', ' ').title()   # e.g. "Glasgow Central Station"
        print(f"[{i}/{len(html_files)}] {html_path.name}")

        html_content = html_path.read_text(encoding='utf-8')

        # Find banner image in same folder (keyword-rich filename ending in -banner.jpg)
        folder = html_path.parent
        banner_candidates = list(folder.glob('*-banner.jpg'))
        featured_image = str(banner_candidates[0]) if banner_candidates else None

        try:
            result = publisher.publish_html_content(
                html_content=html_content,
                slug=slug,
                post_type=post_type,
                featured_image_path=featured_image,
                elementor_template_path=elementor_template_path,
                excerpt=excerpt,
            )
            print(f"    → Published (ID: {result['post_id']}): {result['edit_url']}\n")
        except Exception as e:
            print(f"    → Failed: {e}\n")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--abbr', default='gtm')
    parser.add_argument('--type', dest='content_type', default='location')
    args = parser.parse_args()
    republish(args.abbr, args.content_type)
