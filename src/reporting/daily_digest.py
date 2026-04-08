#!/usr/bin/env python3
"""
Daily Digest — scheduled publish summary email.

Reads logs/scheduled-publish-log.csv, groups today's activity by client,
and sends one summary email covering publishes, review items, and failures.

Usage:
    python3 src/reporting/daily_digest.py              # today's activity
    python3 src/reporting/daily_digest.py --date 2026-04-07  # specific date
    python3 src/reporting/daily_digest.py --dry-run    # print email, don't send
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))

LOG_PATH = ROOT / 'logs' / 'scheduled-publish-log.csv'
RECIPIENT = 'kmmsubs@gmail.com'

# Statuses to skip entirely — not meaningful for a digest
SKIP_STATUSES = {'dry_run', 'queue_empty', 'review_required'}

# Human-readable client names
CLIENT_NAMES = {
    'gtm': 'Glasgow Thai Massage',
    'gtb': 'Glasgow Thai Massage Blog',
    'sdy': 'Serendipity Massage',
    'tmg': 'Thai Massage Greenock',
    'tmb': 'Thai Massage Greenock Blog',
}


def load_rows(target_date: str) -> dict[str, list[dict]]:
    """Read CSV and return rows for target_date, grouped by abbr."""
    if not LOG_PATH.exists():
        return {}

    by_client: dict[str, list[dict]] = defaultdict(list)

    with open(LOG_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['date'] != target_date:
                continue
            if row['status'] in SKIP_STATUSES:
                continue
            by_client[row['abbr'].lower()].append(row)

    return dict(by_client)


def build_email(target_date: str, by_client: dict[str, list[dict]]) -> tuple[str, str]:
    """Return (subject, body) for the digest email."""
    if not by_client:
        subject = f'SEO Machine — No activity on {target_date}'
        body = f'No content was published or attempted on {target_date}.\n'
        return subject, body

    # Totals across all clients
    total_published = 0
    total_review = 0
    total_failed = 0
    total_cost = 0.0

    client_sections = []

    for abbr in sorted(by_client):
        rows = by_client[abbr]
        name = CLIENT_NAMES.get(abbr, abbr.upper())

        published = [r for r in rows if r['status'] == 'published']
        needs_review = [r for r in rows if r['status'] == 'published_review']
        failed = [r for r in rows if r['status'] == 'failed']

        client_cost = sum(
            float(r['cost'].replace('$', '')) for r in rows if r['cost']
        )

        total_published += len(published)
        total_review += len(needs_review)
        total_failed += len(failed)
        total_cost += client_cost

        lines = [f'── {name} ──']

        if published:
            lines.append(f'  ✓ Published ({len(published)}):')
            for r in published:
                cost_str = r['cost'] if r['cost'] else ''
                post_id = f'  post {r["post_id"]}' if r['post_id'] else ''
                lines.append(f'    • {r["topic"]} [{r["content_type"]}]{post_id}  {cost_str}')
                if r['notes'] and r['notes'].startswith('http'):
                    lines.append(f'      {r["notes"]}')

        if needs_review:
            lines.append(f'  ✎ Needs review ({len(needs_review)}):')
            for r in needs_review:
                lines.append(f'    • {r["topic"]} [{r["content_type"]}]')
                if r['notes']:
                    # notes format: "Quality gate: hook | https://..."
                    parts = r['notes'].split(' | ')
                    lines.append(f'      Reason: {parts[0]}')
                    if len(parts) > 1:
                        lines.append(f'      {parts[1]}')

        if failed:
            lines.append(f'  ✗ Failed ({len(failed)}):')
            for r in failed:
                # Truncate long error messages
                err = r['notes'][:120] + '...' if len(r.get('notes', '')) > 120 else r.get('notes', '')
                lines.append(f'    • {r["topic"]} [{r["content_type"]}]')
                if err:
                    lines.append(f'      {err}')

        lines.append(f'  Cost: ${client_cost:.4f}')
        client_sections.append('\n'.join(lines))

    # Summary line
    summary_parts = []
    if total_published:
        summary_parts.append(f'{total_published} published')
    if total_review:
        summary_parts.append(f'{total_review} need review')
    if total_failed:
        summary_parts.append(f'{total_failed} failed')

    summary = ' · '.join(summary_parts) if summary_parts else 'no activity'

    subject = f'SEO Machine {target_date} — {summary}  (${total_cost:.2f})'

    body_lines = [
        f'SEO Machine Daily Digest — {target_date}',
        f'{"=" * 50}',
        f'Total: {summary}  |  Cost: ${total_cost:.4f}',
        '',
    ]
    body_lines.extend('\n'.join(client_sections).split('\n'))
    body_lines += ['', f'{"=" * 50}', 'Log: logs/scheduled-publish-log.csv']

    body = '\n'.join(body_lines)
    return subject, body


def main() -> None:
    parser = argparse.ArgumentParser(description='Send daily SEO Machine digest email')
    parser.add_argument('--date', default=str(date.today()), help='Date to report on (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', help='Print email instead of sending')
    args = parser.parse_args()

    by_client = load_rows(args.date)
    subject, body = build_email(args.date, by_client)

    print(f'Subject: {subject}')
    print('-' * 60)
    print(body)
    print('-' * 60)

    if args.dry_run:
        print('(dry-run — email not sent)')
        return

    # Use the global send_email utility
    send_email_path = Path.home() / '.claude' / 'utils' / 'send_email.py'
    if not send_email_path.exists():
        print(f'ERROR: send_email.py not found at {send_email_path}', file=sys.stderr)
        sys.exit(1)

    import subprocess
    result = subprocess.run(
        [sys.executable, str(send_email_path),
         '--to', RECIPIENT,
         '--subject', subject,
         '--body', body],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f'Email sent to {RECIPIENT}')
    else:
        print(f'ERROR sending email: {result.stderr}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
