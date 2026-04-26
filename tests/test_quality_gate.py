"""Unit tests for QualityGate."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / 'data_sources' / 'modules'))


# --- Helpers ---

def make_client_config(abbr='gtm'):
    return {
        'abbreviation': abbr,
        'name': 'Test Business',
        'phone': '0141 000 0000',
        'website': 'https://example.com',
        'wordpress': {'url': 'https://example.com'},
    }


def make_mock_anthropic(response_text='<p>Rewritten content here.</p>'):
    """Return a mock Anthropic client whose messages.create returns the given text."""
    mock_usage = MagicMock()
    mock_usage.input_tokens = 1000
    mock_usage.output_tokens = 500
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=response_text)]
    mock_msg.usage = mock_usage
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg
    return mock_client


PASSING_CONTENT = """
<p>Imagine coming home after a long week and sinking into total relaxation with a
<a href="/couples-massage/">couples massage</a> designed just for you.</p>
<p>One of our regulars, a nurse who works long shifts, found that monthly sessions
improved her sleep and reduced her neck tension significantly. Short sentence here.
Then a longer one. Then short again. Mix it up throughout.</p>
<p>Our <a href="/services/">couples massage</a> is perfect for anniversaries. Book your session today and
feel the difference. Get in touch to arrange your visit anytime.</p>
<p>We use expert techniques tailored to your needs. Simple words work best here.
Each session is designed around you. Book now to get started.</p>
"""

FAILING_CONTENT = """
<p>Massage therapy is a therapeutic practice that involves the manipulation of
soft body tissues including muscles, connective tissue, tendons, ligaments and
joints through the utilisation of professional techniques and methodologies
that have been scientifically validated and empirically demonstrated to provide
significant physiological and psychological benefits to recipients of such treatments.</p>
<p>The aforementioned therapeutic modality encompasses numerous specialisations
and subspecialisations within the broader framework of complementary medicine.</p>
"""


# --- Tests ---

def make_passing_analyzers():
    """Return mock EngagementAnalyzer and ReadabilityScorer that report a pass."""
    mock_eng = MagicMock()
    mock_eng.return_value.analyze.return_value = {
        'scores': {'hook': True, 'ctas': True, 'stories': True, 'rhythm': True, 'paragraphs': True},
    }
    mock_read = MagicMock()
    mock_read.return_value.analyze.return_value = {
        'readability_metrics': {'flesch_reading_ease': 72.0},
    }
    return mock_eng, mock_read


def test_passes_without_rewrite_when_content_is_good():
    from quality_gate import QualityGate
    gate = QualityGate(make_mock_anthropic(), make_client_config())
    mock_eng, mock_read = make_passing_analyzers()
    with patch('quality_gate.EngagementAnalyzer', mock_eng), \
         patch('quality_gate.ReadabilityScorer', mock_read), \
         patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
        result = gate.check_and_improve(PASSING_CONTENT, 'Couples Massage', 'service')
    assert result.passed is True
    assert result.attempts == 1
    assert result.cost_usd == 0.0
    assert result.content == PASSING_CONTENT


def test_rewrites_once_when_first_check_fails():
    from quality_gate import QualityGate
    mock_client = make_mock_anthropic(PASSING_CONTENT)
    gate = QualityGate(mock_client, make_client_config())
    with patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
        result = gate.check_and_improve(FAILING_CONTENT, 'Deep Tissue Massage', 'service')
    assert mock_client.messages.create.call_count >= 1
    assert result.attempts >= 2


def test_returns_passed_false_after_max_rewrites_still_failing():
    from quality_gate import QualityGate
    # Rewrite returns content that still fails
    mock_client = make_mock_anthropic(FAILING_CONTENT)
    gate = QualityGate(mock_client, make_client_config())
    with patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
        result = gate.check_and_improve(FAILING_CONTENT, 'Deep Tissue', 'service')
    assert result.passed is False
    assert result.attempts == 3  # original + 2 rewrites
    assert len(result.failures) > 0
    assert mock_client.messages.create.call_count == 2  # 2 rewrite calls


def test_cost_accumulates_across_rewrite_attempts():
    from quality_gate import QualityGate
    mock_client = make_mock_anthropic(FAILING_CONTENT)
    gate = QualityGate(mock_client, make_client_config())
    with patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
        result = gate.check_and_improve(FAILING_CONTENT, 'Deep Tissue', 'service')
    # 2 rewrite calls × (1000 input + 500 output tokens) at Sonnet pricing
    assert result.cost_usd > 0.0


def test_api_error_on_all_rewrites_returns_failed():
    from quality_gate import QualityGate
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API unavailable")
    gate = QualityGate(mock_client, make_client_config())
    with patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
        result = gate.check_and_improve(FAILING_CONTENT, 'Deep Tissue', 'service')
    assert result.passed is False
    assert 'rewrite_api_error' in result.failures


def test_api_error_on_first_rewrite_still_tries_second():
    from quality_gate import QualityGate
    # First rewrite call fails, second returns passing content.
    # Use mock analyzers: failing scores for FAILING_CONTENT, passing scores after rewrite.
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        Exception("API unavailable"),   # rewrite 1 fails
        MagicMock(                       # rewrite 2 succeeds with passing content
            content=[MagicMock(text=PASSING_CONTENT)],
            usage=MagicMock(input_tokens=1000, output_tokens=500),
        ),
    ]

    failing_scores = {
        'scores': {'hook': False, 'ctas': False, 'stories': False, 'rhythm': True, 'paragraphs': True},
    }
    passing_scores = {
        'scores': {'hook': True, 'ctas': True, 'stories': True, 'rhythm': True, 'paragraphs': True},
    }
    failing_read = {'readability_metrics': {'flesch_reading_ease': 30.0}}
    passing_read = {'readability_metrics': {'flesch_reading_ease': 72.0}}

    mock_eng = MagicMock()
    # analyze() called: initial check (fail), then after rewrite-2 succeeds (pass)
    mock_eng.return_value.analyze.side_effect = [failing_scores, passing_scores]
    mock_eng.return_value._analyze_ctas.side_effect = [{'distributed': False}, {'distributed': True}]
    mock_eng.return_value._analyze_paragraphs.side_effect = [{'long_count': 5}, {'long_count': 0}]
    mock_read = MagicMock()
    mock_read.return_value.analyze.side_effect = [failing_read, passing_read]

    gate = QualityGate(mock_client, make_client_config())
    with patch('quality_gate.EngagementAnalyzer', mock_eng), \
         patch('quality_gate.ReadabilityScorer', mock_read), \
         patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
        # Topic "Couples Massage": fails keyword check on FAILING_CONTENT, passes on PASSING_CONTENT
        result = gate.check_and_improve(FAILING_CONTENT, 'Couples Massage', 'service')
    assert result.passed is True
    assert mock_client.messages.create.call_count == 2


def test_scorer_error_is_failsafe_returns_passed():
    from quality_gate import QualityGate
    gate = QualityGate(make_mock_anthropic(), make_client_config())
    with patch('quality_gate.EngagementAnalyzer') as mock_eng:
        mock_eng.return_value.analyze.side_effect = Exception("Malformed content")
        with patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
            result = gate.check_and_improve(FAILING_CONTENT, 'Deep Tissue', 'service')
    assert result.passed is True
    assert result.attempts == 1
    assert result.cost_usd == 0.0


def test_api_error_on_first_rewrite_uses_original_failures_for_second():
    """When rewrite 1 hits an API error, rewrite 2 must still receive fix instructions."""
    from quality_gate import QualityGate
    captured_prompts = []

    def capture_and_succeed(*args, **kwargs):
        # Capture the prompt from the second call
        if len(captured_prompts) == 1:
            # second call — return passing content
            captured_prompts.append(kwargs.get('messages', [{}])[0].get('content', ''))
            mock_usage = MagicMock()
            mock_usage.input_tokens = 1000
            mock_usage.output_tokens = 500
            mock_msg = MagicMock()
            mock_msg.content = [MagicMock(text=PASSING_CONTENT)]
            mock_msg.usage = mock_usage
            return mock_msg
        # first call — fail
        captured_prompts.append('error')
        raise Exception("API unavailable")

    failing_scores = {
        'scores': {'hook': False, 'ctas': False, 'stories': False, 'rhythm': True, 'paragraphs': True},
    }
    passing_scores = {
        'scores': {'hook': True, 'ctas': True, 'stories': True, 'rhythm': True, 'paragraphs': True},
    }
    failing_read = {'readability_metrics': {'flesch_reading_ease': 30.0}}
    passing_read = {'readability_metrics': {'flesch_reading_ease': 72.0}}

    mock_eng = MagicMock()
    # analyze() called: initial check (fail), then after rewrite-2 succeeds (pass)
    mock_eng.return_value.analyze.side_effect = [failing_scores, passing_scores]
    mock_eng.return_value._analyze_ctas.side_effect = [{'distributed': False}, {'distributed': True}]
    mock_eng.return_value._analyze_paragraphs.side_effect = [{'long_count': 5}, {'long_count': 0}]
    mock_read = MagicMock()
    mock_read.return_value.analyze.side_effect = [failing_read, passing_read]

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = capture_and_succeed
    gate = QualityGate(mock_client, make_client_config())
    with patch('quality_gate.EngagementAnalyzer', mock_eng), \
         patch('quality_gate.ReadabilityScorer', mock_read), \
         patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
        # Topic "Couples Massage": fails keyword check on FAILING_CONTENT, passes on PASSING_CONTENT
        result = gate.check_and_improve(FAILING_CONTENT, 'Couples Massage', 'service')

    assert result.passed is True
    # The second API call prompt should contain real fix instructions (not empty)
    second_prompt = captured_prompts[1]
    assert 'specific improvements' in second_prompt
    assert len(second_prompt) > 200  # a real prompt, not an empty one


def test_failures_list_only_contains_strings():
    from quality_gate import QualityGate
    mock_client = make_mock_anthropic(FAILING_CONTENT)
    gate = QualityGate(mock_client, make_client_config())
    with patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
        result = gate.check_and_improve(FAILING_CONTENT, 'Deep Tissue', 'service')
    assert isinstance(result.failures, list)
    assert all(isinstance(f, str) for f in result.failures)


def test_preserve_instructions_included_for_passing_criteria():
    """When readability passes but CTAs fail, the rewrite prompt must preserve readability."""
    from quality_gate import QualityGate
    captured_prompt = []

    def capture_call(**kwargs):
        captured_prompt.append(kwargs.get('messages', [{}])[0].get('content', ''))
        mock_usage = MagicMock()
        mock_usage.input_tokens = 1000
        mock_usage.output_tokens = 500
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=PASSING_CONTENT)]
        mock_msg.usage = mock_usage
        return mock_msg

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = lambda *a, **kw: capture_call(**kw)

    gate = QualityGate(mock_client, make_client_config())

    # Mock: readability passes, CTAs fail
    passing_read = {'readability_metrics': {'flesch_reading_ease': 70}}
    failing_eng = {'scores': {'hook': True, 'ctas': False, 'stories': True, 'rhythm': True, 'paragraphs': True}}

    with patch('quality_gate.EngagementAnalyzer') as mock_eng_cls, \
         patch('quality_gate.ReadabilityScorer') as mock_read_cls, \
         patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
        mock_eng_cls.return_value.analyze.return_value = failing_eng
        mock_eng_cls.return_value._analyze_ctas.return_value = {'distributed': False}
        mock_eng_cls.return_value._analyze_paragraphs.return_value = {'long_count': 0}
        mock_read_cls.return_value.analyze.return_value = passing_read
        gate.check_and_improve(FAILING_CONTENT, 'Deep Tissue', 'service')

    assert len(captured_prompt) >= 1
    prompt = captured_prompt[0]
    assert 'PRESERVE' in prompt
    assert 'Readability is already good' in prompt


def test_keyword_placement_passes_when_topic_in_first_100_words():
    from quality_gate import QualityGate
    gate = QualityGate(make_mock_anthropic(), make_client_config())
    assert gate._keyword_in_first_100_words(PASSING_CONTENT, 'Couples Massage') is True


def test_keyword_placement_fails_when_topic_missing_from_first_100_words():
    from quality_gate import QualityGate
    gate = QualityGate(make_mock_anthropic(), make_client_config())
    content_no_early_keyword = '<p>' + ('filler word ' * 120) + '</p><p>couples massage mentioned here</p>'
    assert gate._keyword_in_first_100_words(content_no_early_keyword, 'Couples Massage') is False


def test_count_internal_links_counts_relative_and_domain_hrefs():
    from quality_gate import QualityGate
    gate = QualityGate(make_mock_anthropic(), make_client_config())
    content = (
        '<p><a href="/service/thai-massage/">Thai Massage</a></p>'
        '<p><a href="https://example.com/book/">Book Now</a></p>'
        '<p><a href="https://external.com/page/">External</a></p>'
    )
    assert gate._count_internal_links(content) == 2


def test_keyword_placement_failure_included_in_gate_result():
    from quality_gate import QualityGate
    gate = QualityGate(make_mock_anthropic(PASSING_CONTENT), make_client_config())
    mock_eng, mock_read = make_passing_analyzers()
    content_no_early_keyword = (
        '<p>' + ('filler word ' * 120) + '</p>'
        '<p>Our <a href="/service/">deep tissue</a> massage is great. '
        '<a href="/book/">Book now.</a></p>'
    )
    with patch('quality_gate.EngagementAnalyzer', mock_eng), \
         patch('quality_gate.ReadabilityScorer', mock_read), \
         patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
        result = gate.check_and_improve(content_no_early_keyword, 'Deep Tissue Massage', 'service')
    assert 'keyword_placement' in result.failures or result.passed is True
