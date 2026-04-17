"""
Competitor citation gap analysis.

Fetches top N GBP competitors, checks which known citation sites they appear on
but the client doesn't, and optionally discovers new directories via backlinks.

Usage:
    python3 src/research/research_citation_gaps.py --abbr sdy
    python3 src/research/research_citation_gaps.py --abbr sdy --top 10
    python3 src/research/research_citation_gaps.py --abbr sdy --dry-run
    python3 src/research/research_citation_gaps.py --abbr sdy --discover
"""

from __future__ import annotations
import argparse
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

from dataforseo import DataForSEO
from citation_sites import CITATION_SITES

_DIRECTORY_SIGNALS = [
    'directory', 'listing', 'local', 'find', 'search', 'pages', 'guide',
    'index', 'register', 'business', 'trade', 'map', 'therapist', 'holistic',
    'wellness', 'health', 'therapy', 'massage',
]
_EXCLUDE_DOMAINS = {
    'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
    'youtube.com', 'tiktok.com', 'pinterest.com', 'reddit.com',
    'google.com', 'apple.com', 'microsoft.com', 'bbc.co.uk',
    'gov.uk', 'nhs.uk', 'wikipedia.org', 'amazon.co.uk',
    'wix.com', 'squarespace.com', 'wordpress.com', 'blogger.com',
}


def _domain(url: str) -> str:
    if not url:
        return ''
    try:
        parsed = urlparse(url if '://' in url else f'https://{url}')
        return parsed.netloc.lstrip('www.')
    except Exception:
        return ''


def _clean_area(area: str) -> str:
    """Strip 'City Centre' / 'Town Centre' suffixes — bare city name geocodes better."""
    import re
    return re.sub(r'\s+(city|town)\s+centre\b', '', area, flags=re.IGNORECASE).strip()


def get_competitors(dfs: DataForSEO, config: dict, top_n: int) -> list[dict]:
    keyword = (
        config.get('main_keyword')
        or config.get('keyword_prefix')
        or f"massage therapy {_clean_area(config.get('area', config.get('city', '')))}"
    )
    raw_area = config.get('area', config.get('city', 'Glasgow'))
    city = _clean_area(raw_area)
    location_name = f"{city},Scotland,United Kingdom"
    our_domain = _domain(config.get('website', ''))

    results = dfs.get_maps_pack(keyword, location_name=location_name, limit=top_n + 5)
    competitors = []
    for r in results:
        comp_domain = _domain(r.get('url', ''))
        if comp_domain and comp_domain != our_domain:
            r['_domain'] = comp_domain
            competitors.append(r)
        if len(competitors) >= top_n:
            break
    return competitors


# GBP presence is verified via API separately — SERP method produces false negatives
_SKIP_SERP_CHECK = {'google_business_profile'}


def check_known_sites(
    dfs: DataForSEO,
    competitors: list[dict],
    our_state: dict,
    dry_run: bool = False,
) -> list[dict]:
    our_found = {sid for sid, d in our_state.items() if d.get('status') == 'found'}
    gaps = []

    for site in CITATION_SITES:
        if site.id in _SKIP_SERP_CHECK:
            continue
        site_domain = _domain(site.url)
        if not site_domain:
            continue

        competitor_count = 0
        for comp in competitors:
            name = comp.get('name', '')
            if not name:
                continue
            query = f'"{name}" site:{site_domain}'
            if dry_run:
                print(f'  [dry-run] {query}')
                continue
            try:
                results = dfs.get_organic_serp(query, limit=3)
                if results:
                    competitor_count += 1
            except Exception as e:
                print(f'  Warning: SERP failed for {site.name}: {e}')

        if dry_run:
            continue

        if competitor_count > 0:
            gaps.append({
                'site_id': site.id,
                'site_name': site.name,
                'site_url': site.url,
                'submission_url': site.submission_url,
                'competitor_count': competitor_count,
                'total_competitors': len(competitors),
                'our_status': 'found' if site.id in our_found else 'not_found',
            })

    gaps.sort(key=lambda x: (x['our_status'] == 'found', -x['competitor_count']))
    return gaps


def discover_new_sites(
    dfs: DataForSEO,
    competitors: list[dict],
    dry_run: bool = False,
) -> list[dict]:
    known_domains = {_domain(s.url) for s in CITATION_SITES}
    domain_counts: dict[str, int] = {}

    for comp in competitors:
        comp_domain = comp.get('_domain', '')
        if not comp_domain:
            continue
        if dry_run:
            print(f'  [dry-run] backlinks: {comp_domain}')
            continue
        try:
            referring = dfs.get_referring_domains(comp_domain, limit=100)
            for ref in referring:
                ref_clean = ref.lstrip('www.')
                if ref_clean in known_domains:
                    continue
                if any(ref_clean.endswith(excl) or excl in ref_clean for excl in _EXCLUDE_DOMAINS):
                    continue
                if any(sig in ref_clean for sig in _DIRECTORY_SIGNALS):
                    domain_counts[ref_clean] = domain_counts.get(ref_clean, 0) + 1
        except Exception as e:
            print(f'  Warning: backlinks failed for {comp_domain}: {e}')

    discovered = [
        {'domain': d, 'competitor_count': c}
        for d, c in domain_counts.items()
        if c >= 2
    ]
    discovered.sort(key=lambda x: -x['competitor_count'])
    return discovered


