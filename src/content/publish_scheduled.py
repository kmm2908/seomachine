"""
Scheduled Blog Publisher
========================
Publishes the next pending topic from a client's topic queue file, then logs
the result and sends an email notification.

Intended to be run on a cron schedule. Each run publishes exactly one topic
and advances the queue pointer.

Queue file: research/[abbr]/topic-queue.json
Log file:   logs/scheduled-publish-log.csv

Usage:
    python3 src/content/publish_scheduled.py --abbr gtb
    python3 src/content/publish_scheduled.py --abbr gtb --dry-run
    python3 src/content/publish_scheduled.py --abbr gtm --queue comp-alt-queue.json
    python3 src/content/publish_scheduled.py --abbr gtm --queue comp-alt-queue.json --status

Cron example (publish one GTB post every Monday at 09:00):
    0 9 * * 1 cd /path/to/seomachine && python3 src/content/publish_scheduled.py --abbr gtb
"""

import argparse
import csv
import json
import os
import re
import sys
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT / 'src' / 'content'))
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

import anthropic

# Import pipeline functions from geo_batch_runner
from geo_batch_runner import (
    load_business_config,
    build_system_prompt,
    build_user_prompt,
    generate_content,
    write_content_file,
    slugify,
    _ensure_directions_snippet,
    _ensure_template_fresh,
    CLIENTS_DIR,
    CONTENT_DIR,
    CONTENT_TYPE_AGENTS,
)
from google_sheets import send_email
from quality_gate import QualityGate

LOG_PATH = ROOT / 'logs' / 'scheduled-publish-log.csv'
LOG_HEADERS = ['date', 'abbr', 'topic', 'content_type', 'status', 'post_id', 'cost', 'notes']

MISSED_RUN_BUFFER_DAYS = 2  # allow this many extra days before flagging a missed run


# ---------------------------------------------------------------------------
# Queue file helpers
# ---------------------------------------------------------------------------

def queue_path(abbr: str, queue_name: str = 'topic-queue.json') -> Path:
    return ROOT / 'research' / abbr.lower() / queue_name


def load_queue(abbr: str, queue_name: str = 'topic-queue.json') -> dict:
    path = queue_path(abbr, queue_name)
    if not path.exists():
        raise FileNotFoundError(
            f"No topic queue found at {path.relative_to(ROOT)}. "
            f"Generate one with: python3 src/research/research_blog_topics.py --abbr {abbr} --queue"
        )
    with open(path) as f:
        return json.load(f)


def save_queue(abbr: str, queue: dict, queue_name: str = 'topic-queue.json') -> None:
    path = queue_path(abbr, queue_name)
    path.write_text(json.dumps(queue, indent=2))


def next_pending(queue: dict) -> tuple[int, dict] | tuple[None, None]:
    """Return (index, topic_dict) for the first pending topic, or (None, None)."""
    for i, t in enumerate(queue.get('topics', [])):
        if t.get('status') == 'pending':
            return i, t
    return None, None


def pending_count(queue: dict) -> int:
    return sum(1 for t in queue.get('topics', []) if t.get('status') == 'pending')


# ---------------------------------------------------------------------------
# Log helpers
# ---------------------------------------------------------------------------

def append_log(row: dict) -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    write_header = not LOG_PATH.exists()
    with open(LOG_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=LOG_HEADERS)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, '') for k in LOG_HEADERS})


