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
                           'Central Chambers, 93 Hope Street') == 'match'

def test_compare_name_case_insensitive():
    assert compare_name('Glasgow Thai Massage', 'glasgow thai massage') == 'match'

def test_compare_name_mismatch():
    assert compare_name('Glasgow Thai Massage', 'Thai House Glasgow') == 'mismatch'

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

def test_all_sites_have_required_fields():
    for site in CITATION_SITES:
        assert site.id, f"Site missing id: {site}"
        assert site.name, f"Site {site.id} missing name"
        assert site.tier in (1, 2, 3, 4), f"Site {site.id} invalid tier"
        assert 1 <= site.priority <= 10, f"Site {site.id} invalid priority"
