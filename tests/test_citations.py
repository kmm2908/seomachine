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
