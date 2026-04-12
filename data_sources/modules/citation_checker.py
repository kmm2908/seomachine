# data_sources/modules/citation_checker.py
"""
Citation presence checker — routes each site to the correct tier method.

Tier 1: Direct API (Yelp Fusion, Foursquare, GBP)
Tier 2: DataForSEO Business Data endpoints
Tier 3: Playwright scrape
Tier 4: Not checked automatically (manual pack only)
"""

from __future__ import annotations
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))

from citation_sites import CitationSite, CitationCheckResult
from nap_utils import compare_name, compare_phone, compare_address

logger = logging.getLogger(__name__)

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}


# ── Tier 1: Yelp Fusion ───────────────────────────────────────────────────────

def _check_yelp(site: CitationSite, config: dict) -> CitationCheckResult:
    result = CitationCheckResult(site=site)
    api_key = os.getenv('YELP_API_KEY', '')
    if not api_key:
        result.status = 'unknown'
        result.error = 'YELP_API_KEY not set'
        return result
    try:
        resp = requests.get(
            'https://api.yelp.com/v3/businesses/search',
            headers={'Authorization': f'Bearer {api_key}'},
            params={
                'term': config.get('name', ''),
                'location': config.get('address', ''),
                'limit': 5,
            },
            timeout=15,
        )
        resp.raise_for_status()
        businesses = resp.json().get('businesses', [])
        return _match_api_results(site, config, businesses,
                                  name_key='name',
                                  phone_key='phone',
                                  address_key=None,
                                  url_key='url')
    except Exception as exc:
        logger.warning('Yelp check failed for %s: %s', config.get('name'), exc)
        result.status = 'unknown'
        result.error = str(exc)
        return result


# ── Tier 1: Foursquare ───────────────────────────────────────────────────────