def _bar(count: int, total: int, width: int = 8) -> str:
    filled = round((count / total) * width) if total else 0
    return '█' * filled + '░' * (width - filled)


def write_report(
    abbr: str,
    config: dict,
    competitors: list[dict],
    gaps: list[dict],
    discovered: list[dict],
    root: Path,
) -> Path:
    name = config.get('name', abbr.upper())
    out_dir = root / 'research' / abbr
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'citation-gaps-{date.today().isoformat()}.md'

    lines = [
        f'# Citation Gap Analysis — {name}',
        f'',
        f'Generated: {date.today().isoformat()}  ',
        f'Competitors analysed: {len(competitors)}',
        '',
        '## Competitors',
        '',
    ]
    for i, c in enumerate(competitors, 1):
        lines.append(f'{i}. **{c["name"]}** — {c.get("_domain", "?")} (rating: {c.get("rating", "?")})')

    action_gaps = [g for g in gaps if g['our_status'] == 'not_found']
    covered = [g for g in gaps if g['our_status'] == 'found']

    lines += [
        '',
        f'## Citation Gaps — {len(action_gaps)} sites where competitors appear but you don\'t',
        '',
        f'{"Site":<32} {"Coverage":<22} Submission URL',
        '─' * 90,
    ]
    for g in action_gaps:
        bar = _bar(g['competitor_count'], g['total_competitors'])
        cov = f'{bar} {g["competitor_count"]}/{g["total_competitors"]}'
        lines.append(f'{g["site_name"]:<32} {cov:<22} {g["submission_url"]}')

    if covered:
        lines += ['', '## Already Listed (you and competitors share these)', '']
        for g in covered:
            bar = _bar(g['competitor_count'], g['total_competitors'])
            lines.append(f'- {g["site_name"]:<30} {bar} {g["competitor_count"]}/{g["total_competitors"]}')

    if discovered:
        lines += [
            '',
            '## Discovered Sites (not in standard list — 2+ competitors linked here)',
            '',
        ]
        for d in discovered:
            lines.append(f'- {d["domain"]} — {d["competitor_count"]}/{len(competitors)} competitors')

    out_path.write_text('\n'.join(lines) + '\n')
    return out_path


def run(abbr: str, top_n: int = 5, discover: bool = False, dry_run: bool = False, root: Path = ROOT) -> dict:
    """Callable entry point for citation_manager integration."""
    config_path = root / 'clients' / abbr / 'config.json'
    config = json.loads(config_path.read_text())

    state_path = root / 'clients' / abbr / 'citations' / 'state.json'
    our_state = {}
    if state_path.exists():
        our_state = json.loads(state_path.read_text()).get('sites', {})

    dfs = DataForSEO()

    print(f'  → Fetching top {top_n} GBP competitors...')
    competitors = get_competitors(dfs, config, top_n)
    print(f'  → Found {len(competitors)} competitors — checking {len(CITATION_SITES)} citation sites...')

    gaps = check_known_sites(dfs, competitors, our_state, dry_run=dry_run)

    discovered = []
    if discover and not dry_run:
        print('  → Running backlinks discovery...')
        discovered = discover_new_sites(dfs, competitors)

    result = {
        'generated': date.today().isoformat(),
        'competitors': [{'name': c['name'], 'domain': c.get('_domain', '')} for c in competitors],
        'gaps': gaps,
        'discovered': discovered,
    }

    if not dry_run:
        gap_path = root / 'clients' / abbr / 'citations' / 'gap-results.json'
        gap_path.parent.mkdir(parents=True, exist_ok=True)
        gap_path.write_text(json.dumps(result, indent=2))

        out_path = write_report(abbr, config, competitors, gaps, discovered, root)
        action_count = len([g for g in gaps if g['our_status'] == 'not_found'])
        print(f'  → {action_count} gap(s) found — report: {out_path}')

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--abbr', required=True)
    parser.add_argument('--top', type=int, default=5)
    parser.add_argument('--discover', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if args.dry_run:
        config = json.loads((ROOT / 'clients' / args.abbr / 'config.json').read_text())
        dfs = DataForSEO()
        fake_competitors = [{'name': 'Demo Competitor', '_domain': 'example.co.uk'}]
        print(f'[dry-run] SERP queries that would be made ({len(CITATION_SITES)} sites × competitors):')
        check_known_sites(dfs, fake_competitors, {}, dry_run=True)
        if args.discover:
            discover_new_sites(dfs, fake_competitors, dry_run=True)
        return

    run(abbr=args.abbr, top_n=min(args.top, 10), discover=args.discover)


if __name__ == '__main__':
    main()
