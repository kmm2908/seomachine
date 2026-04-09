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
    """Detect SiteGround or Cloudflare bot-challenge responses.
    SiteGround may return HTTP 200 with a JS challenge page (sgchallenge cookie),
    HTTP 202 with a meta-refresh to /.well-known/sgcaptcha/, or HTTP 503.
    """
    text_sample = r.text[:2000] if r.text else ''
    if 'sgchallenge' in text_sample or '/.well-known/captcha/' in text_sample:
        return True
    if r.status_code in (202, 503) and 'sgcaptcha' in text_sample:
        return True
    if r.status_code == 403 and 'Cloudflare' in text_sample:
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


def _make_playwright_context(playwright):
    """Create a browser context that looks like a real browser (anti-bot measures)."""
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
        ],
    )
    context = browser.new_context(
        user_agent=(
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        locale='en-GB',
        timezone_id='Europe/London',
    )
    # Hide webdriver flag — key for bypassing SiteGround bot detection
    context.add_init_script(
        'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    )
    return browser, context


def _playwright_fetch(
    site_url: str,
    target_url: str,
    wp_config: Optional[Dict] = None,
    *,
    is_api: bool = False,
) -> Optional[str]:
    """
    Fetch target_url via Playwright using a shared session.

    Strategy:
    1. Navigate to site homepage first (solves SiteGround JS challenge, sets cookies).
    2. Wait until the challenge redirect completes (title is no longer "Robot Challenge").
    3. For API targets: use page.evaluate(fetch(...)) so the call inherits solved cookies.
    4. For HTML targets: navigate directly after challenge is solved.

    This avoids the problem where each fresh Playwright browser has to solve the
    challenge independently — instead, one challenge solve covers all API calls.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    import base64
    auth_header = ''
    if wp_config:
        creds = f"{wp_config.get('username','')}:{wp_config.get('app_password','')}".encode()
        auth_header = 'Basic ' + base64.b64encode(creds).decode()

    try:
        with sync_playwright() as p:
            browser, context = _make_playwright_context(p)
            page = context.new_page()

            homepage = site_url.rstrip('/')
            logger.debug(f'Playwright: loading homepage {homepage} to solve challenge...')

            # Step 1: Navigate to homepage (may get bot challenge with 202 redirect)
            try:
                page.goto(homepage, wait_until='commit', timeout=60000)
            except Exception:
                pass  # Execution context destruction during challenge redirect is expected

            # Step 2: Wait for challenge to complete and redirect to real page
            try:
                page.wait_for_load_state('networkidle', timeout=40000)
            except Exception:
                pass

            # Check if we're stuck on a challenge/captcha page
            current_url = page.url
            if '/.well-known/' in current_url or 'captcha' in current_url.lower():
                logger.warning(
                    'SiteGround IP challenge active — Playwright cannot bypass CAPTCHA. '
                    'Wait ~30 minutes for IP block to expire, or run audit from a different network.'
                )
                browser.close()
                return None

            if 'sgchallenge' in (page.content()[:2000]):
                logger.debug('Playwright: challenge page still active after wait')
                browser.close()
                return None

            logger.debug(f'Playwright: challenge cleared, at {current_url!r}')

            # Step 3: Fetch the target
            if target_url.rstrip('/') == homepage or target_url == homepage + '/':
                result = page.content()
            elif is_api:
                # Use fetch() from within the browser context (inherits solved cookies)
                headers_json = json.dumps({'Authorization': auth_header} if auth_header else {})
                js_fetch = f'''async () => {{
                    try {{
                        const r = await fetch({json.dumps(target_url)}, {{
                            headers: {headers_json}
                        }});
                        return await r.text();
                    }} catch(e) {{
                        return null;
                    }}
                }}'''
                try:
                    result = page.evaluate(js_fetch)
                except Exception as e:
                    logger.debug(f'Playwright fetch() eval failed: {e}')
                    result = None
            else:
                try:
                    resp = page.goto(target_url, wait_until='networkidle', timeout=30000)
                    result = page.content() if (resp and resp.ok) else None
                except Exception:
                    result = page.content() if page.url else None

            browser.close()
            return result if result else None

    except Exception as e:
        logger.debug(f'Playwright error for {target_url}: {e}')
        return None


# Module-level caches
_SITE_URL_CACHE: Optional[str] = None
_SSH_CONFIG_CACHE: Optional[Dict] = None


def _get_via_ssh(url: str, wp_config: Optional[Dict] = None) -> Optional[str]:
    """
    Fetch a URL by SSHing into the SiteGround server and running curl on localhost.

    This bypasses SiteGround's CDN/WAF entirely — the request goes server-to-server
    on 127.0.0.1, so no IP challenge, no bot detection, ever.

    Requires: `_SSH_CONFIG_CACHE` set by the caller (via `_get_with_fallback(ssh_config=...)`).
    SSH key: ~/.ssh/seomachine_deploy (same key used by GitHub Actions deploy pipeline).
    """
    import subprocess, base64, shlex
    from urllib.parse import urlparse

    ssh_cfg = _SSH_CONFIG_CACHE
    if not ssh_cfg:
        return None

    parsed = urlparse(url)
    domain = parsed.netloc
    path = parsed.path or '/'
    if parsed.query:
        path += '?' + parsed.query

    # Build auth header
    auth_header = ''
    if wp_config:
        creds = f"{wp_config.get('username','')}:{wp_config.get('app_password','')}".encode()
        auth_header = 'Basic ' + base64.b64encode(creds).decode()

    # curl on localhost with Host header — bypasses CDN completely
    # Use HTTPS with -k (skip cert verify) since localhost uses the site's cert
    curl_parts = [
        'curl', '-sk', '--max-time', '20',
        '-H', f'Host: {domain}',
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/124.0.0.0',
        '-H', 'Accept: */*',
    ]
    if auth_header:
        curl_parts += ['-H', f'Authorization: {auth_header}']
    curl_parts.append(f'https://127.0.0.1{path}')

    # Wrap in SSH command
    key_path = str(Path(ssh_cfg['key'].replace('~', str(Path.home()))).expanduser())
    ssh_cmd = [
        'ssh',
        '-i', key_path,
        '-p', str(ssh_cfg.get('port', 18765)),
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'BatchMode=yes',
        '-o', 'ConnectTimeout=15',
        f"{ssh_cfg['user']}@{ssh_cfg['host']}",
        ' '.join(shlex.quote(p) for p in curl_parts),
    ]

    try:
        result = subprocess.run(
            ssh_cmd, capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout:
            logger.debug(f'SSH fetch succeeded for {url} ({len(result.stdout)} bytes)')
            return result.stdout
        if result.returncode != 0:
            logger.debug(f'SSH fetch failed (exit {result.returncode}): {result.stderr[:200]}')
        return None
    except subprocess.TimeoutExpired:
        logger.debug(f'SSH fetch timed out for {url}')
        return None
    except Exception as e:
        logger.debug(f'SSH fetch error for {url}: {e}')
        return None


def _get_with_fallback(
    url: str,
    wp_config: Optional[Dict] = None,
    site_url: Optional[str] = None,
    ssh_config: Optional[Dict] = None,
) -> Optional[str]:
    """
    Fetch a URL with three-tier fallback:
      1. requests (fast, no overhead)
      2. SSH localhost curl (bypasses SiteGround CDN/WAF entirely — permanent fix)
      3. Playwright headless (JS challenge bypass, but blocked by IPC rate-limit)
    """
    global _SITE_URL_CACHE, _SSH_CONFIG_CACHE

    if site_url:
        _SITE_URL_CACHE = site_url
    if ssh_config:
        _SSH_CONFIG_CACHE = ssh_config

    # Tier 1: plain requests
    r = _get(url, wp_config=wp_config)
    if r is not None and r.status_code < 400:
        return r.text

    # Tier 2: SSH localhost curl (preferred — no IP block risk)
    if _SSH_CONFIG_CACHE:
        result = _get_via_ssh(url, wp_config=wp_config)
        if result:
            return result

    # Tier 3: Playwright (handles JS challenges, but blocked by hard IPC rate-limit)
    effective_site = _SITE_URL_CACHE or url
    is_api = '/wp-json/' in url
    return _playwright_fetch(effective_site, url, wp_config=wp_config, is_api=is_api)


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

    # Fetch homepage — fall back to Playwright if requests is blocked by bot protection
    html = _get_with_fallback(site_url, wp_config=wp_config, site_url=site_url)
    if not html:
        result.findings.append(
            'Could not reach site to check schema — '
            'site may have persistent bot protection. '
            'Try running the audit from a different network.'
        )
        return result

    soup = _soup(html)
    # Try to find a published service/location post URL via WP REST API
    # (GTM-style sites embed LocalBusiness schema on content pages, not the homepage)
    content_url = None
    for cpt in ['seo_service', 'seo_location', 'posts']:
        api_url = site_url.rstrip('/') + f'/wp-json/wp/v2/{cpt}?per_page=1&status=publish&_fields=link'
        raw = _get_with_fallback(api_url, wp_config=wp_config)
        if raw:
            try:
                # Strip HTML wrapper if present (Playwright/SSH may return raw JSON or HTML-wrapped)
                text = raw
                if raw.lstrip().startswith('<'):
                    pre = _soup(raw).find('pre')
                    text = pre.get_text() if pre else raw
                items = json.loads(text)
                if items and isinstance(items, list):
                    content_url = items[0].get('link')
                    break
            except Exception:
                pass
    if content_url and content_url not in pages_to_check:
        pages_to_check.append(content_url)
    elif not content_url:
        # Fall back to first internal nav link
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
        page_html = _get_with_fallback(url, wp_config=wp_config)
        if page_html:
            all_blocks.extend(_extract_jsonld(_soup(page_html)))
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

    # ── Try SEO Machine audit endpoint (single auth'd call) ──────────────────────
    # Falls back to Playwright if plain requests are blocked by bot protection.
    audit_url = site_url.rstrip('/') + '/wp-json/seomachine/v1/audit'
    audit_html = _get_with_fallback(audit_url, wp_config=wp_config, site_url=site_url)
    if audit_html:
        try:
            # Playwright wraps JSON in an HTML <pre> tag (Chromium JSON viewer)
            # Try <pre> extraction first; fall back to regex
            soup_json = _soup(audit_html)
            pre = soup_json.find('pre')
            raw_json = pre.get_text() if pre else audit_html
            # Strip any leading/trailing HTML if <pre> wasn't found
            if not pre:
                json_match = re.search(r'\{.*\}', raw_json, re.DOTALL)
                raw_json = json_match.group(0) if json_match else raw_json
            counts = json.loads(raw_json).get('post_counts', {})
            result.blog_count     = counts.get('post', 0)
            result.page_count     = counts.get('page', 0)
            result.service_count  = counts.get('seo_service', 0)
            result.location_count = counts.get('seo_location', 0)
        except Exception as _e:
            logger.debug(f'Audit endpoint parse failed: {_e}')

    # ── Fallback: individual WP REST API calls ─────────────────────────────────
    # Only run for counts that are still 0 (audit endpoint may have populated some already)
    _need_fallback = (
        result.blog_count == 0 or result.service_count == 0
        or result.location_count == 0 or result.page_count == 0
    )
    if _need_fallback:
        api_base = site_url.rstrip('/') + '/wp-json/wp/v2'

        def _api_total(endpoint: str) -> int:
            r2 = _get(f'{api_base}/{endpoint}', wp_config=wp_config)
            if r2 is not None and r2.status_code == 200:
                return int(r2.headers.get('X-WP-Total', 0))
            return 0

        if result.blog_count == 0:
            result.blog_count = _api_total('posts?per_page=1&status=publish')
        if result.page_count == 0:
            result.page_count = _api_total('pages?per_page=1&status=publish')
        if result.service_count == 0:
            result.service_count = _api_total('seo_service?per_page=1&status=publish')
        if result.location_count == 0:
            result.location_count = _api_total('seo_location?per_page=1&status=publish')

    # If still no service pages, try inferring from homepage navigation
    if result.service_count == 0:
        home_html = _get_with_fallback(site_url, wp_config=wp_config)
        if home_html:
            soup = _soup(home_html)
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
        sm_html = _get_with_fallback(site_url.rstrip('/') + sitemap_path, wp_config=wp_config)
        if sm_html and '<' in sm_html:
            result.has_sitemap = True
            result.sitemap_url_count = sm_html.count('<loc>')
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
        from google_business_profile import GoogleBusinessProfile, from_client_config as _gbp_from_config
        gbp = _gbp_from_config(config)
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
        from google_business_profile import GoogleBusinessProfile, from_client_config as _gbp_from_config
        gbp = _gbp_from_config(config)
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
    site_html = _get_with_fallback(site_url, wp_config=wp_config)
    if site_html:
        blocks = _extract_jsonld(_soup(site_html))
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

    # Fetch homepage (Playwright fallback handles bot protection)
    start = time.time()
    home_html = _get_with_fallback(site_url, wp_config=wp_config)
    if not home_html:
        result.findings.append('Could not reach site.')
        return result
    result.response_time_ms = int((time.time() - start) * 1000)

    soup = _soup(home_html)

    # Meta title
    title_tag = soup.find('title')
    result.has_meta_title = bool(title_tag and title_tag.get_text(strip=True))

    # Meta description
    meta_desc = soup.find('meta', attrs={'name': re.compile(r'^description$', re.I)})
    result.has_meta_description = bool(meta_desc and meta_desc.get('content', '').strip())

    # H1
    result.has_h1 = bool(soup.find('h1'))

    # robots.txt
    robots_html = _get_with_fallback(site_url.rstrip('/') + '/robots.txt', wp_config=wp_config)
    result.has_robots = bool(robots_html and 'user-agent' in robots_html.lower())

    # sitemap
    for path in ['/sitemap.xml', '/sitemap_index.xml', '/wp-sitemap.xml']:
        sm_html = _get_with_fallback(site_url.rstrip('/') + path, wp_config=wp_config)
        if sm_html and '<' in sm_html:
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
