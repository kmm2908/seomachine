"""
Blog Topic Research

Generates a prioritised list of blog post topic ideas based on:
  - Client GBP categories and services (from config.json)
  - Niche-level keyword research via DataForSEO (cached 30 days)
  - Competitor SERP presence (using profiles from competitor-analysis.md)

Niche cache lives in research/niches/[niche]/ and is shared across all clients
in the same niche (e.g. GTM and GTB both use thai-massage cache).

Usage:
    python3 src/research/research_blog_topics.py --abbr gtb
    python3 src/research/research_blog_topics.py --abbr gtm --limit 30
    python3 src/research/research_blog_topics.py --abbr gtb --sheet
    python3 src/research/research_blog_topics.py --abbr gtb --refresh
    python3 src/research/research_blog_topics.py --abbr gtb --queue           # create queue (7-day cadence)
    python3 src/research/research_blog_topics.py --abbr gtb --queue --cadence 14
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

from dataforseo import DataForSEO

# --- Constants ---
CACHE_TTL_DAYS = 30
UK_LOCATION_CODE = 2826      # United Kingdom
MIN_VOLUME = 50              # exclude keywords with fewer monthly searches
MAX_COMPETITION = 0.40       # DataForSEO competition index 0–1 (proxy for difficulty)

# Informational intent signals — keywords containing these are blog/topical candidates
INFORMATIONAL_SIGNALS = [
    'how ', 'what ', 'why ', 'when ', 'where ', 'who ',
    'benefits', 'tips', 'guide', 'advice', ' vs ', 'versus',
    'difference', 'types of', 'best ', 'does ', 'is it',
    'should ', 'can ', 'effects', 'help with', 'work for',
    'explained', 'treatment', 'therapy', 'relief for', 'for back',
    'for stress', 'for anxiety', 'for sleep', 'for pain', 'for athletes',
    'to expect', 'first time', 'how often', 'how long',
]

# Location-specific terms — skip these for blog content (use for location pages instead)
LOCATION_SIGNALS = [
    'near me', 'near you', 'glasgow', 'edinburgh', 'london', 'manchester',
    'birmingham', 'leeds', 'bristol', 'city centre', 'city center',
]


# ---------------------------------------------------------------------------
# Config and context loading
# ---------------------------------------------------------------------------

def load_config(abbr: str) -> dict:
    path = ROOT / 'clients' / abbr.lower() / 'config.json'
    with open(path) as f:
        return json.load(f)


def load_competitor_domains(abbr: str) -> list:
    """Extract competitor domains from competitor-analysis.md."""
    path = ROOT / 'clients' / abbr.lower() / 'competitor-analysis.md'
    if not path.exists():
        return []

    content = path.read_text()
    domains = re.findall(r'https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', content)

    # Strip the client's own domains and generic directories
    own = {
        'glasgowthaimassage.co.uk', 'blog.glasgowthaimassage.co.uk',
        'blogglasgowthaimassage.co.uk', 'serendipitymassage.co.uk',
    }
    skip_patterns = ['google.', 'facebook.', 'instagram.', 'twitter.', 'youtube.',
                     'yelp.', 'tripadvisor.', 'yell.', 'thomsonlocal.', 'scoot.',
                     'cylex.', 'freeindex.', 'hotfrog.']

    seen = set()
    result = []
    for d in domains:
        d = d.lower()
        if d in own or d in seen:
            continue
        if any(p in d for p in skip_patterns):
            continue
        seen.add(d)
        result.append(d)

    return result[:20]


# ---------------------------------------------------------------------------
# Seed keyword generation
# ---------------------------------------------------------------------------

def build_seeds(config: dict) -> list:
    """Build seed keywords from client config fields."""
    seeds = set()
    prefix = config.get('keyword_prefix', '')   # e.g. "thai massage"
    services = config.get('services', [])

    if prefix:
        seeds.update([
            prefix,
            f"benefits of {prefix}",
            f"what is {prefix}",
            f"{prefix} benefits",
            f"how does {prefix} work",
            f"types of {prefix}",
            f"what to expect from {prefix}",
            f"{prefix} for back pain",
            f"{prefix} for stress",
            f"{prefix} for anxiety",
            f"{prefix} for sleep",
            f"{prefix} vs swedish massage",
            f"how often should you get {prefix}",
            f"is {prefix} painful",
            f"{prefix} for first time",
        ])

    for svc in services[:6]:
        svc = svc.lower()
        seeds.update([
            svc,
            f"benefits of {svc}",
            f"{svc} for back pain",
            f"what is {svc}",
        ])

    return list(seeds)


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------

def is_informational(keyword: str) -> bool:
    kw = keyword.lower()
    return any(signal in kw for signal in INFORMATIONAL_SIGNALS)


def has_location_intent(keyword: str) -> bool:
    kw = keyword.lower()
    return any(signal in kw for signal in LOCATION_SIGNALS)


def passes_thresholds(kw: dict) -> bool:
    volume = kw.get('search_volume') or 0
    competition = kw.get('competition') or 0
    return volume >= MIN_VOLUME and competition <= MAX_COMPETITION


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_topic(kw: dict, competitor_domains: list, serp_results: list) -> float:
    """
    Score = volume × difficulty_factor × gap_bonus

    difficulty_factor: lower competition → higher score
    gap_bonus: more known competitors ranking → bigger opportunity signal
    """
    volume = kw.get('search_volume') or 0
    competition = kw.get('competition') or 0.5

    serp_domains = [r.get('domain', '').lower() for r in serp_results]
    competitor_hits = sum(
        1 for cd in competitor_domains
        if any(cd in sd for sd in serp_domains[:10])
    )

    difficulty_factor = 1.0 - (competition * 0.6)
    gap_bonus = 1.0 + (competitor_hits * 0.25)

    return volume * difficulty_factor * gap_bonus


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_dir(niche: str) -> Path:
    d = ROOT / 'research' / 'niches' / niche
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_cache(niche: str) -> tuple:
    """Returns (keywords, serp_dict) or (None, None) if missing/stale."""
    cache = _cache_dir(niche)
    meta_path = cache / 'meta.json'
    if not meta_path.exists():
        return None, None

    with open(meta_path) as f:
        meta = json.load(f)

    age = datetime.now() - datetime.fromisoformat(meta['last_updated'])
    if age > timedelta(days=CACHE_TTL_DAYS):
        print(f"→ Cache stale ({age.days} days old) — refreshing")
        return None, None

    remaining = CACHE_TTL_DAYS - age.days
    print(f"→ Using cached niche data ({age.days}d old, {remaining}d until refresh)")

    keywords = json.loads((cache / 'keywords.json').read_text()) if (cache / 'keywords.json').exists() else []
    serp = json.loads((cache / 'serp.json').read_text()) if (cache / 'serp.json').exists() else {}
    return keywords, serp


def save_cache(niche: str, keywords: list, serp: dict, seeds: list) -> None:
    cache = _cache_dir(niche)
    (cache / 'keywords.json').write_text(json.dumps(keywords, indent=2))
    (cache / 'serp.json').write_text(json.dumps(serp, indent=2))
    (cache / 'meta.json').write_text(json.dumps({
        'last_updated': datetime.now().isoformat(),
        'niche': niche,
        'keywords_count': len(keywords),
        'seeds_used': seeds,
    }, indent=2))


# ---------------------------------------------------------------------------
# DataForSEO calls
# ---------------------------------------------------------------------------

def fetch_keywords(dfs: DataForSEO, seeds: list) -> list:
    """Expand seed keywords into related ideas."""
    seen = {}
    for i, seed in enumerate(seeds, 1):
        print(f"  [{i}/{len(seeds)}] Expanding: {seed}")
        try:
            ideas = dfs.get_keyword_ideas(seed, location_code=UK_LOCATION_CODE, limit=50)
            for kw in ideas:
                key = (kw.get('keyword') or '').lower()
                if key and key not in seen:
                    seen[key] = kw
        except Exception as e:
            print(f"    ⚠ {seed}: {e}")

    return list(seen.values())


def fetch_serp(dfs: DataForSEO, keywords: list) -> dict:
    """Fetch SERP top-10 for a list of keywords."""
    serp = {}
    for i, kw in enumerate(keywords, 1):
        print(f"  [{i}/{len(keywords)}] SERP: {kw}")
        try:
            serp[kw] = dfs.get_organic_serp(kw, location_code=UK_LOCATION_CODE, limit=10)
        except Exception as e:
            print(f"    ⚠ {e}")
            serp[kw] = []
    return serp


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def infer_content_type(keyword: str) -> str:
    kw = keyword.lower()
    if any(s in kw for s in ['what ', 'how ', 'why ', 'does ', 'is it', 'are ', 'should ']):
        return 'topical'
    return 'blog'


def write_report(abbr: str, topics: list, competitor_domains: list, niche: str) -> Path:
    out_dir = ROOT / 'research' / abbr.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime('%Y-%m-%d')
    out_path = out_dir / f'blog-topics-{date_str}.md'

    lines = [
        f"# Blog Topic Opportunities — {abbr.upper()} / {niche}",
        f"Generated: {datetime.now().strftime('%d %B %Y')}  |  Thresholds: vol ≥ {MIN_VOLUME}, competition ≤ {int(MAX_COMPETITION * 100)}%  |  Cache TTL: {CACHE_TTL_DAYS} days",
        "",
        f"**Competitor domains:** {', '.join(competitor_domains[:10]) or 'none found'}",
        "",
        "---",
        "",
        "## Prioritised Topics",
        "",
        "| # | Keyword | Vol | Competition | Competitors in SERP | Type |",
        "|---|---------|-----|-------------|---------------------|------|",
    ]

    for i, t in enumerate(topics, 1):
        vol = t.get('search_volume') or 0
        comp = int((t.get('competition') or 0) * 100)
        cc = t.get('competitor_count', 0)
        ctype = infer_content_type(t['keyword'])
        lines.append(f"| {i} | {t['keyword']} | {vol:,} | {comp}% | {cc} | {ctype} |")

    lines += ["", "---", "", "## Detail — Top 15", ""]

    for i, t in enumerate(topics[:15], 1):
        vol = t.get('search_volume') or 0
        comp = int((t.get('competition') or 0) * 100)
        serp = t.get('serp', [])
        comp_in_serp = [r for r in serp if any(cd in r.get('domain', '').lower() for cd in competitor_domains)]

        lines += [
            f"### {i}. {t['keyword']}",
            f"- **Volume:** {vol:,}  |  **Competition:** {comp}%  |  **Score:** {t['score']:.0f}",
        ]
        if comp_in_serp:
            names = ', '.join(r['domain'] for r in comp_in_serp[:3])
            lines.append(f"- **Competitors ranking:** {len(comp_in_serp)} ({names})")
        else:
            lines.append("- **Competitors ranking:** none detected")

        if serp:
            lines.append("- **Current top 5:**")
            for r in serp[:5]:
                title = (r.get('title') or '')[:65]
                lines.append(f"  - {r.get('position')}. [{r.get('domain')}] {title}")

        lines.append("")

    out_path.write_text('\n'.join(lines))
    return out_path


def write_queue(topics: list, abbr: str, cadence_days: int) -> Path:
    """Write a topic-queue.json for use with publish_scheduled.py."""
    out_dir = ROOT / 'research' / abbr.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'topic-queue.json'

    queue_topics = []
    for t in topics:
        ctype = infer_content_type(t['keyword'])
        queue_topics.append({
            'topic': t['keyword'],
            'content_type': ctype,
            'status': 'pending',
            'created_at': datetime.now().strftime('%Y-%m-%d'),
            'published_at': None,
            'post_id': None,
            'cost': None,
            'error': None,
        })

    queue = {
        'abbr': abbr.upper(),
        'cadence_days': cadence_days,
        'created_at': datetime.now().strftime('%Y-%m-%d'),
        'topics': queue_topics,
    }
    out_path.write_text(json.dumps(queue, indent=2))
    return out_path


def push_to_sheet(topics: list, abbr: str, niche: str) -> None:
    """Push topics to Google Sheet with status 'pause' for review."""
    try:
        import google_sheets as gs
        service = gs.get_service()
        sheet_id = gs.get_sheet_id()

        # Find next empty row in column A
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range='A:A'
        ).execute()
        next_row = len(result.get('values', [])) + 1

        rows = []
        for t in topics:
            ctype = infer_content_type(t['keyword'])
            # Columns: A=topic, B=status, C=cost, D=abbr, E=type, F=file, G=notes, H=review#, I=niche
            rows.append([t['keyword'], 'pause', '', abbr.upper(), ctype, '', '', '', niche])

        if rows:
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f'A{next_row}',
                valueInputOption='RAW',
                body={'values': rows},
            ).execute()
            print(f"→ Pushed {len(rows)} topics to Sheet (rows {next_row}–{next_row + len(rows) - 1}), status: pause")

    except Exception as e:
        print(f"⚠ Sheet push failed: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Research blog topics for a client niche')
    parser.add_argument('--abbr', required=True, help='Client abbreviation e.g. gtb')
    parser.add_argument('--limit', type=int, default=25, help='Topics to output (default 25)')
    parser.add_argument('--sheet', action='store_true', help='Push topics to Google Sheet (status: pause)')
    parser.add_argument('--refresh', action='store_true', help='Force cache refresh even if < 30 days old')
    parser.add_argument('--queue', action='store_true', help='Write topic-queue.json for scheduled publishing')
    parser.add_argument('--cadence', type=int, default=7, help='Publishing cadence in days for --queue (default 7)')
    args = parser.parse_args()

    abbr = args.abbr.lower()
    config = load_config(abbr)
    niche = config.get('niche')
    if not niche:
        print(f"✗ No 'niche' field in clients/{abbr}/config.json")
        sys.exit(1)

    print(f"\n→ Client: {abbr.upper()}  |  Niche: {niche}")

    competitor_domains = load_competitor_domains(abbr)
    print(f"→ {len(competitor_domains)} competitor domains from competitor-analysis.md")

    dfs = DataForSEO()

    # --- Cache check ---
    keywords, serp_cache = (None, None) if args.refresh else load_cache(niche)

    if keywords is None:
        seeds = build_seeds(config)
        print(f"\n→ Fetching keyword ideas for {len(seeds)} seeds...")
        all_keywords = fetch_keywords(dfs, seeds)
        print(f"→ {len(all_keywords)} raw keywords collected")

        # Filter
        filtered = [
            kw for kw in all_keywords
            if is_informational(kw.get('keyword', ''))
            and not has_location_intent(kw.get('keyword', ''))
            and passes_thresholds(kw)
        ]
        filtered.sort(key=lambda x: x.get('search_volume') or 0, reverse=True)
        keywords = filtered[:100]
        print(f"→ {len(keywords)} after filtering (informational, non-local, vol ≥ {MIN_VOLUME}, comp ≤ {int(MAX_COMPETITION*100)}%)")

        # SERP check top 25 candidates
        serp_candidates = [k['keyword'] for k in keywords[:25]]
        print(f"\n→ Fetching SERP data for top {len(serp_candidates)} candidates...")
        serp_cache = fetch_serp(dfs, serp_candidates)

        save_cache(niche, keywords, serp_cache, seeds)
        print(f"→ Cached to research/niches/{niche}/")

    # --- Score ---
    scored = []
    for kw in keywords:
        keyword = kw.get('keyword', '')
        serp_results = (serp_cache or {}).get(keyword, [])
        comp_count = sum(
            1 for r in serp_results
            if any(cd in r.get('domain', '').lower() for cd in competitor_domains)
        )
        score = score_topic(kw, competitor_domains, serp_results)
        scored.append({**kw, 'score': score, 'serp': serp_results, 'competitor_count': comp_count})

    scored.sort(key=lambda x: x['score'], reverse=True)
    top_topics = scored[:args.limit]

    # --- Report ---
    out_path = write_report(abbr, top_topics, competitor_domains, niche)
    print(f"\n✓ Report: {out_path.relative_to(ROOT)}")

    # --- Sheet push ---
    if args.sheet:
        push_to_sheet(top_topics, abbr, niche)

    # --- Queue file ---
    if args.queue:
        q_path = write_queue(top_topics, abbr, args.cadence)
        print(f"\n✓ Queue: {q_path.relative_to(ROOT)}  ({len(top_topics)} topics, every {args.cadence}d)")
        print(f"  Run: python3 src/content/publish_scheduled.py --abbr {abbr}")

    # --- Console summary ---
    print(f"\nTop 10 topics for {abbr.upper()}:")
    for i, t in enumerate(top_topics[:10], 1):
        vol = t.get('search_volume') or 0
        print(f"  {i:2}. {t['keyword']:<45} vol:{vol:>6,}  competitors:{t['competitor_count']}")


if __name__ == '__main__':
    main()
