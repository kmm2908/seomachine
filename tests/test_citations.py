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

from citation_state import CitationState

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
