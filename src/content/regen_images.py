"""
Regenerate Images for Existing Content Pages
=============================================
Strips old injected images from HTML, regenerates them with the current
ImageGenerator (topic-specific prompts + room/treatment reference photos),
and saves the updated HTML in place.

Usage:
    python3 src/content/regen_images.py --abbr sdy --folders hair-oiling-treatment-2026-04-06,thai-facial-massage-2026-03-28
    python3 src/content/regen_images.py --abbr sdy --folders hair-oiling-treatment-2026-04-06 --type service
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))

from image_generator import ImageGenerator

CLIENTS_DIR = ROOT / 'clients'
CONTENT_DIR = ROOT / 'content'


def strip_img_tags(html: str) -> str:
    """Remove all <img ...> tags from HTML. Safe because content writers never
    include img tags — they are always injected post-generation by ImageGenerator."""
    return re.sub(r'<img[^>]+>', '', html)


def topic_from_folder(folder_name: str) -> str:
    """Derive a human-readable topic from a dated folder name.
    E.g. 'hair-oiling-treatment-2026-04-06' → 'Hair Oiling Treatment'
    """
    slug = re.sub(r'-\d{4}-\d{2}-\d{2}$', '', folder_name)
    return slug.replace('-', ' ').title()


def regen_folder(abbr: str, folder: Path, img_settings: dict) -> float:
    """Strip old images, regenerate with current prompts. Returns cost in USD."""
    html_files = list(folder.glob('*.html'))
    if not html_files:
        print(f"  ⚠ No HTML file found in {folder.name} — skipping")
        return 0.0

    html_path = html_files[0]
    topic = topic_from_folder(folder.name)

    print(f"\n→ {folder.name}")
    print(f"  Topic: {topic}")

    # Strip old img tags and save
    html = html_path.read_text(encoding='utf-8')
    stripped = strip_img_tags(html)
    html_path.write_text(stripped, encoding='utf-8')
    print(f"  ✓ Stripped existing img tags")

    # Delete old image files
    old_images = list(folder.glob('*.jpg'))
    for img in old_images:
        img.unlink()
    print(f"  ✓ Deleted {len(old_images)} old image(s)")

    # Regenerate
    generator = ImageGenerator(
        room_description=img_settings.get('room_description', ''),
        room_reference_image_path=img_settings.get('room_reference_image', ''),
    )
    cost = generator.generate_for_post(stripped, topic, html_path, 'service')
    print(f"  ✓ Generated new images (${cost:.4f})")

    return cost


def main():
    parser = argparse.ArgumentParser(description='Regenerate images for existing content pages')
    parser.add_argument('--abbr', required=True, help='Client abbreviation (e.g. sdy)')
    parser.add_argument('--folders', required=True,
                        help='Comma-separated folder names under content/[abbr]/[type]/')
    parser.add_argument('--type', dest='content_type', default='service',
                        help='Content type subdirectory (default: service)')
    args = parser.parse_args()

    config_path = CLIENTS_DIR / args.abbr / 'config.json'
    config = json.loads(config_path.read_text())
    img_settings = config.get('image_settings', {})

    base_dir = CONTENT_DIR / args.abbr / args.content_type
    folder_names = [f.strip() for f in args.folders.split(',')]

    total_cost = 0.0
    for folder_name in folder_names:
        folder = base_dir / folder_name
        if not folder.exists():
            print(f"\n⚠ Folder not found: {folder}")
            continue
        total_cost += regen_folder(args.abbr, folder, img_settings)

    print(f"\n{'─' * 40}")
    print(f"Total cost: ${total_cost:.4f}")
    print(f"\nNext step: republish each page to WordPress:")
    for name in folder_names:
        folder_path = base_dir / name
        html_files = list(folder_path.glob('*.html')) if folder_path.exists() else []
        if html_files:
            rel = html_files[0].relative_to(ROOT)
            print(f"  python3 src/content/republish_existing.py --abbr {args.abbr} --file {rel}")


if __name__ == '__main__':
    main()
