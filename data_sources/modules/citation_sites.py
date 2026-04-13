# data_sources/modules/citation_sites.py
"""
Master list of UK citation sites and per-site metadata.

Tier 1 — Direct API (fully automated check + creation where API allows)
Tier 2 — DataForSEO Business Data endpoint (automated check)
Tier 3 — Playwright scrape (automated check + attempted form submission)
Tier 4 — Manual pack only (check attempted, creation is human-assisted)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Optional


SiteStatus = Literal['found', 'not_found', 'unknown', 'duplicate']
SubmitStatus = Literal['submitted', 'manual_required', 'pending_verification', 'failed']


@dataclass
class CitationSite:
    id: str
    name: str
    url: str                          # base URL
    tier: int                         # 1–4
    priority: int                     # 1–10 (10 = most important)
    submission_url: str               # direct URL to create/claim a listing
    # Tier 1
    api_module: Optional[str] = None  # e.g. 'google_business_profile'
    api_env_key: Optional[str] = None # env var name for API key
    # Tier 2
    dataforseo_endpoint: Optional[str] = None
    # Tier 3
    search_url_template: Optional[str] = None  # {name}, {postcode}, {city} placeholders
    name_selector: Optional[str] = None        # CSS selector for business name in results
    phone_selector: Optional[str] = None       # CSS selector for phone in results
    address_selector: Optional[str] = None     # CSS selector for address in results
    # Tier 3 form submission
    form_url_template: Optional[str] = None
    form_selectors: dict = field(default_factory=dict)


@dataclass
class CitationCheckResult:
    site: CitationSite
    status: SiteStatus = 'unknown'
    nap_match: Optional[bool] = None
    listing_url: Optional[str] = None
    found_name: str = ''
    found_phone: str = ''
    found_address: str = ''
    issues: list = field(default_factory=list)   # e.g. ['phone_mismatch', 'duplicate_found']
    submit_status: Optional[SubmitStatus] = None
    error: str = ''


# ── Master site list ──────────────────────────────────────────────────────────

CITATION_SITES: list[CitationSite] = [
    # ── Tier 1 — Direct API ──
    CitationSite(
        id='google_business_profile',
        name='Google Business Profile',
        url='https://business.google.com',
        tier=1, priority=10,
        submission_url='https://business.google.com/create',
        api_module='google_business_profile',
    ),
    CitationSite(
        id='yelp',
        name='Yelp',
        url='https://www.yelp.co.uk',
        tier=1, priority=8,
        submission_url='https://biz.yelp.co.uk/signup',
        api_module='yelp_fusion',
        api_env_key='YELP_API_KEY',
    ),
    CitationSite(
        id='foursquare',
        name='Foursquare',
        url='https://foursquare.com',
        tier=1, priority=6,
        submission_url='https://business.foursquare.com/venue/claim',
        api_module='foursquare',
        api_env_key='FOURSQUARE_API_KEY',
    ),
    # ── Tier 2 — DataForSEO ──
    CitationSite(
        id='trustpilot',
        name='Trustpilot',
        url='https://uk.trustpilot.com',
        tier=2, priority=8,
        submission_url='https://businessapp.b2b.trustpilot.com/signup',
        dataforseo_endpoint='/v3/business_data/trustpilot/search/live',
    ),
    CitationSite(
        id='tripadvisor',
        name='TripAdvisor',
        url='https://www.tripadvisor.co.uk',
        tier=2, priority=6,
        submission_url='https://www.tripadvisor.co.uk/GetListedNew',
        dataforseo_endpoint='/v3/business_data/tripadvisor/search/live',
    ),
    # ── Tier 3 — Playwright ──
    CitationSite(
        id='yell',
        name='Yell.com',
        url='https://www.yell.com',
        tier=3, priority=9,
        submission_url='https://www.yell.com/ucs/UcsSearchAction.do',
        search_url_template='https://www.yell.com/ucs/UcsSearchAction.do?keywords={name}&location={postcode}',
        name_selector='h3.businessCapsule--name a',
        phone_selector='span[itemprop="telephone"]',
        address_selector='span[itemprop="streetAddress"]',
        form_url_template='https://www.yellbusiness.co.uk/free-listing',
        form_selectors={
            'business_name': 'input[name="businessName"]',
            'phone': 'input[name="phone"]',
            'address': 'input[name="address"]',
            'postcode': 'input[name="postcode"]',
        },
    ),
    CitationSite(
        id='thomson_local',
        name='Thomson Local',
        url='https://www.thomsonlocal.com',
        tier=3, priority=8,
        submission_url='https://www.thomsonlocal.com/advertise',
        search_url_template='https://www.thomsonlocal.com/search/{postcode}/{name}',
        name_selector='.listing-details h2 a',
        phone_selector='.listing-phone',
        address_selector='.listing-address',
        form_url_template='https://www.thomsonlocal.com/free-listing',
        form_selectors={
            'business_name': '#business-name',
            'phone': '#phone',
            'postcode': '#postcode',
        },
    ),
    CitationSite(
        id='scoot',
        name='Scoot',
        url='https://www.scoot.co.uk',
        tier=3, priority=7,
        submission_url='https://www.scoot.co.uk/add-business',
        search_url_template='https://www.scoot.co.uk/find/{name}/{postcode}',
        name_selector='.result-name a',
        phone_selector='.result-phone',
        address_selector='.result-address',
        form_url_template='https://www.scoot.co.uk/add-business',
        form_selectors={
            'business_name': 'input[name="name"]',
            'phone': 'input[name="phone"]',
            'postcode': 'input[name="postcode"]',
        },
    ),
    CitationSite(
        id='192com',
        name='192.com',
        url='https://www.192.com',
        tier=3, priority=6,
        submission_url='https://www.192.com/atoz/business/add/',
        search_url_template='https://www.192.com/atoz/business/{name}/{postcode}/',
        name_selector='.listing-title',
        phone_selector='.listing-phone',
        address_selector='.listing-address',
        form_url_template='https://www.192.com/atoz/business/add/',
        form_selectors={},
    ),
    CitationSite(
        id='cylex',
        name='Cylex UK',
        url='https://www.cylex-uk.co.uk',
        tier=4, priority=5,  # Tier 4: CAPTCHA blocks Playwright — manual pack only
        submission_url='https://www.cylex-uk.co.uk/my-company.html',
    ),
    CitationSite(
        id='freeindex',
        name='FreeIndex',
        url='https://www.freeindex.co.uk',
        tier=3, priority=5,
        submission_url='https://www.freeindex.co.uk/register.htm',
        search_url_template='https://www.freeindex.co.uk/search.htm?q={name}&loc={postcode}',
        name_selector='h2.listing-title a',
        phone_selector='span.telephone',
        address_selector='span.address',
        form_url_template='https://www.freeindex.co.uk/register.htm',
        form_selectors={},
    ),
    CitationSite(
        id='brownbook',
        name='Brownbook',
        url='https://www.brownbook.net',
        tier=3, priority=4,
        submission_url='https://www.brownbook.net/add-business/',
        search_url_template='https://www.brownbook.net/businesses/near/{postcode}/{name}/',
        name_selector='h2.listing-name',
        phone_selector='.listing-phone',
        address_selector='.listing-address',
        form_url_template='https://www.brownbook.net/add-business/',
        form_selectors={},
    ),
    CitationSite(
        id='misterwhat',
        name='Misterwhat',
        url='https://misterwhat.co.uk',
        tier=3, priority=4,
        submission_url='https://misterwhat.co.uk/businesses/add',
        search_url_template='https://misterwhat.co.uk/search?q={name}&near={postcode}',
        name_selector='.result-name a',
        phone_selector='.result-phone',
        address_selector='.result-address',
        form_url_template='https://misterwhat.co.uk/businesses/add',
        form_selectors={},
    ),
    CitationSite(
        id='hotfrog',
        name='Hotfrog',
        url='https://www.hotfrog.co.uk',
        tier=3, priority=5,
        submission_url='https://www.hotfrog.co.uk/AddBusiness.aspx',
        search_url_template='https://www.hotfrog.co.uk/search/uk/{postcode}/{name}',
        name_selector='h2.businessname a',
        phone_selector='.phone-number',
        address_selector='.address',
        form_url_template='https://www.hotfrog.co.uk/AddBusiness.aspx',
        form_selectors={},
    ),
    # ── Tier 4 — Manual pack ──
    CitationSite(
        id='apple_maps',
        name='Apple Business Connect',
        url='https://businessconnect.apple.com',
        tier=4, priority=8,
        submission_url='https://businessconnect.apple.com',
    ),
    CitationSite(
        id='bing_places',
        name='Bing Places',
        url='https://www.bingplaces.com',
        tier=4, priority=8,
        submission_url='https://www.bingplaces.com',
    ),
    CitationSite(
        id='facebook',
        name='Facebook Business',
        url='https://www.facebook.com',
        tier=4, priority=7,
        submission_url='https://www.facebook.com/pages/create',
    ),
    CitationSite(
        id='treatwell',
        name='Treatwell',
        url='https://www.treatwell.co.uk',
        tier=4, priority=7,
        submission_url='https://www.treatwell.co.uk/join/',
    ),
    CitationSite(
        id='fresha',
        name='Fresha',
        url='https://www.fresha.com',
        tier=4, priority=6,
        submission_url='https://www.fresha.com/for-business',
    ),
    CitationSite(
        id='bark',
        name='Bark.com',
        url='https://www.bark.com',
        tier=4, priority=6,
        submission_url='https://www.bark.com/en/gb/professionals/',
    ),
    CitationSite(
        id='nextdoor',
        name='Nextdoor',
        url='https://nextdoor.co.uk',
        tier=4, priority=5,
        submission_url='https://business.nextdoor.com/en-gb',
    ),
    CitationSite(
        id='checkatrade',
        name='Checkatrade',
        url='https://www.checkatrade.com',
        tier=4, priority=5,
        submission_url='https://www.checkatrade.com/join/',
    ),
    CitationSite(
        id='yelp_create',
        name='Yelp (claim/create)',
        url='https://biz.yelp.co.uk',
        tier=4, priority=8,
        submission_url='https://biz.yelp.co.uk/claim',
    ),
]

# Fast lookup by ID
SITE_BY_ID: dict[str, CitationSite] = {s.id: s for s in CITATION_SITES}
