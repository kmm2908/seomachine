# Citation Generator & Listing Audit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tiered citation audit and creation system for UK local business clients, integrated into the existing `/audit` pipeline.

**Architecture:** Four-tier approach — direct APIs (GBP/Yelp/Foursquare) for checking, DataForSEO for TrustPilot/TripAdvisor, Playwright scraping+form-fill for UK directories, and a pre-filled HTML manual pack for everything else. Results roll up into a citation score that replaces/expands the existing NAP section in the audit report.

**Tech Stack:** Python 3.11+, requests, playwright-python, BeautifulSoup4, DataForSEO API (existing), Yelp Fusion API, Foursquare Places API v3

---

## File Map

**New files:**
- `data_sources/modules/citation_sites.py` — master site list + `CitationSite` dataclass
- `data_sources/modules/citation_checker.py` — per-site presence check (all 4 tiers)
- `data_sources/modules/citation_submitter.py` — per-site creation (Tiers 1, 3, 4)
- `data_sources/modules/citation_state.py` — state.json load/save/staleness
- `data_sources/modules/citation_manager.py` — orchestrator (audit/create/full)
- `data_sources/modules/nap_utils.py` — shared NAP normalisation (extracted from collectors.py)
- `src/citations/run_citations.py` — CLI entry point
- `tests/test_citations.py` — unit tests

**Modified files:**
- `data_sources/modules/scoring.py` — add `CitationResult` dataclass; expand NAP & Citations to 15 pts
- `src/audit/collectors.py` — import nap_utils instead of local functions; add `collect_citations()`
- `src/audit/run_audit.py` — call `collect_citations()`; update console display
- `src/audit/report.py` — add citation section to HTML/markdown output

---

## Task 1: NAP Utilities Module

Extract the private `_normalise_phone` and `_normalise_address` functions from `collectors.py` into a shared module, and add a `compare_nap()` function. This prevents duplication between the audit and the new citation checker.

**Files:**
- Create: `data_sources/modules/nap_utils.py`
- Modify: `src/audit/collectors.py` (lines 348–357 — remove private functions, import from nap_utils)
- Test: `tests/test_citations.py`

- [ ] **Step 1: Create nap_utils.py**

```python
# data_sources/modules/nap_utils.py
"""Shared NAP normalisation and comparison utilities."""

from __future__ import annotations
import re
from typing import Literal

NAPMatchStatus = Literal['match', 'mismatch', 'unknown']


def normalise_phone(phone: str) -> str:
    """Strip non-digit characters for comparison."""
    return re.sub(r'\D', '', phone)


def normalise_address(addr: str) -> str:
    """Lowercase + collapse whitespace for loose comparison."""
    return re.sub(r'\s+', ' ', addr.lower().strip())


def compare_phone(a: str, b: str) -> NAPMatchStatus:
    if not a or not b:
        return 'unknown'
    return 'match' if normalise_phone(a) == normalise_phone(b) else 'mismatch'


def compare_address(a: str, b: str) -> NAPMatchStatus:
    if not a or not b:
        return 'unknown'
    na, nb = normalise_address(a), normalise_address(b)
    return 'match' if (na in nb or nb in na or na == nb) else 'mismatch'


def compare_name(a: str, b: str) -> NAPMatchStatus:
    if not a or not b:
        return 'unknown'
    return 'match' if a.lower().strip() == b.lower().strip() else 'mismatch'
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_citations.py
import pytest
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))

from nap_utils import normalise_phone, normalise_address, compare_phone, compare_address, compare_name

def test_normalise_phone_strips_spaces_and_punctuation():
    assert normalise_phone('+44 141 552 1234') == '441415521234'
    assert normalise_phone('0141-552-1234') == '01415521234'

def test_compare_phone_match():
    assert compare_phone('0141 552 1234', '01415521234') == 'match'

def test_compare_phone_mismatch():
    assert compare_phone('0141 552 1234', '0141 552 9999') == 'mismatch'

def test_compare_phone_unknown_when_empty():
    assert compare_phone('', '0141 552 1234') == 'unknown'

def test_compare_address_partial_match():
    assert compare_address('Central Chambers, 93 Hope Street, Glasgow, G2 6LD',
                           '93 hope street glasgow') == 'match'

def test_compare_name_case_insensitive():
    assert compare_name('Glasgow Thai Massage', 'glasgow thai massage') == 'match'

def test_compare_name_mismatch():
    assert compare_name('Glasgow Thai Massage', 'Thai House Glasgow') == 'mismatch'
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine"
python3 -m pytest tests/test_citations.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'nap_utils'` or similar.

- [ ] **Step 4: Run tests — expect PASS after creating module**

```bash
python3 -m pytest tests/test_citations.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Update collectors.py to import from nap_utils**

Replace lines 348–357 in `src/audit/collectors.py`:

```python
# Remove these two private functions:
# def _normalise_phone(phone: str) -> str: ...
# def _normalise_address(addr: str) -> str: ...

# Add this import near the top (after ROOT/sys.path setup):
from nap_utils import normalise_phone as _normalise_phone, normalise_address as _normalise_address
```

- [ ] **Step 6: Verify audit still works**

```bash
python3 -m pytest tests/ -v -k "not test_citations" 2>&1 | tail -10
```

Expected: existing tests pass.

- [ ] **Step 7: Commit**

```bash
git add data_sources/modules/nap_utils.py tests/test_citations.py src/audit/collectors.py
git commit -m "feat: extract shared NAP normalisation utilities to nap_utils.py"
```

---

## Task 2: Citation Site List & Core Data Structures

Define `CitationSite`, `CitationCheckResult`, and the master list of ~35 UK citation sites. Each site has a tier (1–4), priority, and tier-specific config (API endpoint, search URL template, form selectors).

**Files:**
- Create: `data_sources/modules/citation_sites.py`

- [ ] **Step 1: Create citation_sites.py**

```python
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
        tier=3, priority=5,
        submission_url='https://www.cylex-uk.co.uk/my-company.html',
        search_url_template='https://www.cylex-uk.co.uk/companies/{name}-{postcode}.html',
        name_selector='h2.company-name',
        phone_selector='div.phone',
        address_selector='div.address',
        form_url_template='https://www.cylex-uk.co.uk/my-company.html',
        form_selectors={},
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
```

- [ ] **Step 2: Add import test**

In `tests/test_citations.py` add:

```python
from citation_sites import CITATION_SITES, SITE_BY_ID, CitationSite, CitationCheckResult

