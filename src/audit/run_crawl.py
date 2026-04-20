#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT))

from src.audit.crawler import crawl, save_crawl_report, save_crawl_summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crawl a WordPress site for SEO issues."
    )
    parser.add_argument(
        "--abbr", required=True, help="Client abbreviation (e.g. gtm, sdy)"
    )
    parser.add_argument(
        "--max-pages", type=int, default=500, help="Maximum pages to crawl (default: 500)"
    )
    parser.add_argument(
        "--concurrency", type=int, default=10,
        help="Concurrent requests (default: 10)"
    )
    parser.add_argument(
        "--delay", type=float, default=0.1,
        help="Seconds between request batches (default: 0.1)"
    )
    parser.add_argument(
        "--output", help="Output directory (default: audits/[abbr]/[date])"
    )
    args = parser.parse_args()

    config_path = ROOT / "clients" / args.abbr / "config.json"
    if not config_path.exists():
        print(f"Error: no config found at {config_path}", file=sys.stderr)
        sys.exit(1)

    config = json.loads(config_path.read_text())
    site_url = config["wordpress"]["url"]

    output_dir = (
        Path(args.output) if args.output
        else ROOT / "audits" / args.abbr / date.today().isoformat()
    )

    print(f"→ Crawling {site_url}...")
    result = asyncio.run(
        crawl(
            site_url,
            max_pages=args.max_pages,
            concurrency=args.concurrency,
            delay=args.delay,
        )
    )

    s = result.stats
    iss = result.issues
    critical = len(iss.pages_4xx) + len(iss.redirect_chains) + len(iss.broken_resources)
    warnings = len(iss.https_issues) + len(iss.orphan_pages) + len(iss.missing_h1)
    info = (
        len(iss.missing_title) + len(iss.title_too_long) + len(iss.duplicate_titles)
        + len(iss.missing_meta) + len(iss.meta_too_long) + len(iss.duplicate_meta)
        + len(iss.multiple_h1)
    )

    print(
        f"→ Pages: {s.total_pages} crawled | "
        f"200: {s.pages_200} · 3xx: {s.pages_3xx} · "
        f"4xx: {s.pages_4xx} · 5xx: {s.pages_5xx}"
    )
    print(f"→ Issues: {critical} critical · {warnings} warnings · {info} info")

    json_path = save_crawl_report(result, output_dir)
    md_path = save_crawl_summary(result, output_dir)
    print(f"→ Saved: {json_path}")
    print(f"→ Saved: {md_path}")


if __name__ == "__main__":
    main()