def _check_foursquare(site: CitationSite, config: dict) -> CitationCheckResult:
    result = CitationCheckResult(site=site)
    api_key = os.getenv('FOURSQUARE_API_KEY', '')
    if not api_key:
        result.status = 'unknown'
        result.error = 'FOURSQUARE_API_KEY not set'
        return result
    try:
        resp = requests.get(
            'https://api.foursquare.com/v3/places/search',
            headers={
                'Authorization': api_key,
                'Accept': 'application/json',
            },
            params={
                'query': config.get('name', ''),
                'near': config.get('city', '') or config.get('postcode', ''),
                'limit': 5,
            },
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get('results', [])
        businesses = [
            {
                'name': r.get('name', ''),
                'url': f"https://foursquare.com/v/{r.get('fsq_id', '')}",
                'phone': r.get('tel', ''),
                'address': ', '.join(r.get('location', {}).get('formatted_address', '').split(',')),
            }
            for r in results
        ]
        return _match_api_results(site, config, businesses,
                                  name_key='name', phone_key='phone',
                                  address_key='address', url_key='url')
    except Exception as exc:
        logger.warning('Foursquare check failed for %s: %s', config.get('name'), exc)
        result.status = 'unknown'
        result.error = str(exc)
        return result


# ── Shared result matching ────────────────────────────────────────────────────

def _match_api_results(site, config, businesses, name_key, phone_key, address_key, url_key):
    """Find a matching business in API results and compare NAP."""
    result = CitationCheckResult(site=site)
    biz_name = config.get('name', '')

    for b in businesses:
        candidate_name = b.get(name_key, '')
        if compare_name(biz_name, candidate_name) == 'match':
            result.status = 'found'
            result.listing_url = b.get(url_key, '')
            result.found_name = candidate_name
            result.found_phone = b.get(phone_key, '')
            result.found_address = b.get(address_key, '') if address_key else ''

            issues = []
            ph_status = compare_phone(config.get('phone', ''), result.found_phone)
            addr_status = compare_address(config.get('address', ''), result.found_address) if result.found_address else 'unknown'

            if ph_status == 'mismatch':
                issues.append('phone_mismatch')
            if addr_status == 'mismatch':
                issues.append('address_mismatch')

            result.issues = issues
            result.nap_match = len(issues) == 0
            return result

    result.status = 'not_found'
    return result


# ── Tier 1: Google Business Profile ─────────────────────────────────────────

def _check_gbp(site: CitationSite, config: dict) -> CitationCheckResult:
    result = CitationCheckResult(site=site)
    gbp_id = config.get('gbp_location_id', '')
    if not gbp_id:
        result.status = 'unknown'
        result.error = 'gbp_location_id not in config'
        return result
    try:
        from google_business_profile import GoogleBusinessProfile
        gbp = GoogleBusinessProfile.from_client_config(config)
        info = gbp.get_business_info(gbp_id)
        if info:
            result.status = 'found'
            result.found_name = info.get('name', '')
            result.found_phone = info.get('telephone', '')
            result.found_address = str(info.get('address', ''))
            result.listing_url = f'https://business.google.com/location/{gbp_id}'
            issues = []
            if compare_phone(config.get('phone', ''), result.found_phone) == 'mismatch':
                issues.append('phone_mismatch')
            if compare_address(config.get('address', ''), result.found_address) == 'mismatch':
                issues.append('address_mismatch')
            result.issues = issues
            result.nap_match = len(issues) == 0
        else:
            result.status = 'not_found'
    except Exception as exc:
        result.status = 'unknown'
        result.error = str(exc)
    return result


# ── Tier 2: DataForSEO ────────────────────────────────────────────────────────

def _check_dataforseo(site: CitationSite, config: dict) -> CitationCheckResult:
    result = CitationCheckResult(site=site)
    try:
        from dataforseo import DataForSEO
        client = DataForSEO()
        payload = [{
            'keyword': config.get('name', ''),
            'location_code': 2826,
            'language_code': 'en',
        }]
        data = client._post(site.dataforseo_endpoint, payload)
        tasks = data.get('tasks', [])
        if not tasks or tasks[0].get('status_code') != 20000:
            result.status = 'unknown'
            return result

        items = (tasks[0].get('result') or [{}])[0].get('items') or []
        biz_name = config.get('name', '').lower()
        for item in items:
            candidate = item.get('title', '') or item.get('name', '')
            if compare_name(biz_name, candidate) == 'match':
                result.status = 'found'
                result.found_name = candidate
                result.found_phone = item.get('phone', '')
                result.found_address = item.get('address', '')
                result.listing_url = item.get('url', '') or item.get('profile_url', '')
                issues = []
                if result.found_phone and compare_phone(config.get('phone', ''), result.found_phone) == 'mismatch':
                    issues.append('phone_mismatch')
                if result.found_address and compare_address(config.get('address', ''), result.found_address) == 'mismatch':
                    issues.append('address_mismatch')
                result.issues = issues
                result.nap_match = len(issues) == 0
                return result

        result.status = 'not_found'
    except Exception as exc:
        logger.warning('DataForSEO check failed for %s on %s: %s', config.get('name'), site.id, exc)
        result.status = 'unknown'
        result.error = str(exc)
    return result


# ── Tier 3: Playwright scrape ─────────────────────────────────────────────────

def _check_playwright(site: CitationSite, config: dict, dry_run: bool = False) -> CitationCheckResult:
    result = CitationCheckResult(site=site)
    if not site.search_url_template:
        result.status = 'unknown'
        result.error = 'No search_url_template defined'
        return result

    search_url = site.search_url_template.format(
        name=config.get('name', '').replace(' ', '+'),
        postcode=config.get('postcode', ''),
        city=config.get('city', ''),
    )

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=_HEADERS['User-Agent'],
                locale='en-GB',
            )
            page = ctx.new_page()
            page.goto(search_url, wait_until='domcontentloaded', timeout=20000)
            html = page.content()
            browser.close()

        if _is_captcha_html(html):
            result.status = 'unknown'
            result.error = 'CAPTCHA detected'
            return result

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        names = soup.select(site.name_selector) if site.name_selector else []
        biz_name = config.get('name', '')

        for i, name_el in enumerate(names[:5]):
            candidate_name = name_el.get_text(strip=True)
            if compare_name(biz_name, candidate_name) == 'match':
                result.status = 'found'
                result.found_name = candidate_name

                if site.phone_selector:
                    ph_els = soup.select(site.phone_selector)
                    result.found_phone = ph_els[i].get_text(strip=True) if i < len(ph_els) else ''
                if site.address_selector:
                    addr_els = soup.select(site.address_selector)
                    result.found_address = addr_els[i].get_text(strip=True) if i < len(addr_els) else ''

                result.listing_url = name_el.get('href', '')
                issues = []
                if result.found_phone and compare_phone(config.get('phone', ''), result.found_phone) == 'mismatch':
                    issues.append('phone_mismatch')
                if result.found_address and compare_address(config.get('address', ''), result.found_address) == 'mismatch':
                    issues.append('address_mismatch')
                result.issues = issues
                result.nap_match = len(issues) == 0
                return result

        result.status = 'not_found'
    except Exception as exc:
        logger.warning('Playwright check failed for %s on %s: %s', config.get('name'), site.id, exc)
        result.status = 'unknown'
        result.error = str(exc)

    return result


def _is_captcha_html(html: str) -> bool:
    markers = ['captcha', 'cf-challenge', 'challenge-form', 'access denied', 'robot or human']
    lower = html.lower()
    return any(m in lower for m in markers)


# ── Main dispatcher ───────────────────────────────────────────────────────────

def check_site(site: CitationSite, config: dict, dry_run: bool = False) -> CitationCheckResult:
    """Route a site to the correct tier checker."""
    try:
        if site.tier == 1:
            if site.id == 'google_business_profile':
                return _check_gbp(site, config)
            elif site.id == 'yelp':
                return _check_yelp(site, config)
            elif site.id == 'foursquare':
                return _check_foursquare(site, config)
        elif site.tier == 2:
            return _check_dataforseo(site, config)
        elif site.tier == 3:
            return _check_playwright(site, config, dry_run=dry_run)
        else:  # tier 4
            result = CitationCheckResult(site=site)
            result.status = 'unknown'
            result.error = 'Tier 4 — manual check required'
            return result
    except Exception as exc:
        logger.error('Unhandled error checking %s: %s', site.id, exc)
        r = CitationCheckResult(site=site)
        r.status = 'unknown'
        r.error = str(exc)
        return r
    # Fallback for unhandled Tier 1 sites
    result = CitationCheckResult(site=site)
    result.status = 'unknown'
    result.error = f'No checker implemented for {site.id}'
    return result