def test_site_list_has_expected_sites():
    ids = {s.id for s in CITATION_SITES}
    assert 'google_business_profile' in ids
    assert 'yell' in ids
    assert 'trustpilot' in ids
    assert 'apple_maps' in ids

def test_site_by_id_lookup():
    assert SITE_BY_ID['yell'].tier == 3
    assert SITE_BY_ID['google_business_profile'].tier == 1
    assert SITE_BY_ID['trustpilot'].priority == 8

def test_citation_check_result_defaults():
    site = SITE_BY_ID['yell']
    r = CitationCheckResult(site=site)
    assert r.status == 'unknown'
    assert r.issues == []
```

- [ ] **Step 3: Run tests**

```bash
python3 -m pytest tests/test_citations.py -v
```

Expected: all new tests pass.

- [ ] **Step 4: Commit**

```bash
git add data_sources/modules/citation_sites.py tests/test_citations.py
git commit -m "feat: citation site list and core data structures"
```

---

## Task 3: Citation State Manager

Handles `clients/[abbr]/citations/state.json` — tracks per-site check results, listing URLs, last check date, and submit status. Determines which sites are due for re-checking (30-day default cadence).

**Files:**
- Create: `data_sources/modules/citation_state.py`
- Create dir pattern: `clients/[abbr]/citations/` (created on first save)

- [ ] **Step 1: Create citation_state.py**

```python
# data_sources/modules/citation_state.py
"""Manages persistent citation state per client in clients/[abbr]/citations/state.json."""

from __future__ import annotations
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from citation_sites import CitationCheckResult, CitationSite, CITATION_SITES


_DEFAULT_CADENCE_DAYS = 30


