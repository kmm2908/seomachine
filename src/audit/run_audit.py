#!/usr/bin/env python3
"""
SEO Machine Audit

Runs a full 6-category SEO audit for a client and produces:
  1. Internal markdown report   audits/[abbr]/[date]/audit-internal.md
  2. Prospect PDF               audits/[abbr]/[date]/audit-prospect.pdf
  3. Pending content queue      audits/[abbr]/[date]/pending-queue.json

Usage:
    python3 src/audit/run_audit.py --abbr gtm
    python3 src/audit/run_audit.py --abbr gtm --no-pdf        # skip PDF
    python3 src/audit/run_audit.py --abbr gtm --no-email      # skip email
    python3 src/audit/run_audit.py --url https://example.com  # prospect (no client config needed)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

from scoring import (
    AuditResult, SchemaResult, ContentResult, GBPResult,
    ReviewResult, NAPResult, TechnicalResult, CompetitorResult,
)
from collectors import (
    collect_schema, collect_content, collect_gbp, collect_reviews,
    collect_nap, collect_citations, collect_technical, collect_competitor,
    _get_with_fallback as _prime_fallback_cache,
)
from report import build_markdown, build_prospect_html
from pdf_gen import generate_pdf
from queue_gen import build_pending_queue

EMAIL_RECIPIENT = os.getenv('EMAIL_TO', 'kmmsubs@gmail.com')
SEND_EMAIL_PATH = Path.home() / '.claude' / 'utils' / 'send_email.py'


def _load_config(abbr: str) -> dict:
    config_path = ROOT / 'clients' / abbr / 'config.json'
    if not config_path.exists():
        raise FileNotFoundError(f'Client config not found: {config_path}')
    return json.loads(config_path.read_text())


def _minimal_config(url: str, name: str) -> dict:
    """Build a minimal config for a prospect-only audit (no client folder)."""
    return {
        'name': name or url,
        'abbreviation': 'prospect',
        'website': url,
        'wordpress': {'url': url},
    }


def _print_summary(result: AuditResult) -> None:
    g = result.grade_letter
    s = result.total_score
    bar = '█' * (s // 5) + '░' * (20 - s // 5)
    print(f'\n╔══════════════════════════════════════════════════════╗')
    print(f'║  SEO AUDIT: {result.site_name:<39} ║')
    print(f'╠══════════════════════════════════════════════════════╣')
    print(f'║  Score: {s:>3}/100  Grade: {g}  [{bar}] ║')
    print(f'╠══════════════════════════════════════════════════════╣')
    cats = [
        ('Schema',    result.schema.score,    20),
        ('Content',   result.content.score,   20),
        ('GBP',       result.gbp.score,       20),
        ('Reviews',   result.reviews.score,   15),
        ('NAP+Cit',   result.nap.score,       15),
        ('Technical', result.technical.score, 10),
    ]
    for label, sc, mx in cats:
        bar_c = '█' * int((sc / mx) * 10) + '░' * (10 - int((sc / mx) * 10))
        print(f'║  {label:<10} {sc:>2}/{mx:<2}  [{bar_c}]               ║')
    print(f'╚══════════════════════════════════════════════════════╝\n')

    # Top findings
    all_findings = (
        result.schema.findings + result.content.findings + result.gbp.findings
        + result.reviews.findings + result.nap.findings + result.technical.findings
    )
    if all_findings:
        print('Top issues:')
        for f in all_findings[:5]:
            print(f'  ✗ {f}')
        remainder = len(all_findings) - 5
        if remainder > 0:
            print(f'  … and {remainder} more (see full report)')
    print()


def run_audit(
    abbr: str | None = None,
    url: str | None = None,
    site_name: str | None = None,
    send_email: bool = True,
    generate_pdf_flag: bool = True,
    run_crawl: bool = False,
) -> AuditResult:

    today = str(date.today())

    # Load or build config
    if abbr:
        config = _load_config(abbr)
        site_name = site_name or config.get('name', abbr.upper())
        site_url = url or config.get('website') or config.get('wordpress', {}).get('url', '')
        wp_config = config.get('wordpress')
        out_dir = ROOT / 'audits' / abbr / today
    else:
        config = _minimal_config(url, site_name or url)
        abbr = 'prospect'
        site_url = url
        wp_config = {'url': url}
        out_dir = ROOT / 'audits' / 'prospect' / today

    out_dir.mkdir(parents=True, exist_ok=True)

    if not site_url:
        raise ValueError('No site URL found in config. Pass --url or add `website` to config.json.')

    logger.info(f'Auditing {site_name} ({site_url})')

    # Prime the SSH + site_url caches in collectors before any collection starts.
    # All subsequent _get_with_fallback() calls inherit these automatically.
    ssh_config = config.get('ssh')
    if ssh_config:
        logger.info(f'SSH tunnel available: {ssh_config["user"]}@{ssh_config["host"]}')
    _prime_fallback_cache.__module__  # no-op import check
    import collectors as _collectors_mod
    _collectors_mod._SITE_URL_CACHE = site_url
    _collectors_mod._SSH_CONFIG_CACHE = ssh_config

    # ── Collect ──────────────────────────────────────────────────────────────
    logger.info('Collecting schema data...')
    schema = collect_schema(site_url, wp_config=wp_config)

    logger.info('Collecting content data...')
    content = collect_content(site_url, wp_config, config=config)

    logger.info('Collecting GBP data...')
    gbp = collect_gbp(config)

    logger.info('Collecting review data...')
    reviews = collect_reviews(config)

    logger.info('Collecting NAP data...')
    nap_schema = collect_nap(config, schema, site_url, wp_config=wp_config)

    # Run citation audit if client abbreviation is available
    if config.get('abbreviation'):
        logger.info('Collecting citation data...')
        nap = collect_citations(config, ROOT)
        # Carry schema NAP findings into CitationResult
        nap.schema_name_match = getattr(nap_schema, 'name_match', 'unknown')
        nap.schema_address_match = getattr(nap_schema, 'address_match', 'unknown')
        nap.schema_phone_match = getattr(nap_schema, 'phone_match', 'unknown')
        nap.findings = nap_schema.findings + nap.findings
        nap.compute_score()
    else:
        nap = nap_schema

    crawl_report = None
    if run_crawl:
        import asyncio as _asyncio
        from dataclasses import asdict as _asdict
        from src.audit.crawler import crawl as _run_crawl, save_crawl_report as _save_report
        print("→ Running site crawler...")
        _crawl_result = _asyncio.run(_run_crawl(site_url))
        _save_report(_crawl_result, out_dir)
        crawl_report = _asdict(_crawl_result)

    logger.info('Collecting technical data...')
    technical = collect_technical(site_url, wp_config=wp_config, crawl_report=crawl_report)

    logger.info('Collecting competitor data...')
    competitor = collect_competitor(abbr) if abbr != 'prospect' else CompetitorResult()

    # ── Score ────────────────────────────────────────────────────────────────
    result = AuditResult(
        abbr=abbr,
        site_name=site_name,
        site_url=site_url,
        date=today,
        schema=schema,
        content=content,
        gbp=gbp,
        reviews=reviews,
        nap=nap,
        technical=technical,
        competitor=competitor,
    )
    result.compute_totals()

    _print_summary(result)

    # ── Build reports ────────────────────────────────────────────────────────
    logger.info('Building internal report...')
    md = build_markdown(result)
    md_path = out_dir / 'audit-internal.md'
    md_path.write_text(md, encoding='utf-8')
    logger.info(f'Internal report → {md_path}')

    logger.info('Building prospect HTML...')
    html = build_prospect_html(result)
    html_path = out_dir / 'audit-prospect.html'
    html_path.write_text(html, encoding='utf-8')
    logger.info(f'Prospect HTML → {html_path}')

    # ── PDF ──────────────────────────────────────────────────────────────────
    pdf_path = out_dir / 'audit-prospect.pdf'
    if generate_pdf_flag:
        logger.info('Generating PDF...')
        ok = generate_pdf(html, pdf_path)
        if ok:
            logger.info(f'PDF → {pdf_path}')
        else:
            logger.warning('PDF generation failed — HTML file saved instead.')
            pdf_path = html_path   # fall back to HTML for email
    else:
        pdf_path = html_path

    # ── Pending queue ────────────────────────────────────────────────────────
    logger.info('Building pending content queue...')
    queue = build_pending_queue(result)
    queue_path = out_dir / 'pending-queue.json'
    queue_path.write_text(
        json.dumps(queue, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    logger.info(f'Pending queue ({len(queue)} items) → {queue_path}')

    # ── API cache ────────────────────────────────────────────────────────────
    if abbr != 'prospect':
        from dataclasses import asdict as _dc_asdict
        cache_path = ROOT / 'clients' / abbr / 'audit-latest.json'
        cache_path.write_text(
            json.dumps(_dc_asdict(result), indent=2, ensure_ascii=False),
            encoding='utf-8',
        )
        logger.info(f'API cache → {cache_path}')

    # ── Email ────────────────────────────────────────────────────────────────
    if send_email:
        _send_report_email(result, pdf_path, md_path)

    return result


def _send_report_email(result: AuditResult, pdf_path: Path, md_path: Path) -> None:
    if not SEND_EMAIL_PATH.exists():
        logger.warning(f'send_email.py not found at {SEND_EMAIL_PATH} — email skipped.')
        return

    subject = (
        f'SEO Audit: {result.site_name} — '
        f'{result.total_score}/100 (Grade {result.grade_letter})'
    )
    body = (
        f'SEO Audit complete for {result.site_name}.\n\n'
        f'Score: {result.total_score}/100  Grade: {result.grade_letter}\n'
        f'Date: {result.date}\n\n'
        f'Outputs saved to: audits/{result.abbr}/{result.date}/\n'
        f'  - audit-internal.md\n'
        f'  - audit-prospect.pdf (or .html)\n'
        f'  - pending-queue.json\n\n'
        f'--- Top Issues ---\n'
    )
    all_findings = (
        result.schema.findings + result.content.findings + result.gbp.findings
        + result.reviews.findings + result.nap.findings + result.technical.findings
    )
    for f in all_findings[:8]:
        body += f'• {f}\n'

    cmd = [
        sys.executable, str(SEND_EMAIL_PATH),
        '--to', EMAIL_RECIPIENT,
        '--subject', subject,
        '--body', body,
    ]

    # Attach PDF if it's a real PDF file
    if pdf_path.suffix == '.pdf' and pdf_path.exists():
        cmd += ['--attachment', str(pdf_path)]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            logger.info(f'Audit report emailed to {EMAIL_RECIPIENT}')
        else:
            logger.warning(f'Email failed: {res.stderr}')
    except Exception as e:
        logger.warning(f'Email error: {e}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Run SEO audit for a client.')
    parser.add_argument('--abbr', help='Client abbreviation (e.g. gtm, sdy)')
    parser.add_argument('--url', help='Site URL (for prospect audit without client config)')
    parser.add_argument('--name', help='Business name (for prospect audit)')
    parser.add_argument('--no-pdf', action='store_true', help='Skip PDF generation')
    parser.add_argument('--no-email', action='store_true', help='Skip email delivery')
    parser.add_argument('--crawl', action='store_true',
                        help='Run site crawler before audit and include findings in report')
    args = parser.parse_args()

    if not args.abbr and not args.url:
        parser.error('Provide either --abbr (existing client) or --url (prospect).')

    run_audit(
        abbr=args.abbr,
        url=args.url,
        site_name=args.name,
        send_email=not args.no_email,
        generate_pdf_flag=not args.no_pdf,
        run_crawl=getattr(args, 'crawl', False),
    )


if __name__ == '__main__':
    main()
