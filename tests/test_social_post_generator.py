"""Unit tests for social post generator."""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src' / 'social'))


SAMPLE_HTML = """<!-- SECTION 1 -->
<h2>Thai Massage Benefits: Why This Ancient Practice Works</h2>
<p>Thai massage has been practised for over 2,500 years.</p>
<h3>Improved Flexibility</h3>
<p>Regular sessions can increase range of motion by up to 15%.</p>
<h3>Stress Relief</h3>
<p>Studies show cortisol levels drop significantly after a session.</p>

<!-- SECTION 2 FAQ -->
<h2>Frequently Asked Questions</h2>
<details><summary>Does Thai massage hurt?</summary>
<p>You may feel deep pressure, but it should never be painful.</p></details>
<details><summary>How often should I get Thai massage?</summary>
<p>Once a week for therapeutic benefits, or monthly for maintenance.</p></details>

<!-- SCHEMA -->
<script type="application/ld+json">{"@type": "BlogPosting"}</script>"""

SAMPLE_METADATA = {
    'title': 'Thai Massage Benefits: Why This Ancient Practice Works',
    'post_url': 'https://glasgowthaimassage.co.uk/blog/thai-massage-benefits/',
    'booking_url': 'https://glasgowthaimassage.co.uk/booking/',
    'business_name': 'Glasgow Thai Massage',
    'abbreviation': 'GTM',
    'content_type': 'blog',
}


def _make_mock_response(content_json: dict):
    """Build a mock Claude API response."""
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(type='text', text=json.dumps(content_json))]
    mock_msg.usage.input_tokens = 5000
    mock_msg.usage.output_tokens = 3000
    return mock_msg


def test_generate_returns_video_script_and_social_posts():
    """generate() returns structured video script and social posts."""
    from social_post_generator import SocialPostGenerator

    expected_output = {
        'video_script': {
            'title': 'Thai Massage Benefits',
            'description': 'Learn why Thai massage works',
            'tags': ['thai massage'],
            'thumbnail_text': 'Thai Massage Benefits',
            'scenes': [
                {
                    'scene_number': 1,
                    'narration': 'Thai massage has been practised for 2500 years.',
                    'visual_type': 'ken_burns',
                    'visual_description': 'Spa treatment scene',
                    'duration_hint': '15s',
                    'source_image': 'banner.jpg',
                    'text_overlay': None,
                }
            ],
            'shorts': [
                {
                    'short_number': 1,
                    'type': 'surprising_fact',
                    'hook': 'Did you know Thai massage is 2500 years old?',
                    'narration': 'Thai massage dates back 2500 years.',
                    'visual_type': 'text_overlay',
                    'text_overlays': ['2,500 Years', 'Of Healing'],
                    'duration_target': '30s',
                    'source_scenes': [1],
                }
            ],
        },
        'social_posts': {
            'linkedin': {'text': 'Professional post about Thai massage.', 'hashtags': ['#ThaiMassage']},
            'facebook': {'text': 'Check out Thai massage benefits!', 'hashtags': ['#ThaiMassage']},
            'x_thread': [{'text': 'Thai massage thread tweet 1', 'media': 'banner'}],
            'x_standalone': [{'text': 'Thai massage tweet 1', 'day_offset': 0}],
            'instagram': {'caption': 'Thai massage caption', 'hashtags': ['#ThaiMassage'], 'media': 'banner'},
            'gbp': {'text': 'Local Thai massage post', 'cta_type': 'BOOK', 'cta_url': 'https://example.com/booking/', 'media': 'banner'},
        },
    }

    with patch('social_post_generator.anthropic') as mock_anthropic:
        mock_client = mock_anthropic.Anthropic.return_value
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        mock_stream_ctx.get_final_message.return_value = _make_mock_response(expected_output)
        mock_client.messages.stream.return_value = mock_stream_ctx

        gen = SocialPostGenerator()
        result, cost = gen.generate(SAMPLE_HTML, SAMPLE_METADATA)

        assert 'video_script' in result
        assert 'social_posts' in result
        assert len(result['video_script']['scenes']) >= 1
        assert len(result['video_script']['shorts']) >= 1
        assert 'linkedin' in result['social_posts']
        assert 'x_thread' in result['social_posts']
        assert 'x_standalone' in result['social_posts']
        assert 'gbp' in result['social_posts']
        assert cost > 0


def test_extract_content_from_html():
    """extract_content() parses HTML into structured text."""
    from social_post_generator import extract_content_from_html

    result = extract_content_from_html(SAMPLE_HTML)

    assert result['title'] == 'Thai Massage Benefits: Why This Ancient Practice Works'
    assert 'practised for over 2,500 years' in result['body_text']
    assert len(result['faq_questions']) == 2
    assert result['faq_questions'][0]['question'] == 'Does Thai massage hurt?'
    assert 'headings' in result