class CitationState:
    def __init__(self, abbr: str, root: Path):
        self.abbr = abbr
        self._dir = root / 'clients' / abbr / 'citations'
        self._path = self._dir / 'state.json'
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            return json.loads(self._path.read_text())
        return {'last_run': None, 'sites': {}}

    def save(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._data['last_run'] = date.today().isoformat()
        self._path.write_text(json.dumps(self._data, indent=2))

    def is_due(self, site_id: str, cadence_days: int = _DEFAULT_CADENCE_DAYS) -> bool:
        """Return True if site hasn't been checked within cadence_days."""
        entry = self._data['sites'].get(site_id, {})
        last_checked = entry.get('last_checked')
        if not last_checked:
            return True
        last = datetime.fromisoformat(last_checked).date()
        return (date.today() - last).days >= cadence_days

    def get_due_sites(self, sites: list[CitationSite], force: bool = False) -> list[CitationSite]:
        """Return sites that need checking."""
        if force:
            return sites
        return [s for s in sites if self.is_due(s.id)]

    def update(self, result: CitationCheckResult) -> None:
        """Record the outcome of a single site check."""
        self._data['sites'][result.site.id] = {
            'status': result.status,
            'listing_url': result.listing_url,
            'nap_match': result.nap_match,
            'found_name': result.found_name,
            'found_phone': result.found_phone,
            'found_address': result.found_address,
            'issues': result.issues,
            'submit_status': result.submit_status,
            'last_checked': date.today().isoformat(),
        }

    def get_not_found(self) -> list[str]:
        """Return site IDs with status not_found and no pending submission."""
        return [
            sid for sid, data in self._data['sites'].items()
            if data.get('status') == 'not_found'
            and data.get('submit_status') is None
        ]

    def all_results_snapshot(self) -> list[dict]:
        """Return all known site states as a list, sorted by site priority desc."""
        site_priority = {s.id: s.priority for s in CITATION_SITES}
        return sorted(
            [{'id': sid, **data} for sid, data in self._data['sites'].items()],
            key=lambda x: site_priority.get(x['id'], 0),
            reverse=True,
        )
```

- [ ] **Step 2: Add tests**

In `tests/test_citations.py` add:

```python
import tempfile, os
from citation_state import CitationState
from citation_sites import CITATION_SITES, SITE_BY_ID, CitationCheckResult

def _make_state(tmp_path):
    (tmp_path / 'clients' / 'test' / 'citations').mkdir(parents=True, exist_ok=True)
    return CitationState('test', tmp_path)

def test_new_site_is_due(tmp_path):
    state = _make_state(tmp_path)
    assert state.is_due('yell') is True

def test_site_not_due_after_recent_check(tmp_path):
    state = _make_state(tmp_path)
    result = CitationCheckResult(site=SITE_BY_ID['yell'], status='found')
    state.update(result)
    state.save()
    # Reload and check
    state2 = CitationState('test', tmp_path)
    assert state2.is_due('yell') is False

def test_get_due_sites_respects_cadence(tmp_path):
    state = _make_state(tmp_path)
    result = CitationCheckResult(site=SITE_BY_ID['yell'], status='found')
    state.update(result)
    state.save()
    state2 = CitationState('test', tmp_path)
    due = state2.get_due_sites([SITE_BY_ID['yell'], SITE_BY_ID['trustpilot']])
    ids = [s.id for s in due]
    assert 'yell' not in ids        # just checked
    assert 'trustpilot' in ids      # never checked

def test_get_due_sites_force_returns_all(tmp_path):
    state = _make_state(tmp_path)
    result = CitationCheckResult(site=SITE_BY_ID['yell'], status='found')
    state.update(result)
    state.save()
    state2 = CitationState('test', tmp_path)
    due = state2.get_due_sites([SITE_BY_ID['yell']], force=True)
    assert len(due) == 1

def test_get_not_found(tmp_path):
    state = _make_state(tmp_path)
    r = CitationCheckResult(site=SITE_BY_ID['yell'], status='not_found')
    state.update(r)
    assert 'yell' in state.get_not_found()
```

- [ ] **Step 3: Run tests**

```bash
python3 -m pytest tests/test_citations.py -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add data_sources/modules/citation_state.py tests/test_citations.py
git commit -m "feat: citation state manager (state.json load/save/staleness)"
```

---

## Task 4: Citation Checker — Tier 1 APIs (Yelp Fusion + Foursquare)

GBP is already handled by `google_business_profile.py`. This task adds Yelp Fusion and Foursquare API checks.

**Files:**
- Create: `data_sources/modules/citation_checker.py`

- [ ] **Step 1: Add YELP_API_KEY and FOURSQUARE_API_KEY to .env**

```bash
# In .env, add:
YELP_API_KEY=
FOURSQUARE_API_KEY=
```

(Leave blank if no key yet — checks will return `unknown` gracefully.)

- [ ] **Step 2: Create citation_checker.py with Tier 1 methods**

```python
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
                                  address_key=None,  # Yelp address is nested
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

            # NAP checks
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
```

- [ ] **Step 3: Add tests (mock API calls)**

In `tests/test_citations.py` add:

```python
from unittest.mock import patch, MagicMock
from citation_checker import _check_yelp, _check_foursquare, _match_api_results
from citation_sites import SITE_BY_ID

_GTM_CONFIG = {
    'name': 'Glasgow Thai Massage',
    'address': '142 West Nile Street, Glasgow, G1 2RQ',
    'phone': '0141 552 1234',
    'city': 'Glasgow',
    'postcode': 'G1 2RQ',
}

def test_yelp_found_with_nap_match():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {'businesses': [
        {'name': 'Glasgow Thai Massage', 'phone': '01415521234',
         'url': 'https://yelp.co.uk/biz/gtm', 'id': 'abc'}
    ]}
    mock_resp.raise_for_status = MagicMock()
    with patch('citation_checker.requests.get', return_value=mock_resp):
        with patch.dict('os.environ', {'YELP_API_KEY': 'test-key'}):
            r = _check_yelp(SITE_BY_ID['yelp'], _GTM_CONFIG)
    assert r.status == 'found'
    assert r.nap_match is True

def test_yelp_not_found():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {'businesses': []}
    mock_resp.raise_for_status = MagicMock()
    with patch('citation_checker.requests.get', return_value=mock_resp):
        with patch.dict('os.environ', {'YELP_API_KEY': 'test-key'}):
            r = _check_yelp(SITE_BY_ID['yelp'], _GTM_CONFIG)
    assert r.status == 'not_found'

def test_yelp_returns_unknown_without_api_key():
    with patch.dict('os.environ', {}, clear=True):
        r = _check_yelp(SITE_BY_ID['yelp'], _GTM_CONFIG)
    assert r.status == 'unknown'
    assert 'YELP_API_KEY' in r.error
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_citations.py::test_yelp_found_with_nap_match tests/test_citations.py::test_yelp_not_found tests/test_citations.py::test_yelp_returns_unknown_without_api_key -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add data_sources/modules/citation_checker.py tests/test_citations.py .env
git commit -m "feat: citation checker Tier 1 (Yelp Fusion + Foursquare API)"
```

---

## Task 5: Citation Checker — Tier 2 (DataForSEO)

Add DataForSEO-powered checks for TrustPilot and TripAdvisor.

**Files:**
- Modify: `data_sources/modules/citation_checker.py`

- [ ] **Step 1: Add Tier 2 method to citation_checker.py**

```python
# Add to citation_checker.py after Tier 1 section

# ── Tier 2: DataForSEO ────────────────────────────────────────────────────────

def _check_dataforseo(site: CitationSite, config: dict) -> CitationCheckResult:
    result = CitationCheckResult(site=site)
    try:
        from dataforseo import DataForSEO
        client = DataForSEO()
        payload = [{
            'keyword': config.get('name', ''),
            'location_code': 2826,   # United Kingdom
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
```

- [ ] **Step 2: Add tests**

```python
def test_dataforseo_found():
    from citation_checker import _check_dataforseo
    mock_client = MagicMock()
    mock_client._post.return_value = {
        'tasks': [{
            'status_code': 20000,
            'result': [{'items': [
                {'title': 'Glasgow Thai Massage', 'phone': '0141 552 1234',
                 'address': '142 West Nile Street, Glasgow', 'url': 'https://trustpilot.com/review/gtm'}
            ]}]
        }]
    }
    with patch('citation_checker.DataForSEO', return_value=mock_client):
        r = _check_dataforseo(SITE_BY_ID['trustpilot'], _GTM_CONFIG)
    assert r.status == 'found'
    assert r.nap_match is True

def test_dataforseo_not_found():
    from citation_checker import _check_dataforseo
    mock_client = MagicMock()
    mock_client._post.return_value = {
        'tasks': [{'status_code': 20000, 'result': [{'items': []}]}]
    }
    with patch('citation_checker.DataForSEO', return_value=mock_client):
        r = _check_dataforseo(SITE_BY_ID['trustpilot'], _GTM_CONFIG)
    assert r.status == 'not_found'
```

- [ ] **Step 3: Run tests**

```bash
python3 -m pytest tests/test_citations.py::test_dataforseo_found tests/test_citations.py::test_dataforseo_not_found -v
```

Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add data_sources/modules/citation_checker.py tests/test_citations.py
git commit -m "feat: citation checker Tier 2 (DataForSEO TrustPilot/TripAdvisor)"
```

---

## Task 6: Citation Checker — Tier 3 (Playwright Scraping)

Generic Playwright-based check: uses `search_url_template` and CSS selectors from each `CitationSite` to search and extract business NAP. If CAPTCHA is detected, marks as `unknown`.

**Files:**
- Modify: `data_sources/modules/citation_checker.py`

- [ ] **Step 1: Add Tier 3 method to citation_checker.py**

```python
# Add to citation_checker.py

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

                # Try to get phone and address from same result container
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
```

- [ ] **Step 2: Add route dispatcher to citation_checker.py**

```python
# Add at bottom of citation_checker.py

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
```

- [ ] **Step 3: Add dispatcher test**

```python
def test_check_site_routes_tier4_to_unknown():
    from citation_checker import check_site
    r = check_site(SITE_BY_ID['apple_maps'], _GTM_CONFIG)
    assert r.status == 'unknown'
    assert 'Tier 4' in r.error

def test_is_captcha_html_detects_cloudflare():
    from citation_checker import _is_captcha_html
    assert _is_captcha_html('<html><body class="cf-challenge">prove you are human</body></html>') is True
    assert _is_captcha_html('<html><body><h1>Results for Glasgow</h1></body></html>') is False
```

- [ ] **Step 4: Run all citation tests**

```bash
python3 -m pytest tests/test_citations.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add data_sources/modules/citation_checker.py tests/test_citations.py
git commit -m "feat: citation checker Tier 3 (Playwright scrape) + route dispatcher"
```

---

## Task 7: Citation Scoring

Add `CitationResult` dataclass to `scoring.py` and update `AuditResult` to include it. The NAP & Citations section stays at 15 pts total.

**Files:**
- Modify: `data_sources/modules/scoring.py`

- [ ] **Step 1: Add CitationResult to scoring.py**

After the `NAPResult` class (line ~183), add:

```python
@dataclass
class CitationResult:
    """Citation presence and NAP consistency across directories (max 15 pts).
    Replaces the schema-only NAPResult as the 'nap' scoring category.
    """
    # Schema NAP (carried over from original NAPResult checks)
    schema_name_match: str = 'unknown'
    schema_address_match: str = 'unknown'
    schema_phone_match: str = 'unknown'
    # Citation coverage
    total_sites: int = 0
    found_count: int = 0
    nap_issue_count: int = 0
    duplicate_count: int = 0
    critical_missing: list = field(default_factory=list)  # GBP/Bing/Yelp
    # Per-site results (CitationCheckResult objects)
    site_results: list = field(default_factory=list)
    score: int = 0
    findings: List[str] = field(default_factory=list)

    def compute_score(self) -> int:
        pts = 0

        # Schema NAP (kept for backward compat when citation check not run)
        if not self.site_results:
            if self.schema_name_match == 'match':    pts += 3
            if self.schema_address_match == 'match': pts += 3
            if self.schema_phone_match == 'match':   pts += 3
            # Pad to max with schema notes
            self.score = min(pts, 15)
            return self.score

        # Citation coverage: 80%+ of priority sites = 6 pts
        if self.total_sites > 0:
            pct = self.found_count / self.total_sites
            if pct >= 0.8:
                pts += 6
            elif pct >= 0.6:
                pts += 4
            elif pct >= 0.4:
                pts += 2

        # NAP consistency: 5 pts (deduct 1 per issue, min 0)
        nap_pts = max(0, 5 - self.nap_issue_count)
        pts += nap_pts

        # No duplicates: 2 pts
        if self.duplicate_count == 0:
            pts += 2

        # No critical sites missing: 2 pts
        if not self.critical_missing:
            pts += 2

        self.score = min(pts, 15)
        return self.score
```

- [ ] **Step 2: Update AuditResult to use CitationResult as the nap field**

In `scoring.py`, find the `AuditResult` dataclass and update the `nap` field type annotation:

```python
# Change:
#   nap: NAPResult
# To:
    nap: 'NAPResult | CitationResult' = field(default_factory=NAPResult)
```

And update `compute_total_score()` — it already calls `self.nap.compute_score()` so no change needed there.

- [ ] **Step 3: Add scoring tests**

```python
from scoring import CitationResult

def test_citation_score_full_coverage():
    r = CitationResult(
        total_sites=10, found_count=9,   # 90% = 6 pts
        nap_issue_count=0,               # 5 pts
        duplicate_count=0,               # 2 pts
        critical_missing=[],             # 2 pts
        site_results=['mock'],           # trigger citation path
    )
    r.compute_score()
    assert r.score == 15

def test_citation_score_partial_coverage():
    r = CitationResult(
        total_sites=10, found_count=6,   # 60% = 4 pts
        nap_issue_count=2,               # 3 pts
        duplicate_count=1,               # 0 pts
        critical_missing=['bing_places'], # 0 pts
        site_results=['mock'],
    )
    r.compute_score()
    assert r.score == 7

def test_citation_score_falls_back_to_schema_nap():
    r = CitationResult(
        schema_name_match='match',
        schema_address_match='match',
        schema_phone_match='match',
        site_results=[],  # no citation run
    )
    r.compute_score()
    assert r.score == 9  # 3+3+3
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_citations.py -v -k "score"
```

Expected: 3 score tests pass.

- [ ] **Step 5: Commit**

```bash
git add data_sources/modules/scoring.py tests/test_citations.py
git commit -m "feat: CitationResult scoring dataclass (replaces NAPResult in audit)"
```

---

## Task 8: Manual Pack Generator

Generates `clients/[abbr]/citations/manual-pack.html` — a self-contained, print-friendly HTML file with pre-filled NAP data and per-site submission instructions for Tier 4 (and any Tier 3 fallbacks).

**Files:**
- Create: `data_sources/modules/citation_manual_pack.py`

- [ ] **Step 1: Create citation_manual_pack.py**

```python
# data_sources/modules/citation_manual_pack.py
"""Generates a pre-filled manual citation submission pack (HTML)."""

from __future__ import annotations
from datetime import date
from pathlib import Path
from typing import Optional

from citation_sites import CitationSite, CitationCheckResult, CITATION_SITES


def generate_manual_pack(
    abbr: str,
    config: dict,
    site_results: list[CitationCheckResult],
    root: Path,
) -> Path:
    """
    Generate manual-pack.html for sites that need manual submission.
    Includes Tier 4 sites + any Tier 3 sites where submit_status == 'manual_required'.
    Returns the path to the generated file.
    """
    manual_sites = [
        r for r in site_results
        if r.site.tier == 4 or r.submit_status == 'manual_required'
    ]
    # Also include Tier 4 sites not yet checked
    checked_ids = {r.site.id for r in site_results}
    unchecked_tier4 = [
        CitationCheckResult(site=s)
        for s in CITATION_SITES
        if s.tier == 4 and s.id not in checked_ids
    ]
    all_manual = manual_sites + unchecked_tier4

    out_dir = root / 'clients' / abbr / 'citations'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'manual-pack.html'
    out_path.write_text(_render_pack(config, all_manual))
    return out_path


def _render_pack(config: dict, results: list[CitationCheckResult]) -> str:
    name = config.get('name', '')
    address = config.get('address', '')
    phone = config.get('phone', '')
    website = config.get('website', '')
    description = config.get('description', f'{name} — professional massage therapy in {config.get("city", "")}.')

    rows = '\n'.join(_render_site_row(r, config) for r in results)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Citation Manual Pack — {name}</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #222; }}
  h1 {{ font-size: 1.4rem; border-bottom: 2px solid #333; padding-bottom: 8px; }}
  h2 {{ font-size: 1.1rem; margin-top: 2rem; }}
  .nap-block {{ background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; padding: 16px; margin: 16px 0; font-family: monospace; white-space: pre-wrap; }}
  .site {{ border: 1px solid #ddd; border-radius: 6px; padding: 16px; margin: 16px 0; }}
  .site h3 {{ margin: 0 0 8px; }}
  .site a.btn {{ display: inline-block; background: #2563eb; color: #fff; text-decoration: none; padding: 8px 16px; border-radius: 4px; margin: 8px 0; }}
  .fields {{ background: #f9f9f9; padding: 12px; border-radius: 4px; font-size: 0.9rem; }}
  .fields dt {{ font-weight: bold; margin-top: 6px; }}
  .fields dd {{ margin: 0 0 4px 16px; font-family: monospace; }}
  input[type=checkbox] {{ margin-right: 6px; }}
  .done {{ opacity: 0.5; text-decoration: line-through; }}
  .generated {{ color: #666; font-size: 0.85rem; }}
</style>
</head>
<body>
<h1>Citation Manual Submission Pack — {name}</h1>
<p class="generated">Generated {date.today().isoformat()}</p>

<h2>Standard NAP Block (copy-paste)</h2>
<div class="nap-block">Business Name: {name}
Address: {address}
Phone: {phone}
Website: {website}

Short Description (50 words):
{description[:280]}

Categories: Massage, Thai Massage, Health & Beauty, Wellness</div>

<h2>Sites to Submit ({len(results)} total)</h2>
{rows}

<script>
document.querySelectorAll('input[type=checkbox]').forEach(cb => {{
  cb.addEventListener('change', () => {{
    cb.closest('.site').classList.toggle('done', cb.checked);
  }});
}});
</script>
</body>
</html>"""


def _render_site_row(result: CitationCheckResult, config: dict) -> str:
    site = result.site
    status_note = ''
    if result.status == 'not_found':
        status_note = '<span style="color:#dc2626">✗ Not listed</span>'
    elif result.status == 'manual_required':
        status_note = '<span style="color:#d97706">⚠ Automated submission failed</span>'
    else:
        status_note = '<span style="color:#6b7280">Not yet checked</span>'

    return f"""<div class="site">
  <h3><input type="checkbox"> {site.name} — {status_note}</h3>
  <a class="btn" href="{site.submission_url}" target="_blank">Open Submission Page</a>
  <div class="fields">
    <dl>
      <dt>Business Name</dt><dd>{config.get('name', '')}</dd>
      <dt>Address</dt><dd>{config.get('address', '')}</dd>
      <dt>Phone</dt><dd>{config.get('phone', '')}</dd>
      <dt>Website</dt><dd>{config.get('website', '')}</dd>
      <dt>Category</dt><dd>Massage Therapist / Health &amp; Beauty</dd>
    </dl>
  </div>
</div>"""
```

- [ ] **Step 2: Add tests**

```python
from citation_manual_pack import generate_manual_pack
from citation_sites import SITE_BY_ID, CitationCheckResult

def test_generate_manual_pack_creates_file(tmp_path):
    config = {
        'name': 'Glasgow Thai Massage',
        'address': '142 West Nile Street, Glasgow',
        'phone': '0141 552 1234',
        'website': 'https://glasgowthaimassage.co.uk',
        'city': 'Glasgow',
    }
    r = CitationCheckResult(site=SITE_BY_ID['apple_maps'], status='not_found')
    r.submit_status = None
    path = generate_manual_pack('gtm', config, [r], tmp_path)
    assert path.exists()
    html = path.read_text()
    assert 'Glasgow Thai Massage' in html
    assert 'Apple Business Connect' in html
    assert '0141 552 1234' in html

def test_manual_pack_includes_tier4_sites_not_in_results(tmp_path):
    config = {'name': 'Test', 'address': 'Test St', 'phone': '123', 'website': '', 'city': 'Glasgow'}
    path = generate_manual_pack('test', config, [], tmp_path)
    html = path.read_text()
    assert 'Apple Business Connect' in html
    assert 'Bing Places' in html
```

- [ ] **Step 3: Run tests**

```bash
python3 -m pytest tests/test_citations.py -v -k "manual_pack"
```

Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add data_sources/modules/citation_manual_pack.py tests/test_citations.py
git commit -m "feat: citation manual pack HTML generator"
```

---

## Task 9: Citation Submitter — Tier 3 Playwright Form Fill

Attempts automated form submission for Tier 3 sites using the `form_url_template` and `form_selectors` from each `CitationSite`. Falls back to `manual_required` on CAPTCHA or error.

**Files:**
- Create: `data_sources/modules/citation_submitter.py`

- [ ] **Step 1: Create citation_submitter.py**

```python
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
from typing import Optional

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

        # Heuristic: if CAPTCHA appears after submit, mark manual
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
```

- [ ] **Step 2: Add tests**

```python
from citation_submitter import submit_site

def test_submit_tier4_returns_manual_required():
    r = submit_site(SITE_BY_ID['apple_maps'], _GTM_CONFIG)
    assert r.submit_status == 'manual_required'

def test_submit_dry_run_skips_playwright():
    r = submit_site(SITE_BY_ID['yell'], _GTM_CONFIG, dry_run=True)
    assert r.submit_status == 'manual_required'
    assert 'dry-run' in r.error

def test_submit_no_form_selectors_returns_manual():
    # 192.com has empty form_selectors
    r = submit_site(SITE_BY_ID['192com'], _GTM_CONFIG)
    assert r.submit_status == 'manual_required'
```

- [ ] **Step 3: Run tests**

```bash
python3 -m pytest tests/test_citations.py -v -k "submit"
```

Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add data_sources/modules/citation_submitter.py tests/test_citations.py
git commit -m "feat: citation submitter (Playwright form fill + manual fallback)"
```

---

## Task 10: Citation Manager — Orchestrator

Ties everything together: `run_audit()`, `run_creation()`, `run_full()`.

**Files:**
- Create: `data_sources/modules/citation_manager.py`

- [ ] **Step 1: Create citation_manager.py**

```python
# data_sources/modules/citation_manager.py
"""
Citation Manager — orchestrates audit, creation, and full runs.

Usage:
    from citation_manager import CitationManager
    manager = CitationManager(abbr='gtm', config=config, root=ROOT)
    report = manager.run_full(dry_run=False)
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

from citation_sites import CITATION_SITES, CitationCheckResult, CitationSite
from citation_checker import check_site
from citation_submitter import submit_site
from citation_state import CitationState
from citation_manual_pack import generate_manual_pack
from scoring import CitationResult

logger = logging.getLogger(__name__)

_CRITICAL_SITE_IDS = {'google_business_profile', 'bing_places', 'yelp'}


class CitationManager:
    def __init__(self, abbr: str, config: dict, root: Path):
        self.abbr = abbr
        self.config = config
        self.root = root
        self.state = CitationState(abbr, root)

    def run_audit(self, force: bool = False, dry_run: bool = False) -> CitationResult:
        """Check all due sites and return scored CitationResult."""
        sites = self.state.get_due_sites(CITATION_SITES, force=force)
        results = []
        for site in sites:
            logger.info('Checking %s (%s)...', site.name, site.id)
            r = check_site(site, self.config, dry_run=dry_run)
            self.state.update(r)
            results.append(r)

        self.state.save()
        return self._build_scored_result(results)

    def run_creation(self, dry_run: bool = False) -> list[CitationCheckResult]:
        """Attempt creation for all not_found sites. Returns submission results."""
        not_found_ids = self.state.get_not_found()
        sites_to_submit = [s for s in CITATION_SITES if s.id in not_found_ids]

        submitted = []
        for site in sites_to_submit:
            logger.info('Submitting to %s...', site.name)
            r = submit_site(site, self.config, dry_run=dry_run)
            self.state.update(r)
            submitted.append(r)

        # Generate manual pack for anything that needs it
        all_results = self._all_results_from_state()
        pack_path = generate_manual_pack(self.abbr, self.config, all_results, self.root)
        logger.info('Manual pack saved to %s', pack_path)
        self.state.save()
        return submitted

    def run_full(self, force: bool = False, dry_run: bool = False) -> CitationResult:
        """Audit all sites, then attempt creation for missing ones."""
        scored = self.run_audit(force=force, dry_run=dry_run)
        self.run_creation(dry_run=dry_run)
        return scored

    def _build_scored_result(self, results: list[CitationCheckResult]) -> CitationResult:
        total = len([r for r in results if r.status != 'unknown'])
        found = len([r for r in results if r.status == 'found'])
        nap_issues = sum(len(r.issues) for r in results if r.status == 'found')
        duplicates = len([r for r in results if r.status == 'duplicate'])
        critical_missing = [
            r.site.id for r in results
            if r.site.id in _CRITICAL_SITE_IDS and r.status == 'not_found'
        ]
        cr = CitationResult(
            total_sites=total,
            found_count=found,
            nap_issue_count=nap_issues,
            duplicate_count=duplicates,
            critical_missing=critical_missing,
            site_results=results,
        )
        cr.compute_score()
        cr.findings = self._build_findings(results, cr)
        return cr

    def _build_findings(self, results: list[CitationCheckResult], cr: CitationResult) -> list[str]:
        findings = []
        if cr.critical_missing:
            for sid in cr.critical_missing:
                name = next((s.name for s in CITATION_SITES if s.id == sid), sid)
                findings.append(f'Critical citation missing: {name}')
        for r in results:
            if 'phone_mismatch' in r.issues:
                findings.append(f'{r.site.name}: phone mismatch — update to {self.config.get("phone", "")}')
            if 'address_mismatch' in r.issues:
                findings.append(f'{r.site.name}: address mismatch')
            if r.status == 'duplicate':
                findings.append(f'{r.site.name}: duplicate listing found — remove one')
        if cr.total_sites > 0 and cr.found_count / cr.total_sites < 0.6:
            findings.append(f'Low citation coverage: {cr.found_count}/{cr.total_sites} sites')
        return findings

    def _all_results_from_state(self) -> list[CitationCheckResult]:
        """Reconstruct CitationCheckResult list from state for pack generation."""
        from citation_sites import SITE_BY_ID
        results = []
        for entry in self.state.all_results_snapshot():
            sid = entry['id']
            if sid not in SITE_BY_ID:
                continue
            r = CitationCheckResult(
                site=SITE_BY_ID[sid],
                status=entry.get('status', 'unknown'),
                submit_status=entry.get('submit_status'),
                issues=entry.get('issues', []),
                listing_url=entry.get('listing_url', ''),
                found_phone=entry.get('found_phone', ''),
                found_address=entry.get('found_address', ''),
            )
            results.append(r)
        return results

    def print_status(self) -> None:
        """Print a status table to stdout."""
        ICONS = {'found': '✓', 'not_found': '✗', 'unknown': '·', 'duplicate': '⚠'}
        SUBMIT_ICONS = {'submitted': '→', 'pending_verification': '⌛', 'manual_required': '✎', 'failed': '✗'}
        print(f'\n  {"Site":<28} {"Status":<12} {"NAP":<8} {"Submission":<16} Issues')
        print('  ' + '─' * 75)
        for entry in self.state.all_results_snapshot():
            sid = entry['id']
            from citation_sites import SITE_BY_ID
            site = SITE_BY_ID.get(sid)
            if not site:
                continue
            status_icon = ICONS.get(entry.get('status', 'unknown'), '·')
            nap = '✓' if entry.get('nap_match') else ('✗' if entry.get('nap_match') is False else '—')
            sub = SUBMIT_ICONS.get(entry.get('submit_status', ''), '')
            issues = ', '.join(entry.get('issues', []))
            print(f'  {site.name:<28} {status_icon} {entry.get("status", "unknown"):<10} {nap:<8} {sub:<16} {issues}')
        print()
```

- [ ] **Step 2: Add integration test**

```python
from citation_manager import CitationManager

def test_run_audit_returns_citation_result(tmp_path):
    config = {
        'name': 'Glasgow Thai Massage',
        'address': '142 West Nile Street, Glasgow, G1 2RQ',
        'phone': '0141 552 1234',
        'city': 'Glasgow',
        'postcode': 'G1 2RQ',
        'website': 'https://glasgowthaimassage.co.uk',
    }
    manager = CitationManager('gtm', config, tmp_path)

    # Mock all site checks to return 'not_found'
    from citation_sites import CITATION_SITES
    mock_results = [CitationCheckResult(site=s, status='not_found') for s in CITATION_SITES]

    with patch('citation_manager.check_site', side_effect=mock_results):
        result = manager.run_audit(force=True, dry_run=True)

    from scoring import CitationResult
    assert isinstance(result, CitationResult)
    assert result.found_count == 0
    assert result.total_sites == len(CITATION_SITES)
```

- [ ] **Step 3: Run tests**

```bash
python3 -m pytest tests/test_citations.py -v -k "manager or audit_returns"
```

Expected: tests pass.

- [ ] **Step 4: Commit**

```bash
git add data_sources/modules/citation_manager.py tests/test_citations.py
git commit -m "feat: citation manager orchestrator (audit/create/full)"
```

---

## Task 11: CLI — run_citations.py

**Files:**
- Create: `src/citations/run_citations.py`
- Create: `src/citations/__init__.py` (empty)

- [ ] **Step 1: Create src/citations/__init__.py**

```bash
touch "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine/src/citations/__init__.py"
```

- [ ] **Step 2: Create run_citations.py**

```python
#!/usr/bin/env python3
"""
Citation Generator & Listing Audit

Usage:
    python3 src/citations/run_citations.py --abbr gtm
    python3 src/citations/run_citations.py --abbr gtm --mode audit
    python3 src/citations/run_citations.py --abbr gtm --mode create
    python3 src/citations/run_citations.py --abbr gtm --status
    python3 src/citations/run_citations.py --abbr gtm --dry-run
    python3 src/citations/run_citations.py --abbr gtm --force
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))

from citation_manager import CitationManager
from citation_state import CitationState

logging.basicConfig(level=logging.INFO, format='%(levelname)s  %(message)s')
logger = logging.getLogger(__name__)


def load_config(abbr: str) -> dict:
    config_path = ROOT / 'clients' / abbr / 'config.json'
    if not config_path.exists():
        print(f'Error: clients/{abbr}/config.json not found')
        sys.exit(1)
    return json.loads(config_path.read_text())


def main():
    parser = argparse.ArgumentParser(description='Citation audit and creation tool')
    parser.add_argument('--abbr', required=True, help='Client abbreviation (e.g. gtm)')
    parser.add_argument('--mode', choices=['audit', 'create', 'full'], default='full',
                        help='Run mode: audit (check only), create (submit missing), full (both)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Check and generate pack but do not submit to any sites')
    parser.add_argument('--force', action='store_true',
                        help='Re-check all sites regardless of last_checked date')
    parser.add_argument('--status', action='store_true',
                        help='Print citation status table and exit')
    args = parser.parse_args()

    config = load_config(args.abbr)
    manager = CitationManager(args.abbr, config, ROOT)

    if args.status:
        manager.print_status()
        return

    if args.mode == 'audit':
        result = manager.run_audit(force=args.force, dry_run=args.dry_run)
    elif args.mode == 'create':
        submitted = manager.run_creation(dry_run=args.dry_run)
        print(f'\n→ Submitted {len(submitted)} listings')
        manual = [r for r in submitted if r.submit_status == 'manual_required']
        if manual:
            print(f'  ✎ {len(manual)} require manual submission — see clients/{args.abbr}/citations/manual-pack.html')
        return
    else:  # full
        result = manager.run_full(force=args.force, dry_run=args.dry_run)

    # Print summary
    print(
        f'\n→ Citations: {result.found_count}/{result.total_sites} found'
        f' | {result.nap_issue_count} NAP issues'
        f' | {result.duplicate_count} duplicates'
        f' | score {result.score}/15'
    )
    if result.findings:
        for f in result.findings[:5]:
            print(f'  ✗ {f}')
        if len(result.findings) > 5:
            print(f'  … and {len(result.findings) - 5} more')

    if args.dry_run:
        print('\n[dry-run] No submissions made.')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Smoke test CLI**

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine"
python3 src/citations/run_citations.py --abbr gtm --mode audit --dry-run --force 2>&1 | tail -10
```

Expected: citation summary line printed, no crash.

- [ ] **Step 4: Commit**

```bash
git add src/citations/ tests/test_citations.py
git commit -m "feat: citation CLI (run_citations.py) with audit/create/full/status modes"
```

---

## Task 12: Audit Integration

Wire citations into the existing `/audit` pipeline. The `collect_nap()` function is expanded to also run the citation check when a client config is available, and the report gets a new citation section.

**Files:**
- Modify: `src/audit/collectors.py`
- Modify: `src/audit/run_audit.py`
- Modify: `src/audit/report.py`

- [ ] **Step 1: Add collect_citations() to collectors.py**

After the `collect_nap()` function, add:

```python
def collect_citations(config: dict, root: Path) -> 'CitationResult':
    """Run citation audit and return scored CitationResult.
    Falls back gracefully if citation modules unavailable."""
    try:
        sys.path.insert(0, str(root / 'data_sources' / 'modules'))
        from citation_manager import CitationManager
        from scoring import CitationResult
        manager = CitationManager(config.get('abbreviation', 'unknown'), config, root)
        return manager.run_audit(force=False, dry_run=False)
    except Exception as exc:
        logger.warning('Citation audit failed: %s', exc)
        from scoring import CitationResult
        r = CitationResult()
        r.findings.append(f'Citation audit unavailable: {exc}')
        r.compute_score()
        return r
```

Also update the import at the top of collectors.py:

```python
from scoring import (
    SchemaResult, ContentResult, GBPResult,
    ReviewResult, NAPResult, CitationResult, TechnicalResult, CompetitorResult,
)
```

- [ ] **Step 2: Update run_audit.py to call collect_citations()**

First, add `collect_citations` to the collectors import in `run_audit.py` (around line 48):

```python
# Change:
#   from collectors import collect_nap, collect_technical, collect_competitor,
# To:
from collectors import collect_nap, collect_citations, collect_technical, collect_competitor,
```

Then find where `collect_nap()` is called (around line 168). Replace the `nap = collect_nap(...)` call:

```python
# Replace:
#   nap = collect_nap(config, schema, site_url, wp_config=wp_config)
# With:
nap_schema = collect_nap(config, schema, site_url, wp_config=wp_config)

# Run citation audit if client abbreviation is available
if config.get('abbreviation'):
    nap = collect_citations(config, ROOT)
    # Carry schema NAP findings into CitationResult
    nap.schema_name_match = nap_schema.name_match
    nap.schema_address_match = nap_schema.address_match
    nap.schema_phone_match = nap_schema.phone_match
    nap.findings = nap_schema.findings + nap.findings
    nap.compute_score()
else:
    nap = nap_schema
```

Also update the console display in `run_audit.py` — change the label from `'NAP'` to `'NAP+Cit'`:

```python
# In the cats list:
('NAP+Cit', result.nap.score, 15),
```

- [ ] **Step 3: Add citation section to report.py**

In `src/audit/report.py`, find the NAP section in the markdown/HTML report templates and add citation details. Locate where NAP findings are rendered (search for `nap.findings` or `NAP`). After the NAP score line, add:

```python
def _citation_section_md(nap) -> str:
    """Generate citation detail block for markdown report."""
    from scoring import CitationResult
    if not isinstance(nap, CitationResult) or not nap.site_results:
        return ''
    lines = [
        f'\n### Citations ({nap.found_count}/{nap.total_sites} found, score {nap.score}/15)\n'
    ]
    for r in sorted(nap.site_results, key=lambda x: x.site.priority, reverse=True)[:15]:
        icon = {'found': '✓', 'not_found': '✗', 'unknown': '·', 'duplicate': '⚠'}.get(r.status, '·')
        nap_note = ' — NAP issues: ' + ', '.join(r.issues) if r.issues else ''
        lines.append(f'- {icon} **{r.site.name}** ({r.status}){nap_note}')
    return '\n'.join(lines)
```

Then call `_citation_section_md(result.nap)` in the report body where the NAP section appears.

- [ ] **Step 4: Add config abbreviation field check**

The `collect_citations()` call uses `config.get('abbreviation')`. Verify this field exists in `clients/gtm/config.json`:

```bash
grep '"abbreviation"' "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine/clients/gtm/config.json"
```

If not present, add it to the client configs. For GTM: `"abbreviation": "gtm"`. For SDY: `"abbreviation": "sdy"`. For GTB: `"abbreviation": "gtb"`. For TMG: `"abbreviation": "tmg"`. For TMB: `"abbreviation": "tmb"`.

- [ ] **Step 5: Run full citation test suite**

```bash
python3 -m pytest tests/test_citations.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Smoke test audit integration**

```bash
python3 src/audit/run_audit.py --abbr gtm --no-pdf --no-email 2>&1 | tail -20
```

Expected: audit runs, NAP+Cit line appears in console output, no import errors.

- [ ] **Step 7: Commit**

```bash
git add src/audit/collectors.py src/audit/run_audit.py src/audit/report.py clients/
git commit -m "feat: wire citation audit into /audit pipeline as NAP+Citations section"
```

---

## Verification

End-to-end test once all tasks are complete:

```bash
# 1. Run citation audit only (no submissions)
python3 src/citations/run_citations.py --abbr gtm --mode audit --dry-run --force

# 2. Check status table
python3 src/citations/run_citations.py --abbr gtm --status

# 3. Verify manual pack was generated
open "clients/gtm/citations/manual-pack.html"

# 4. Run full audit including citations
python3 src/audit/run_audit.py --abbr gtm --no-pdf --no-email

# Expected console output includes:
# ║  NAP+Cit   X/15  [██████████]
```

**Scheduling:** Add a monthly cron job for each active client. Edit `~/.seomachine-cron.sh` to support a `citations` argument, or add directly to crontab:

```bash
# Monthly citation audit — GTM (1st of month, 08:00)
0 8 1 * * cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 src/citations/run_citations.py --abbr gtm --mode audit >> logs/cron-citations-gtm.log 2>&1
```

**Selector tuning note:** After the initial implementation, the Tier 3 Playwright CSS selectors in `citation_sites.py` will need to be verified against live sites. Run `--mode audit --dry-run` first to exercise the scraping without submitting, then inspect results and adjust selectors per site as needed.