def last_published_date(abbr: str) -> datetime | None:
    """Return the most recent successful publish date for this client from the log."""
    if not LOG_PATH.exists():
        return None
    with open(LOG_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        dates = [
            datetime.strptime(r['date'], '%Y-%m-%d')
            for r in reader
            if r.get('abbr', '').lower() == abbr.lower()
            and r.get('status') == 'published'
        ]
    return max(dates) if dates else None


def check_missed_run(abbr: str, cadence_days: int) -> str | None:
    """Return a warning string if the last publish was more than cadence + buffer days ago."""
    last = last_published_date(abbr)
    if last is None:
        return None  # first ever run — no missed run to flag
    gap = (datetime.now() - last).days
    threshold = cadence_days + MISSED_RUN_BUFFER_DAYS
    if gap > threshold:
        return (
            f"⚠ MISSED RUN: last post was {gap} days ago "
            f"(cadence: every {cadence_days}d, threshold: {threshold}d)"
        )
    return None


# ---------------------------------------------------------------------------
# Publishing pipeline
# ---------------------------------------------------------------------------

def publish_topic(topic_dict: dict, abbr: str, dry_run: bool = False) -> dict:
    """
    Run the full content generation + publish pipeline for one topic.
    Returns a result dict with keys: status, post_id, cost, notes, filepath.
    """
    topic = topic_dict['topic']
    content_type = topic_dict.get('content_type', 'blog')
    wp_category = topic_dict.get('wp_category', '')
    brief = topic_dict.get('brief', '')

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key)
    business_config = load_business_config(abbr)
    wp_config = business_config.get('wordpress')
    ssh_config = business_config.get('ssh')

    if not wp_config:
        raise ValueError(f"No wordpress config in clients/{abbr}/config.json")

    if content_type not in CONTENT_TYPE_AGENTS:
        raise ValueError(
            f"Unknown content type '{content_type}'. "
            f"Valid: {', '.join(CONTENT_TYPE_AGENTS.keys())}"
        )

    # Generate content
    content, cost_usd = generate_content(topic, abbr, content_type, client, business_config, brief=brief)

    if not content or len(content) < 100:
        raise ValueError("Generated content is too short or empty")

    # Replace schema tokens
    today_iso = datetime.now().strftime('%Y-%m-%dT12:00:00+00:00')
    schema_cfg = business_config.get('schema', {})
    content = content.replace('[DATE]', today_iso)
    content = content.replace('[BUSINESS_PHONE]', business_config.get('phone', ''))
    content = content.replace('[BUSINESS_URL]', business_config.get('website', ''))
    content = content.replace('[BUSINESS_PRICE_RANGE]', schema_cfg.get('price_range', ''))
    content = content.replace('[BUSINESS_LOGO]', schema_cfg.get('logo_url', ''))

    # Save to disk
    filepath = write_content_file(topic, content, abbr, content_type)

    # Generate images if configured
    if os.getenv('IMAGE_API_PROVIDER') == 'gemini':
        try:
            from image_generator import ImageGenerator
            img_cost = ImageGenerator().generate_for_post(content, topic, filepath, content_type)
            cost_usd += img_cost
            content = filepath.read_text(encoding='utf-8')
            print(f"    → Images: generated (+${img_cost:.2f})")
        except Exception as img_err:
            print(f"    → Images: failed (continuing without) — {img_err}")

    # Quality gate
    gate = QualityGate(client, business_config)
    gate_result = gate.check_and_improve(content, topic, content_type)
    content = gate_result.content
    cost_usd += gate_result.cost_usd
    filepath.write_text(content, encoding='utf-8')

    if not gate_result.passed:
        failures_str = ' | '.join(gate_result.failures)
        print(f"    → Quality gate failed: {failures_str} — publishing with review notice")

        # Inject review notice into content
        notice = f'<p><strong>★★★★★ Quality gate failures: {failures_str}. Review and edit before removing this notice. ★★★★★</strong></p>'
        content = re.sub(r'(<h2[^>]*>)(.*?)(</h2>)', rf'\1\2 ★★★★★\3\n{notice}', content, count=1)
        filepath.write_text(content, encoding='utf-8')

        if not dry_run:
            # Publish to WordPress with review notice
            _ensure_directions_snippet(abbr.lower())
            _ensure_template_fresh(abbr.lower(), wp_config)

            from wordpress_publisher import WordPressPublisher
            publisher = WordPressPublisher.from_config(wp_config, ssh_config=ssh_config)
            post_type = wp_config.get('content_type_map', {}).get(
                content_type, wp_config.get('default_post_type', 'post')
            )
            banner_candidates = list(filepath.parent.glob('*-banner.jpg'))
            featured_image = str(banner_candidates[0]) if banner_candidates else None
            elementor_template = CLIENTS_DIR / abbr.lower() / 'elementor-template.json'

            result = publisher.publish_html_content(
                html_content=content,
                slug=slugify(topic),
                post_type=post_type,
                featured_image_path=featured_image,
                elementor_template_path=str(elementor_template) if elementor_template.exists() else None,
                excerpt=topic,
                category=wp_category,
            )
            print(f"    → Published for review (ID: {result['post_id']}): {result['edit_url']}")

            return {
                'status': 'published_review',
                'post_id': result['post_id'],
                'cost': cost_usd,
                'notes': f"Quality gate: {failures_str} | {result.get('edit_url', '')}",
                'filepath': filepath,
            }

        return {
            'status': 'published_review',
            'post_id': None,
            'cost': cost_usd,
            'notes': f"Quality gate: {failures_str} (dry run)",
            'filepath': filepath,
        }

    if dry_run:
        print(f"    → DRY RUN — skipping WordPress publish")
        return {
            'status': 'dry_run',
            'post_id': None,
            'cost': cost_usd,
            'notes': 'dry-run mode',
            'filepath': filepath,
        }

    # Publish to WordPress
    _ensure_directions_snippet(abbr.lower())
    _ensure_template_fresh(abbr.lower(), wp_config)

    from wordpress_publisher import WordPressPublisher
    publisher = WordPressPublisher.from_config(wp_config, ssh_config=ssh_config)
    post_type = wp_config.get('content_type_map', {}).get(
        content_type, wp_config.get('default_post_type', 'post')
    )
    banner_candidates = list(filepath.parent.glob('*-banner.jpg'))
    featured_image = str(banner_candidates[0]) if banner_candidates else None
    elementor_template = CLIENTS_DIR / abbr.lower() / 'elementor-template.json'

    result = publisher.publish_html_content(
        html_content=content,
        slug=slugify(topic),
        post_type=post_type,
        featured_image_path=featured_image,
        elementor_template_path=str(elementor_template) if elementor_template.exists() else None,
        excerpt=topic,
        category=wp_category,
    )

    print(f"    → Published (ID: {result['post_id']}): {result['edit_url']}")

    return {
        'status': 'published',
        'post_id': result['post_id'],
        'cost': cost_usd,
        'notes': result.get('edit_url', ''),
        'filepath': filepath,
    }


