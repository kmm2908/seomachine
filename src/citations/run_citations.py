#!/usr/bin/env python3
"""
Citation Generator & Listing Audit

Usage:
    python3 src/citations/run_citations.py --abbr gtm
    python3 src/citations/run_citations.py --abbr gtm --mode audit
    python3 src/citations/run_citations.py --abbr gtm --mode create
    python3 src/citations/run_citations.py --abbr gtm --status
    python3 src/citations/run_citations.py --abbr gtm --dry-run
    python3 src/citations/run_citations.py --abbr gtm --force
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))
sys.path.insert(0, str(ROOT / 'src' / 'audit'))

from citation_manager import CitationManager

logging.basicConfig(level=logging.INFO, format='%(levelname)s  %(message)s')
logger = logging.getLogger(__name__)


def load_config(abbr: str) -> dict:
    config_path = ROOT / 'clients' / abbr / 'config.json'
    if not config_path.exists():
        print(f'Error: clients/{abbr}/config.json not found')
        sys.exit(1)
    return json.loads(config_path.read_text())


def main():
    parser = argparse.ArgumentParser(description='Citation audit and creation tool')
    parser.add_argument('--abbr', required=True, help='Client abbreviation (e.g. gtm)')
    parser.add_argument('--mode', choices=['audit', 'create', 'full'], default='full',
                        help='Run mode: audit (check only), create (submit missing), full (both)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Check and generate pack but do not submit to any sites')
    parser.add_argument('--force', action='store_true',
                        help='Re-check all sites regardless of last_checked date')
    parser.add_argument('--status', action='store_true',
                        help='Print citation status table and exit')
    args = parser.parse_args()

    config = load_config(args.abbr)
    manager = CitationManager(args.abbr, config, ROOT)

    if args.status:
        manager.print_status()
        return

    if args.mode == 'audit':
        result = manager.run_audit(force=args.force, dry_run=args.dry_run)
    elif args.mode == 'create':
        submitted = manager.run_creation(dry_run=args.dry_run)
        print(f'\n→ Submitted {len(submitted)} listings')
        manual = [r for r in submitted if r.submit_status == 'manual_required']
        if manual:
            print(f'  ✎ {len(manual)} require manual submission — see clients/{args.abbr}/citations/manual-pack.html')
        return
    else:  # full
        result = manager.run_full(force=args.force, dry_run=args.dry_run)

    # Print summary
    print(
        f'\n→ Citations: {result.found_count}/{result.total_sites} found'
        f' | {result.nap_issue_count} NAP issues'
        f' | {result.duplicate_count} duplicates'
        f' | score {result.score}/15'
    )
    if result.findings:
        for f in result.findings[:5]:
            print(f'  ✗ {f}')
        if len(result.findings) > 5:
            print(f'  … and {len(result.findings) - 5} more')

    if args.dry_run:
        print('\n[dry-run] No submissions made.')


if __name__ == '__main__':
    main()
