#!/usr/bin/env python3
"""
Competitor Research Script
==========================
Pulls top 10 organic + top 10 local map pack results for a client's primary
keyword, scrapes each competitor website, and writes a structured
competitor-analysis.md to clients/[abbr]/.

Usage:
    python3 src/research_competitors.py --abbr gtm
    python3 src/research_competitors.py --abbr gtm --keyword "thai massage glasgow"
    python3 src/research_competitors.py --abbr gtm --maps-only   # re-run maps only

Requirements:
    pip install requests beautifulsoup4 anthropic python-dotenv
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent.resolve()
load_dotenv(ROOT / '.env')

sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))
from dataforseo import DataForSEO

import anthropic

# ── Constants ────────────────────────────────────────────────────────────────

DIRECTORY_DOMAINS = {
    'treatwell.co.uk', 'yell.com', 'yelp.co.uk', 'tripadvisor.co.uk',
    'tripadvisor.com', 'bark.com', 'checkatrade.com', 'google.com',
    'google.co.uk', 'facebook.com', 'instagram.com', 'gumtree.com',
    'freeindex.co.uk', 'thomson.co.uk', 'hotfrog.co.uk', 'cylex.co.uk',
    'scoot.co.uk', '192.com', 'foursquare.com',
}

SCRAPE_TIMEOUT = 10
MAX_SCRAPE_CHARS = 8000

# ── Geocoding (Nominatim / OpenStreetMap) ────────────────────────────────────

def geocode_address(address: str) -> tuple | None:
    """Convert a human-readable address to (lat, lng) using Nominatim.
    Tries progressively simpler queries until one resolves.
    """
    url = 'https://nominatim.openstreetmap.org/search'
    headers = {
        'User-Agent': 'SEOMachine/1.0 +https://github.com/seomachine',
        'Accept-Language': 'en',
    }
    # Build candidates from most specific to least
    candidates = [address]
    parts = [p.strip() for p in address.split(',')]
    if len(parts) > 2:
        candidates.append(', '.join(parts[-2:]))  # e.g. "Glasgow G1 2RQ"
    if len(parts) > 1:
        candidates.append(parts[-1].strip())       # e.g. "Glasgow G1 2RQ"
    # For space-separated areas like "Glasgow City Centre", also try first word only
    words = address.split()
    if len(words) > 1:
        candidates.append(words[0])                # e.g. "Glasgow"
    candidates.append('Glasgow, Scotland')         # absolute fallback

    for query in candidates:
        try:
            time.sleep(1)  # Nominatim rate limit: 1 req/s
            params = {'q': query, 'format': 'json', 'limit': 1, 'countrycodes': 'gb'}
            r = requests.get(url, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            if data:
                lat, lon = float(data[0]['lat']), float(data[0]['lon'])
                print(f"   ✓ Geocoded '{query}' → {lat:.4f}, {lon:.4f}")
                return lat, lon
        except Exception as e:
            print(f"   ✗ '{query}': {e}")

    return None


# ── Website scraping ─────────────────────────────────────────────────────────

def scrape_site(url: str) -> str:
    if not url:
        return ''
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
        }
        r = requests.get(url, headers=headers, timeout=SCRAPE_TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript']):
            tag.decompose()
        chunks = []
        title = soup.find('title')
        if title:
            chunks.append(f"[Page title] {title.get_text(strip=True)}")
        for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
            text = tag.get_text(separator=' ', strip=True)
            if len(text) > 20:
                chunks.append(text)
        return '\n'.join(chunks)[:MAX_SCRAPE_CHARS]
    except Exception as e:
        return f'[scrape failed: {e}]'


def scrape_competitor(base_url: str) -> str:
    if not base_url:
        return ''
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    content_parts = [f"=== {base} ===\n", scrape_site(base_url)]
    for path in ['/services/', '/treatments/', '/prices/', '/pricing/', '/massage/']:
        time.sleep(0.5)
        sub = scrape_site(base + path)
        if sub and '[scrape failed' not in sub and len(sub) > 100:
            content_parts.append(f"\n--- {path} ---\n{sub}")
        if sum(len(p) for p in content_parts) > MAX_SCRAPE_CHARS:
            break
    return '\n'.join(content_parts)[:MAX_SCRAPE_CHARS]


# ── Claude profile extraction ─────────────────────────────────────────────────

def extract_profile(client: anthropic.Anthropic, business_name: str,
                    website_content: str, map_data: dict | None) -> dict:
    map_context = ''
    if map_data:
        map_context = (
            f"Google Maps data: rating {map_data.get('rating', 'n/a')} "
            f"({map_data.get('rating_count', 0)} reviews), "
            f"address: {map_data.get('address', 'n/a')}, "
            f"phone: {map_data.get('phone', 'n/a')}"
        )

    prompt = f"""You are analysing a competitor business for a Thai massage company in Glasgow.