# ---------------------------------------------------------------------------
# Email helpers
# ---------------------------------------------------------------------------

def _email_success(abbr: str, topic: str, content_type: str, result: dict,
                   remaining: int, missed_warning: str | None) -> None:
    subject = f"[{abbr.upper()}] Scheduled post published: {topic}"
    lines = [
        f"Scheduled publish complete — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Client:       {abbr.upper()}",
        f"Topic:        {topic}",
        f"Type:         {content_type}",
        f"Post ID:      {result['post_id']}",
        f"Edit URL:     {result['notes']}",
        f"Cost:         ${result['cost']:.4f}",
        f"File:         {result['filepath'].relative_to(ROOT)}",
        "",
        f"Topics remaining in queue: {remaining}",
    ]
    if missed_warning:
        lines += ["", missed_warning]
    try:
        send_email(subject, '\n'.join(lines))
    except Exception as e:
        print(f"    → Email skipped: {e}")


def _email_failure(abbr: str, topic: str, error: str, missed_warning: str | None) -> None:
    subject = f"[{abbr.upper()}] Scheduled publish FAILED: {topic}"
    lines = [
        f"Scheduled publish failed — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Client: {abbr.upper()}",
        f"Topic:  {topic}",
        f"Error:  {error}",
    ]
    if missed_warning:
        lines += ["", missed_warning]
    try:
        send_email(subject, '\n'.join(lines))
    except Exception as e:
        print(f"    → Email skipped: {e}")


