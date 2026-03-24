"""Smoke test: ai_visibility block is injected into blog/topical prompts only."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src' / 'content'))

from geo_batch_runner import build_system_prompt

CONFIG_WITH_AI_VIS = {
    "name": "Test Business",
    "ai_visibility": {
        "canonical_description": "Test Business is a test studio offering test services.",
        "brand_associations": ["test keyword one", "test keyword two"],
        "positioning_note": "Emphasise testing. Avoid production."
    }
}

CONFIG_WITHOUT_AI_VIS = {
    "name": "Test Business"
}


def test_ai_visibility_injected_for_blog():
    prompt = build_system_prompt('gtm', 'blog', CONFIG_WITH_AI_VIS)
    assert '## AI Brand Positioning' in prompt
    assert 'Test Business is a test studio' in prompt
    assert 'test keyword one, test keyword two' in prompt
    assert 'Emphasise testing' in prompt


def test_ai_visibility_injected_for_topical():
    prompt = build_system_prompt('gtm', 'topical', CONFIG_WITH_AI_VIS)
    assert '## AI Brand Positioning' in prompt


def test_ai_visibility_not_injected_for_location():
    prompt = build_system_prompt('gtm', 'location', CONFIG_WITH_AI_VIS)
    assert '## AI Brand Positioning' not in prompt


def test_ai_visibility_not_injected_for_service():
    prompt = build_system_prompt('gtm', 'service', CONFIG_WITH_AI_VIS)
    assert '## AI Brand Positioning' not in prompt


def test_ai_visibility_missing_block_no_error():
    # No ai_visibility key — must not crash, must not inject section
    prompt = build_system_prompt('gtm', 'blog', CONFIG_WITHOUT_AI_VIS)
    assert '## AI Brand Positioning' not in prompt


def test_ai_visibility_partial_fields():
    # Only canonical_description present — should inject without error
    config = {"name": "Test", "ai_visibility": {"canonical_description": "Just a description."}}
    prompt = build_system_prompt('gtm', 'blog', config)
    assert '## AI Brand Positioning' in prompt
    assert 'Just a description.' in prompt


def test_ai_visibility_not_injected_for_pillar():
    prompt = build_system_prompt('gtm', 'pillar', CONFIG_WITH_AI_VIS)
    assert '## AI Brand Positioning' not in prompt


def test_ai_visibility_not_injected_for_comp_alt():
    prompt = build_system_prompt('gtm', 'comp-alt', CONFIG_WITH_AI_VIS)
    assert '## AI Brand Positioning' not in prompt


def test_ai_visibility_empty_dict_no_injection():
    # Empty ai_visibility dict — must not inject bare heading
    config = {"name": "Test", "ai_visibility": {}}
    prompt = build_system_prompt('gtm', 'blog', config)
    assert '## AI Brand Positioning' not in prompt


if __name__ == '__main__':
    test_ai_visibility_injected_for_blog()
    test_ai_visibility_injected_for_topical()
    test_ai_visibility_not_injected_for_location()
    test_ai_visibility_not_injected_for_service()
    test_ai_visibility_missing_block_no_error()
    test_ai_visibility_partial_fields()
    test_ai_visibility_not_injected_for_pillar()
    test_ai_visibility_not_injected_for_comp_alt()
    test_ai_visibility_empty_dict_no_injection()
    print("All tests passed.")
