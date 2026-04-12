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

from unittest.mock import patch, MagicMock
from citation_checker import _check_yelp, _check_foursquare, _match_api_results, check_site, _is_captcha_html, _check_dataforseo

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

def test_dataforseo_found():
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
    with patch('dataforseo.DataForSEO', return_value=mock_client):
        r = _check_dataforseo(SITE_BY_ID['trustpilot'], _GTM_CONFIG)
    assert r.status == 'found'
    assert r.nap_match is True

def test_dataforseo_not_found():
    mock_client = MagicMock()
    mock_client._post.return_value = {
        'tasks': [{'status_code': 20000, 'result': [{'items': []}]}]
    }
    with patch('dataforseo.DataForSEO', return_value=mock_client):
        r = _check_dataforseo(SITE_BY_ID['trustpilot'], _GTM_CONFIG)
    assert r.status == 'not_found'

def test_check_site_routes_tier4_to_unknown():
    r = check_site(SITE_BY_ID['apple_maps'], _GTM_CONFIG)
    assert r.status == 'unknown'
    assert 'Tier 4' in r.error

def test_is_captcha_html_detects_cloudflare():
    assert _is_captcha_html('<html><body class="cf-challenge">prove you are human</body></html>') is True
    assert _is_captcha_html('<html><body><h1>Results for Glasgow</h1></body></html>') is False