def _email_queue_empty(abbr: str) -> None:
    subject = f"[{abbr.upper()}] Topic queue is empty — no post published"
    body = (
        f"The scheduled publisher ran for {abbr.upper()} but the topic queue is empty.\n\n"
        f"Run the research script to add new topics:\n"
        f"  python3 src/research/research_blog_topics.py --abbr {abbr} --queue"
    )
    try:
        send_email(subject, body)
    except Exception as e:
        print(f"    → Email skipped: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(abbr: str, dry_run: bool = False, queue_name: str = 'topic-queue.json') -> None:
    abbr = abbr.lower()
    print(f"\n→ Scheduled publisher: {abbr.upper()}  [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")

    queue = load_queue(abbr, queue_name)
    cadence_days = queue.get('cadence_days', 7)
    missed_warning = check_missed_run(abbr, cadence_days)
    if missed_warning:
        print(f"  {missed_warning}")

    idx, topic_dict = next_pending(queue)
    if idx is None:
        print("→ Queue is empty — nothing to publish")
        append_log({
            'date': date.today().isoformat(),
            'abbr': abbr,
            'topic': '',
            'content_type': '',
            'status': 'queue_empty',
            'post_id': '',
            'cost': '',
            'notes': 'No pending topics',
        })
        return

    topic = topic_dict['topic']
    content_type = topic_dict.get('content_type', 'blog')
    remaining_before = pending_count(queue)

    print(f"→ Publishing [{content_type}]: {topic}")
    print(f"  ({remaining_before - 1} remaining after this)")

    try:
        result = publish_topic(topic_dict, abbr, dry_run=dry_run)

        # Update queue
        queue['topics'][idx]['status'] = result['status']
        queue['topics'][idx]['published_at'] = date.today().isoformat()
        queue['topics'][idx]['post_id'] = result['post_id']
        queue['topics'][idx]['cost'] = f"${result['cost']:.4f}" if result['cost'] else None
        if result['status'] not in ('published', 'published_review', 'dry_run'):
            queue['topics'][idx]['error'] = result.get('notes', '')
        if result['status'] == 'published_review':
            queue['topics'][idx]['error'] = result.get('notes', '')
        save_queue(abbr, queue, queue_name)

        # Log
        append_log({
            'date': date.today().isoformat(),
            'abbr': abbr,
            'topic': topic,
            'content_type': content_type,
            'status': result['status'],
            'post_id': result['post_id'] or '',
            'cost': f"${result['cost']:.4f}" if result['cost'] else '',
            'notes': result.get('notes', ''),
        })

        remaining_after = pending_count(queue)

        if result['status'] == 'published':
            print(f"✓ Done: {topic} (${result['cost']:.4f})")
        elif result['status'] == 'published_review':
            print(f"✎ Published for review: {topic} (${result['cost']:.4f})")
        elif result['status'] == 'dry_run':
            print(f"✓ Dry run complete: {topic}")
        else:
            print(f"⚠ Needs review: {topic} — {result.get('notes', '')}")

    except Exception as e:
        error_msg = str(e) or type(e).__name__
        tb = traceback.format_exc()
        print(f"✗ Failed: {topic} — {error_msg}")
        print(f"  {tb}")

        queue['topics'][idx]['status'] = 'failed'
        queue['topics'][idx]['error'] = error_msg
        save_queue(abbr, queue)

        append_log({
            'date': date.today().isoformat(),
            'abbr': abbr,
            'topic': topic,
            'content_type': content_type,
            'status': 'failed',
            'post_id': '',
            'cost': '',
            'notes': error_msg,
        })


STATUS_ICONS = {
    'published':        '✓',
    'published_review': '✎',
    'pending':          '·',
    'failed':           '✗',
    'review_required':  '⚠',
    'dry_run':          '~',
}


def show_status(abbr: str, queue_name: str = 'topic-queue.json') -> None:
    """Print a formatted queue status table."""
    abbr = abbr.lower()
    queue = load_queue(abbr, queue_name)
    topics = queue.get('topics', [])
    cadence_days = queue.get('cadence_days', 7)

    counts = {}
    for t in topics:
        s = t.get('status', 'pending')
        counts[s] = counts.get(s, 0) + 1

    last = last_published_date(abbr)
    if last:
        next_due = last + timedelta(days=cadence_days)
        days_until = (next_due.date() - date.today()).days
        schedule_str = (
            f"next due {next_due.strftime('%d %b')} "
            f"({'today' if days_until == 0 else f'in {days_until}d' if days_until > 0 else f'{-days_until}d overdue'})"
        )
    else:
        schedule_str = "no posts published yet"

    print(f"\n{abbr.upper()} topic queue  |  cadence: every {cadence_days}d  |  {schedule_str}")
    pub_count = counts.get('published', 0) + counts.get('published_review', 0)
    print(f"{'pending':<8} {counts.get('pending', 0)}  "
          f"{'published':<10} {pub_count}  "
          f"{'needs edit':<10} {counts.get('published_review', 0)}  "
          f"{'review':<8} {counts.get('review_required', 0)}  "
          f"{'failed':<7} {counts.get('failed', 0)}")
    print("─" * 72)

    for i, t in enumerate(topics, 1):
        status = t.get('status', 'pending')
        icon = STATUS_ICONS.get(status, '?')
        topic = t['topic']
        ctype = t.get('content_type', 'blog')
        pub_date = t.get('published_at') or ''
        post_id = t.get('post_id') or ''
        cost = t.get('cost') or ''
        error = t.get('error') or ''

        right = pub_date or (f"#{post_id}" if post_id else '') or (error[:30] if error else '')
        print(f"  {icon} {i:2}. {topic:<45}  [{ctype:<7}]  {right}")

    print("─" * 72)
    print(f"  Total: {len(topics)}  |  {counts.get('pending', 0)} remaining")
    print()


def main():
    parser = argparse.ArgumentParser(description='Publish next scheduled post from queue')
    parser.add_argument('--abbr', required=True, help='Client abbreviation e.g. gtb')
    parser.add_argument('--dry-run', action='store_true',
                        help='Generate and quality-check content but skip WordPress publish')
    parser.add_argument('--status', action='store_true',
                        help='Show queue status table without publishing anything')
    parser.add_argument('--queue', default='topic-queue.json',
                        help='Queue filename (default: topic-queue.json, e.g. comp-alt-queue.json)')
    args = parser.parse_args()
    if args.status:
        show_status(args.abbr, args.queue)
    else:
        run(args.abbr, dry_run=args.dry_run, queue_name=args.queue)


if __name__ == '__main__':
    main()
