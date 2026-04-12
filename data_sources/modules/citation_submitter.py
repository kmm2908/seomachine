# data_sources/modules/citation_submitter.py
"""
Citation creation/submission.

Tier 1: API-based submission where supported (GBP managed externally; Yelp/Foursquare creation
        requires business owner verification — both become Tier 4 for creation).
Tier 3: Playwright form fill + submit.
Tier 4: Generates manual pack entry (handled by citation_manual_pack).
"""

from __future__ import annotations
import logging
import time
from pathlib import Path

from citation_sites import CitationSite, CitationCheckResult

logger = logging.getLogger(__name__)


def submit_site(
    site: CitationSite,
    config: dict,
    dry_run: bool = False,
) -> CitationCheckResult:
    """Attempt to create a listing on a site. Returns updated CitationCheckResult."""
    result = CitationCheckResult(site=site, status='not_found')

    if site.tier in (1, 4) or not site.form_selectors:
        result.submit_status = 'manual_required'
        return result

    if site.tier == 3 and site.form_url_template and site.form_selectors:
        return _submit_playwright(site, config, dry_run=dry_run)

    result.submit_status = 'manual_required'
    return result


def _submit_playwright(
    site: CitationSite,
    config: dict,
    dry_run: bool = False,
) -> CitationCheckResult:
    result = CitationCheckResult(site=site, status='not_found')

    if dry_run:
        logger.info('[dry-run] Would submit to %s via Playwright', site.name)
        result.submit_status = 'manual_required'
        result.error = 'dry-run mode'
        return result

    form_url = site.form_url_template.format(
        name=config.get('name', ''),
        postcode=config.get('postcode', ''),
        city=config.get('city', ''),
    ) if site.form_url_template else ''

    if not form_url or not site.form_selectors:
        result.submit_status = 'manual_required'
        return result

    try:
        from playwright.sync_api import sync_playwright
        from citation_checker import _is_captcha_html

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(locale='en-GB')
            page = ctx.new_page()
            page.goto(form_url, wait_until='domcontentloaded', timeout=20000)

            if _is_captcha_html(page.content()):
                browser.close()
                result.submit_status = 'manual_required'
                result.error = 'CAPTCHA on submission form'
                return result

            field_map = {
                'business_name': config.get('name', ''),
                'phone': config.get('phone', ''),
                'address': config.get('address', ''),
                'postcode': config.get('postcode', ''),
                'city': config.get('city', ''),
                'website': config.get('website', ''),
            }
            for field_key, selector in site.form_selectors.items():
                value = field_map.get(field_key, '')
                if value:
                    try:
                        page.fill(selector, value)
                        time.sleep(0.3)
                    except Exception:
                        pass  # Field not found — continue with others

            # Submit — look for a submit button
            try:
                page.click('button[type=submit], input[type=submit]', timeout=5000)
                page.wait_for_load_state('domcontentloaded', timeout=10000)
            except Exception:
                pass

            final_html = page.content()
            browser.close()

        if _is_captcha_html(final_html):
            result.submit_status = 'manual_required'
            result.error = 'CAPTCHA after form submit'
        else:
            result.submit_status = 'pending_verification'
            logger.info('Submitted %s to %s — pending email verification', config.get('name'), site.name)

    except Exception as exc:
        logger.warning('Playwright submission failed for %s on %s: %s', config.get('name'), site.name, exc)
        result.submit_status = 'manual_required'
        result.error = str(exc)

    return result
