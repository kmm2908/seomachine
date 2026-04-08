"""
Audit Data Collectors

Six collectors, each returning a typed result dataclass.
All collectors fail gracefully — a collection error never aborts the audit.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import urllib3
import requests
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))

from scoring import (
    SchemaResult, ContentResult, GBPResult,
    ReviewResult, NAPResult, TechnicalResult, CompetitorResult,
)

logger = logging.getLogger(__name__)

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.9',
}
_TIMEOUT = 15


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_captcha(r: requests.Response) -> bool:
    """Detect SiteGround or Cloudflare bot-challenge responses."""
    if r.status_code in (202, 503) and 'sgcaptcha' in r.text:
        return True
    if r.status_code == 403 and 'Cloudflare' in r.text:
        return True
    return False


def _get(url: str, wp_config: Optional[Dict] = None, **kwargs) -> Optional[requests.Response]:
    kwargs.setdefault('verify', False)
    headers = dict(_HEADERS)
    auth = None
    if wp_config:
        auth = (wp_config.get('username', ''), wp_config.get('app_password', ''))
    try:
        r = requests.get(url, headers=headers, timeout=_TIMEOUT, auth=auth, **kwargs)
        if _is_captcha(r):
            logger.debug(f'Bot-challenge response from {url} — treating as blocked')
            return None
        return r
    except Exception as e:
        logger.debug(f'GET {url} failed: {e}')
        return None


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, 'lxml')


def _extract_jsonld(soup: BeautifulSoup) -> List[Dict]:
    """Extract all JSON-LD blocks from a page."""
    blocks = []
    for tag in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(tag.string or '')
            # Unwrap @graph arrays
            if isinstance(data, dict) and '@graph' in data:
                blocks.extend(data['@graph'])
            elif isinstance(data, list):
                blocks.extend(data)
            else:
                blocks.append(data)
        except json.JSONDecodeError:
            pass
    return blocks


def _type_of(block: Dict) -> str:
    return block.get('@type', '')


def _normalise_phone(phone: str) -> str:
    """Strip non-digit characters for comparison."""
    return re.sub(r'\D', '', phone)


def _normalise_address(addr: str) -> str:
    """Lowercase + collapse whitespace for loose comparison."""
    return re.sub(r'\s+', ' ', addr.lower().strip())


# ── Schema Collector ──────────────────────────────────────────────────────────

def collect_schema(site_url: str, wp_config: Optional[Dict] = None) -> SchemaResult:
    result = SchemaResult()
    pages_to_check = [site_url]

    # Add one extra page from the nav if we can find it
    r = _get(site_url, wp_config=wp_config)
    if r is None or r.status_code >= 400:
        result.findings.append(
            'Could not reach site to check schema — '
            'site may have bot protection (SiteGround/Cloudflare). '
            'Schema data collected from WP API where available.'
        )
        return result

    soup = _soup(r.text)
    # Pick first internal link from nav as a sample page
    nav = soup.find('nav') or soup.find('header')
    if nav:
        for a in nav.find_all('a', href=True):
            href = a['href']
            if href.startswith('/') or site_url in href:
                full = urljoin(site_url, href)
                if full != site_url and full not in pages_to_check:
                    pages_to_check.append(full)
                    break

    all_blocks: List[Dict] = []
    for url in pages_to_check[:2]:
        pr = _get(url, wp_config=wp_config)
        if pr is not None and pr.status_code < 400:
            s = _soup(pr.text)
            all_blocks.extend(_extract_jsonld(s))
    result.pages_checked = len(pages_to_check[:2])

    # Check for schema types
    types = [_type_of(b) for b in all_blocks]
    result.has_local_business = any(
        t in ('LocalBusiness', 'MassageTherapist', 'HealthAndBeautyBusiness',
               'BeautySalon', 'SpaOrHealthClub')
        for t in types
    )
    result.has_faq = 'FAQPage' in types
    result.has_article = any(t in ('Article', 'BlogPosting', 'NewsArticle') for t in types)

    # Check required LocalBusiness fields
    lb = next(
        (b for b in all_blocks
         if _type_of(b) in ('LocalBusiness', 'MassageTherapist',
                             'HealthAndBeautyBusiness', 'BeautySalon', 'SpaOrHealthClub')),
        None
    )
    if lb:
        result.name_present = bool(lb.get('name'))
        result.phone_present = bool(lb.get('telephone'))
        result.url_present = bool(lb.get('url'))
        result.opening_hours_present = bool(
            lb.get('openingHours') or lb.get('openingHoursSpecification')
        )
        addr = lb.get('address', {})
        if isinstance(addr, dict):
            result.address_present = bool(
                addr.get('streetAddress') or addr.get('addressLocality')
            )
        elif isinstance(addr, str):
            result.address_present = bool(addr)

    # Build findings
    if not result.has_local_business:
        result.findings.append('No LocalBusiness schema found — Google cannot verify business details.')
    if result.has_local_business and not result.phone_present:
        result.findings.append('LocalBusiness schema is missing telephone number.')
    if result.has_local_business and not result.address_present:
        result.findings.append('LocalBusiness schema is missing address.')
    if result.has_local_business and not result.opening_hours_present:
        result.findings.append('Opening hours not in schema — missed rich result opportunity.')
    if not result.has_faq:
        result.findings.append('No FAQPage schema — missing FAQ rich results.')
    if not result.has_article:
        result.findings.append('No Article/BlogPosting schema on sampled pages.')

    return result


# ── Content Collector ─────────────────────────────────────────────────────────

def collect_content(site_url: str, wp_config: Optional[Dict] = None) -> ContentResult:
    result = ContentResult()

    # ── Try SEO Machine audit endpoint (single auth'd call, bypasses bot protection) ──
    audit_url = site_url.rstrip('/') + '/wp-json/seomachine/v1/audit'
    r = _get(audit_url, wp_config=wp_config)
    if r is not None and r.status_code == 200:
        try:
            counts = r.json().get('post_counts', {})
            result.blog_count     = counts.get('post', 0)
            result.page_count     = counts.get('page', 0)
            result.service_count  = counts.get('seo_service', 0)
            result.location_count = counts.get('seo_location', 0)
        except Exception:
            pass

    # ── Fallback: individual WP REST API calls ─────────────────────────────────
    if result.blog_count == 0 and result.service_count == 0:
        api_base = site_url.rstrip('/') + '/wp-json/wp/v2'

        def _api_total(endpoint: str) -> int:
            r2 = _get(f'{api_base}/{endpoint}', wp_config=wp_config)
            if r2 is not None and r2.status_code == 200:
                return int(r2.headers.get('X-WP-Total', 0))
            return 0

        result.blog_count     = _api_total('posts?per_page=1&status=publish')
        result.page_count     = _api_total('pages?per_page=1&status=publish')
        result.service_count  = _api_total('seo_service?per_page=1&status=publish')
        result.location_count = _api_total('seo_location?per_page=1&status=publish')

    # If still no service pages, try inferring from homepage navigation
    if result.service_count == 0:
        r = _get(site_url, wp_config=wp_config)
        if r is not None and r.status_code < 400:
            soup = _soup(r.text)
            service_keywords = ['massage', 'therapy', 'treatment', 'service',
                                 'facial', 'reflexology', 'sports']
            service_like = set()
            for a in soup.find_all('a', href=True):
                href = a['href'].lower()
                text = (a.get_text() or '').lower()
                if any(k in href or k in text for k in service_keywords):
                    full = urljoin(site_url, a['href'])
                    if urlparse(full).netloc == urlparse(site_url).netloc:
                        service_like.add(full)
            result.service_count = min(len(service_like), 20)

    # Sitemap check
    for sitemap_path in ['/sitemap.xml', '/sitemap_index.xml', '/wp-sitemap.xml']:
        r = _get(site_url.rstrip('/') + sitemap_path, wp_config=wp_config)
        if r is not None and r.status_code == 200 and '<' in r.text:
            result.has_sitemap = True
            result.sitemap_url_count = r.text.count('<loc>')
            break

    # Build findings
    if result.service_count < 2:
        result.findings.append(
            f'Only {result.service_count} service page(s) found — '
            'each service should have a dedicated page.'
        )
    if result.blog_count < 3:
        result.findings.append(
            f'Only {result.blog_count} blog post(s) found — '
            'regular content is essential for organic visibility.'
        )
    if result.location_count == 0:
        result.findings.append(
            'No location/area pages found — '
            'local SEO relies on geo-targeted landing pages.'
        )
    if not result.has_sitemap:
        result.findings.append('No XML sitemap found — search engines may miss content.')

    return result


# ── GBP Collector ─────────────────────────────────────────────────────────────

def collect_gbp(config: Dict) -> GBPResult:
    result = GBPResult()

    location_id = config.get('gbp_location_id')
    if not location_id:
        result.findings.append(
            'GBP location ID not configured — '
            'add `gbp_location_id` to config.json to enable this check.'
        )
        return result

    try:
        from google_business_profile import GoogleBusinessProfile
        gbp = GoogleBusinessProfile.from_client_config(config)
        result.available = True

        info = gbp.get_business_info(location_id)
        result.has_description = bool(info.get('description'))
        cats = info.get('categories', [])
        result.category_count = len(cats) if isinstance(cats, list) else (1 if cats else 0)

        hours = gbp.get_hours(location_id)
        result.has_hours = bool(hours)

        attrs = gbp.get_attributes(location_id)
        result.photo_count = attrs.get('photo_count', 0) if attrs else 0

    except Exception as e:
        result.available = False
        result.findings.append(f'GBP API error: {e}')
        return result

    # Build findings
    if not result.has_description:
        result.findings.append('GBP profile has no description — missed keyword opportunity.')
    if result.category_count < 2:
        result.findings.append('Only one GBP category — add relevant secondary categories.')
    if not result.has_hours:
        result.findings.append('Business hours not set on GBP profile.')
    if result.photo_count < 5:
        result.findings.append(
            f'Only {result.photo_count} photo(s) on GBP — '
            'profiles with 10+ photos get significantly more clicks.'
        )

    return result


# ── Review Collector ──────────────────────────────────────────────────────────

def collect_reviews(config: Dict) -> ReviewResult:
    result = ReviewResult()

    location_id = config.get('gbp_location_id')
    if not location_id:
        # Try to extract review data from schema on site
        site_url = config.get('website', '') or config.get('wordpress', {}).get('url', '')
        if site_url:
            r = _get(site_url)
            if r is not None and r.status_code < 400:
                blocks = _extract_jsonld(_soup(r.text))
                for block in blocks:
                    agg = block.get('aggregateRating', {})
                    if agg:
                        result.available = True
                        result.count = int(agg.get('reviewCount', agg.get('ratingCount', 0)))
                        result.average_rating = float(agg.get('ratingValue', 0))
                        break
        if not result.available:
            result.findings.append(
                'Review data not available — add `gbp_location_id` to config.json '
                'or add aggregateRating to site schema.'
            )
        return result

    try:
        from google_business_profile import GoogleBusinessProfile
        gbp = GoogleBusinessProfile.from_client_config(config)
        reviews = gbp.get_reviews(location_id, limit=50)
        result.available = True

        if reviews:
            result.count = len(reviews)
            ratings = [r_['rating'] for r_ in reviews if r_.get('rating')]
            result.average_rating = sum(ratings) / len(ratings) if ratings else 0.0
            responded = sum(1 for r_ in reviews if r_.get('owner_reply'))
            result.response_rate = responded / len(reviews) if reviews else 0.0

    except Exception as e:
        result.findings.append(f'Review API error: {e}')
        return result

    # Build findings
    if result.count < 10:
        result.findings.append(
            f'Only {result.count} reviews — businesses with 50+ reviews dominate local search.'
        )
    if result.average_rating < 4.5:
        result.findings.append(
            f'Average rating {result.average_rating:.1f} — '
            'aim for 4.8+ to compete in the local pack.'
        )
    if result.response_rate < 0.5:
        pct = int(result.response_rate * 100)
        result.findings.append(
            f'Only {pct}% of reviews have a response — '
            'Google rewards active engagement with review responses.'
        )

    return result


# ── NAP Collector ─────────────────────────────────────────────────────────────

def collect_nap(config: Dict, schema: SchemaResult, site_url: str,
                wp_config: Optional[Dict] = None) -> NAPResult:
    result = NAPResult()

    # Ground truth from config
    result.config_name = config.get('name', '')
    result.config_address = config.get('address', '')
    result.config_phone = config.get('phone', '')

    # Extract NAP from site schema
    r = _get(site_url, wp_config=wp_config)
    if r is not None and r.status_code < 400:
        blocks = _extract_jsonld(_soup(r.text))
        lb = next(
            (b for b in blocks
             if _type_of(b) in ('LocalBusiness', 'MassageTherapist',
                                 'HealthAndBeautyBusiness', 'BeautySalon', 'SpaOrHealthClub')),
            None
        )
        if lb:
            result.schema_name = lb.get('name', '')
            result.schema_phone = lb.get('telephone', '')
            addr = lb.get('address', {})
            if isinstance(addr, dict):
                parts = filter(None, [
                    addr.get('streetAddress'),
                    addr.get('addressLocality'),
                    addr.get('postalCode'),
                ])
                result.schema_address = ', '.join(parts)
            elif isinstance(addr, str):
                result.schema_address = addr

    # Compare (loose matching)
    def _name_match(a: str, b: str) -> bool:
        return a.lower().strip() == b.lower().strip()

    def _phone_match(a: str, b: str) -> bool:
        return bool(a and b and _normalise_phone(a) == _normalise_phone(b))

    def _addr_match(a: str, b: str) -> bool:
        na, nb = _normalise_address(a), _normalise_address(b)
        # Partial match OK — schema address may be abbreviated
        return bool(na and nb and (na in nb or nb in na or na == nb))

    if result.config_name and result.schema_name:
        result.name_match = 'match' if _name_match(result.config_name, result.schema_name) else 'mismatch'
    elif not result.schema_name:
        result.name_match = 'unknown'

    if result.config_phone and result.schema_phone:
        result.phone_match = 'match' if _phone_match(result.config_phone, result.schema_phone) else 'mismatch'
    elif not result.schema_phone:
        result.phone_match = 'unknown'

    if result.config_address and result.schema_address:
        result.address_match = 'match' if _addr_match(result.config_address, result.schema_address) else 'mismatch'
    elif not result.schema_address:
        result.address_match = 'unknown'

    # Build findings
    if result.name_match == 'mismatch':
        result.findings.append(
            f'Business name mismatch: config="{result.config_name}" '
            f'vs schema="{result.schema_name}".'
        )
    if result.phone_match == 'mismatch':
        result.findings.append(
            f'Phone number mismatch: config="{result.config_phone}" '
            f'vs schema="{result.schema_phone}".'
        )
    if result.address_match == 'mismatch':
        result.findings.append(
            f'Address mismatch: config="{result.config_address}" '
            f'vs schema="{result.schema_address}".'
        )
    if result.name_match == 'unknown' and not result.schema_name:
        result.findings.append('Business name not found in site schema — add to LocalBusiness.')
    if result.phone_match == 'unknown' and not result.schema_phone:
        result.findings.append('Phone number not in schema — critical for local search.')

    return result


# ── Technical Collector ───────────────────────────────────────────────────────

def collect_technical(site_url: str, wp_config: Optional[Dict] = None) -> TechnicalResult:
    result = TechnicalResult()

    # SSL
    result.has_ssl = site_url.startswith('https://')

    # Fetch homepage
    start = time.time()
    r = _get(site_url, wp_config=wp_config)
    if r is None or r.status_code >= 400:
        result.findings.append('Could not reach site.')
        return result
    result.response_time_ms = int((time.time() - start) * 1000)

    soup = _soup(r.text)

    # Meta title
    title_tag = soup.find('title')
    result.has_meta_title = bool(title_tag and title_tag.get_text(strip=True))

    # Meta description
    meta_desc = soup.find('meta', attrs={'name': re.compile(r'^description$', re.I)})
    result.has_meta_description = bool(meta_desc and meta_desc.get('content', '').strip())

    # H1
    result.has_h1 = bool(soup.find('h1'))

    # robots.txt
    robots_r = _get(site_url.rstrip('/') + '/robots.txt', wp_config=wp_config)
    result.has_robots = bool(
        robots_r is not None and robots_r.status_code == 200
        and 'user-agent' in robots_r.text.lower()
    )

    # sitemap
    for path in ['/sitemap.xml', '/sitemap_index.xml', '/wp-sitemap.xml']:
        sm_r = _get(site_url.rstrip('/') + path, wp_config=wp_config)
        if sm_r is not None and sm_r.status_code == 200 and '<' in sm_r.text:
            result.has_sitemap = True
            break

    # Build findings
    if not result.has_ssl:
        result.findings.append('Site is not HTTPS — major trust and ranking signal missing.')
    if not result.has_meta_title:
        result.findings.append('Homepage is missing a <title> tag.')
    if not result.has_meta_description:
        result.findings.append('Homepage has no meta description — affects click-through rate.')
    if not result.has_h1:
        result.findings.append('Homepage has no H1 tag — critical for keyword relevance.')
    if not result.has_robots:
        result.findings.append('No robots.txt found.')
    if not result.has_sitemap:
        result.findings.append('No XML sitemap — search engines may miss pages.')
    if result.response_time_ms > 3000:
        result.findings.append(
            f'Slow page load: {result.response_time_ms}ms — '
            'Google uses Core Web Vitals as a ranking factor.'
        )

    return result


# ── Competitor Collector ──────────────────────────────────────────────────────

def collect_competitor(abbr: str) -> CompetitorResult:
    result = CompetitorResult()

    analysis_path = ROOT / 'clients' / abbr / 'competitor-analysis.md'
    if not analysis_path.exists():
        result.notes.append(
            f'No competitor analysis found at {analysis_path}. '
            'Run `research_competitors.py --abbr {abbr}` to generate it.'
        )
        return result

    result.available = True
    text = analysis_path.read_text(encoding='utf-8')

    # Extract competitor names from ### headings
    names = re.findall(r'^###\s+(.+)$', text, re.MULTILINE)
    result.top_competitors = names[:5]

    # Look for map pack position mention
    map_match = re.search(r'position[:\s]+#?(\d+)', text, re.IGNORECASE)
    if map_match:
        result.client_map_position = f'#{map_match.group(1)}'

    if not result.top_competitors:
        result.notes.append('Competitor analysis exists but no competitor profiles found.')

    return result