Business: {business_name}
{map_context}

Website content:
{website_content}

Extract the following as JSON (use null if not found):
{{
  "services": ["list of services offered"],
  "pricing": "pricing info if visible, e.g. '60 min £55'",
  "usp": "their main differentiator or selling point in one sentence",
  "content_quality": "poor/basic/good/strong",
  "has_blog": true/false,
  "has_location_pages": true/false,
  "review_count": number or null,
  "rating": number or null,
  "strengths": ["2-3 things they do well"],
  "gaps": ["2-3 things missing or weak"],
  "notes": "anything else worth noting"
}}

Return only valid JSON, no explanation."""

    try:
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=600,
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw = msg.content[0].text.strip()
        raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.MULTILINE)
        return json.loads(raw)
    except Exception as e:
        return {'error': str(e), 'services': [], 'gaps': [], 'strengths': []}


# ── Markdown output ───────────────────────────────────────────────────────────

def build_markdown(keyword: str, client_name: str, client_domain: str,
                   map_results: list, organic_results: list,
                   profiles: dict) -> str:
    from datetime import date
    today = date.today().isoformat()

    lines = [
        f"# Competitor Analysis — {client_name}",
        f"",
        f"Generated: {today}  ",
        f"Keyword: `{keyword}`",
        f"",
        "---",
        "",
        "## Map Pack — Top 10 Local Results",
        "",
        "| Rank | Business | Rating | Reviews | Website |",
        "|------|----------|--------|---------|---------|",
    ]

    if map_results:
        for r in map_results:
            name = r.get('name', 'Unknown')
            rating = r.get('rating') or '—'
            reviews = r.get('rating_count') or '—'
            url = r.get('url') or '—'
            domain = urlparse(url).netloc if url != '—' else '—'
            own = ' ⭐ (us)' if client_domain in domain else ''
            lines.append(f"| {r.get('position', '?')} | {name}{own} | {rating} | {reviews} | {domain} |")
    else:
        lines.append("| — | _(geocoding unavailable — run script again to populate)_ | — | — | — |")

    lines += [
        "",
        "---",
        "",
        "## Organic — Top 10 Results",
        "",
        "| Rank | Domain | Title |",
        "|------|--------|-------|",
    ]

    for r in organic_results:
        domain = r.get('domain', '—')
        title = (r.get('title') or '—')[:60]
        own = ' ⭐ (us)' if client_domain in domain else ''
        lines.append(f"| {r.get('position', '?')} | {domain}{own} | {title} |")

    lines += ["", "---", "", "## Competitor Profiles", ""]

    seen_domains = set()
    all_competitors = []
    for r in map_results:
        url = r.get('url', '')
        domain = urlparse(url).netloc if url else ''
        if domain and domain not in seen_domains and client_domain not in domain:
            seen_domains.add(domain)
            all_competitors.append(('map', r.get('position'), r.get('name'), url, r))

    for r in organic_results:
        domain = r.get('domain', '')
        if domain and domain not in seen_domains and client_domain not in domain:
            seen_domains.add(domain)
            all_competitors.append(('organic', r.get('position'), r.get('title', domain), r.get('url', ''), None))

    for source, pos, name, url, map_data in all_competitors:
        domain = urlparse(url).netloc if url else url
        profile = profiles.get(domain, {})
        source_label = f"Map #{pos}" if source == 'map' else f"Organic #{pos}"

        lines.append(f"### {name}")
        lines.append(f"**Source**: {source_label}  ")
        lines.append(f"**Website**: {url}  ")

        if map_data:
            rating = map_data.get('rating', '—')
            reviews = map_data.get('rating_count', '—')
            address = map_data.get('address', '—')
            lines.append(f"**Rating**: {rating} ({reviews} reviews)  ")
            lines.append(f"**Address**: {address}  ")

        if profile and 'error' not in profile:
            if profile.get('pricing'):
                lines.append(f"**Pricing**: {profile['pricing']}  ")
            if profile.get('usp'):
                lines.append(f"**USP**: {profile['usp']}  ")
            lines.append(f"**Content quality**: {profile.get('content_quality', '—')}  ")
            lines.append(f"**Has blog**: {'Yes' if profile.get('has_blog') else 'No'}  ")
            lines.append(f"**Has location pages**: {'Yes' if profile.get('has_location_pages') else 'No'}  ")
            services = profile.get('services', [])
            if services:
                lines.append(f"**Services**: {', '.join(services[:8])}")
            strengths = profile.get('strengths', [])
            if strengths:
                lines.append("\n**Strengths**:")
                for s in strengths:
                    lines.append(f"- {s}")
            gaps = profile.get('gaps', [])
            if gaps:
                lines.append("\n**Gaps / weaknesses**:")
                for g in gaps:
                    lines.append(f"- {g}")
            if profile.get('notes'):
                lines.append(f"\n**Notes**: {profile['notes']}")
        else:
            lines.append("_(website could not be scraped)_")

        lines.append("")

    all_gaps = []
    for profile in profiles.values():
        all_gaps.extend(profile.get('gaps', []))

    lines += [
        "---",
        "",
        "## Content Gap Summary",
        "",
        "Topics and pages competitors are missing — opportunities for this client:",
        "",
    ]
    if all_gaps:
        seen = set()
        for gap in all_gaps:
            clean = gap.strip()
            if clean.lower() not in seen:
                seen.add(clean.lower())
                lines.append(f"- {clean}")
    else:
        lines.append("_(run profiles to populate this section)_")

    lines += ["", "---", "", "*Auto-generated by research_competitors.py — refresh quarterly.*", ""]
    return '\n'.join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Research competitors for a client')
    parser.add_argument('--abbr', required=True, help='Client abbreviation (e.g. gtm)')
    parser.add_argument('--keyword', help='Override primary keyword')
    args = parser.parse_args()

    abbr = args.abbr.lower()
    client_dir = ROOT / 'clients' / abbr

    config_path = client_dir / 'config.json'
    if not config_path.exists():
        print(f"ERROR: No config found at {config_path}")
        sys.exit(1)

    config = json.loads(config_path.read_text())
    client_name = config.get('name', abbr.upper())
    client_domain = urlparse(config.get('website', '')).netloc
    # Use area for geocoding (shorter/cleaner than full address)
    area = config.get('area', '')
    address = config.get('address', area)
    # Strip urban qualifiers that confuse Nominatim (e.g. "Glasgow City Centre" → "Glasgow")
    _area_clean = re.sub(r'\b(city\s+cent(?:re|er)|town\s+cent(?:re|er)|district|quarter)\b',
                         '', area, flags=re.IGNORECASE).strip().strip(',').strip()
    geocode_query = _area_clean if _area_clean else (area if area else address)

    keyword = args.keyword
    if not keyword:
        kw_file = client_dir / 'target-keywords.md'
        if kw_file.exists():
            text = kw_file.read_text()
            match = re.search(r'### Category 1.*?\n.*?\|\s*Primary\s*\|([^|]+)\|', text, re.DOTALL)
            if match:
                keyword = match.group(1).strip()
        if not keyword:
            keyword = f"{config.get('keyword_prefix', 'massage')} {area}"

    print(f"\n{'='*60}")
    print(f"Competitor Research: {client_name}")
    print(f"Keyword: {keyword}")
    print(f"Geocoding: {geocode_query}")
    print(f"{'='*60}\n")

    # 1. Geocode
    # Geocode for reference (coords displayed but maps uses location_name which is more reliable)
    print("1. Geocoding location...")
    coords = geocode_address(geocode_query)
    if coords:
        lat, lng = coords
        print(f"   ✓ {lat:.4f}, {lng:.4f}")
    else:
        print("   ✗ Geocoding failed (non-critical — maps uses location_name)")

    # DataForSEO maps uses location_name — more reliable than coordinates for local pack
    area = config.get("area", address)
    # DataForSEO needs "Glasgow" not "Glasgow City Centre" — use city from postcode or first word of area
    city = config.get("city", area.split(",")[0].strip())
    location_name_dfs = f"{city},Scotland,United Kingdom"
    map_keyword = config.get("keyword_prefix", keyword.split()[0])

    # 2. DataForSEO queries
    print("\n2. Fetching SERP data...")
    dfs = DataForSEO()

    print(f"   Querying map pack ('{map_keyword}' @ {location_name_dfs})...")
    map_results = dfs.get_maps_pack(map_keyword, limit=10, location_name=location_name_dfs)
    print(f"   ✓ {len(map_results)} map results")
    time.sleep(1)

    print("   Querying organic SERP (UK)...")
    organic_results = dfs.get_organic_serp(keyword, location_code=2826, limit=10)
    print(f"   ✓ {len(organic_results)} organic results")

    organic_filtered = [
        r for r in organic_results
        if not any(d in (r.get('domain') or '') for d in DIRECTORY_DOMAINS)
    ]
    print(f"   ✓ {len(organic_filtered)} organic after filtering directories")

    # 3. Build competitor list
    competitors_to_scrape = {}

    for r in map_results:
        url = r.get('url', '')
        domain = urlparse(url).netloc
        if domain and client_domain not in domain:
            competitors_to_scrape[domain] = {
                'name': r.get('name', domain),
                'url': url,
                'map_data': r,
            }

    for r in organic_filtered:
        domain = r.get('domain', '')
        if domain and domain not in competitors_to_scrape and client_domain not in domain:
            competitors_to_scrape[domain] = {
                'name': r.get('title', domain),
                'url': r.get('url', ''),
                'map_data': None,
            }

    print(f"\n3. Scraping {len(competitors_to_scrape)} competitor websites...")
    scraped = {}
    for domain, info in competitors_to_scrape.items():
        print(f"   Scraping {domain}...")
        scraped[domain] = scrape_competitor(info['url'])
        time.sleep(1)

    print(f"\n4. Extracting profiles with Claude Haiku...")
    claude_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    profiles = {}
    for domain, info in competitors_to_scrape.items():
        content = scraped.get(domain, '')
        if content and '[scrape failed' not in content:
            print(f"   Profiling {info['name']}...")
            profiles[domain] = extract_profile(
                claude_client, info['name'], content, info['map_data']
            )
            time.sleep(0.5)
        else:
            print(f"   Skipping {domain} (no content)")

    print("\n5. Writing competitor-analysis.md...")
    md = build_markdown(
        keyword=keyword,
        client_name=client_name,
        client_domain=client_domain,
        map_results=map_results,
        organic_results=organic_filtered,
        profiles=profiles,
    )

    output_path = client_dir / 'competitor-analysis.md'
    output_path.write_text(md, encoding='utf-8')
    print(f"   ✓ Written to {output_path.relative_to(ROOT)}")

    print(f"\n{'='*60}")
    print(f"Done.")
    print(f"  Map pack results:  {len(map_results)}")
    print(f"  Organic results:   {len(organic_filtered)}")
    print(f"  Sites profiled:    {len(profiles)}")
    print(f"  Output:            clients/{abbr}/competitor-analysis.md")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
