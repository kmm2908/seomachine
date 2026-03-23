"""Tests for EngagementAnalyzer mini-stories criterion (massage therapy patterns)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'data_sources' / 'modules'))

from engagement_analyzer import EngagementAnalyzer


def make_analyzer():
    return EngagementAnalyzer()


# --- Mini-stories pattern tests ---

def test_mini_stories_detects_unnamed_client_scenario():
    content = "One of our clients came in after months of back pain and felt genuine relief after just one session."
    result = make_analyzer()._analyze_mini_stories(content)
    assert result['count'] >= 1


def test_mini_stories_detects_couple_scenario():
    content = "Couples celebrating anniversaries often tell us it was the most relaxing experience they have had together."
    result = make_analyzer()._analyze_mini_stories(content)
    assert result['count'] >= 1


def test_mini_stories_detects_imagine_pattern():
    content = "Imagine arriving after a long week and feeling all that tension simply melt away."
    result = make_analyzer()._analyze_mini_stories(content)
    assert result['count'] >= 1


def test_mini_stories_rejects_generic_text_without_outcome():
    content = "Massage therapy is a treatment that helps many people. We offer a range of services."
    result = make_analyzer()._analyze_mini_stories(content)
    assert result['count'] == 0


def test_mini_stories_retains_name_pattern():
    content = "Sarah's back pain had been building for months. She discovered that regular massage improved her sleep dramatically."
    result = make_analyzer()._analyze_mini_stories(content)
    assert result['count'] >= 1


# --- 5-criterion analyze() tests ---

def test_analyze_returns_five_criteria():
    content = """
    Imagine coming in after a stressful week and feeling completely restored.
    One of our regulars, a nurse who works long shifts, finds that monthly massage
    keeps her going. We offer a range of treatments. Book today and feel the difference.
    Book a session now — get in touch to arrange your visit.
    Short sentence. Another short one. A longer sentence here with a few more words.
    Short. Long sentence with quite a few words in it. Short again.
    """
    result = make_analyzer().analyze(content)
    assert result['total_criteria'] == 5
    assert 'stories' in result['scores']
    assert 'passed_count' in result
    assert result['passed_count'] <= 5


def test_analyze_passed_count_consistent_with_scores():
    content = "Massage is a treatment. We provide services."
    result = make_analyzer().analyze(content)
    assert result['passed_count'] == sum(result['scores'].values())
    assert result['all_passed'] == (result['passed_count'] == 5)
