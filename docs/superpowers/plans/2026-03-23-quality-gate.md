# Quality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a blocking quality gate to the batch content pipeline that auto-rewrites failing articles (max 2 attempts) before publishing, and flags persistent failures for human review in the Google Sheet.

**Architecture:** A new `QualityGate` class encapsulates the check-rewrite loop. It runs `EngagementAnalyzer` and `ReadabilityScorer`, builds targeted fix instructions from failures, calls Claude API to rewrite, and retries up to 2 times. The batch runner calls it as a single unit and handles the result before writing DONE status or publishing.

**Tech Stack:** Python 3.11+, `anthropic` SDK (already used in batch runner), `textstat` (already used by `ReadabilityScorer`), `dataclasses` (stdlib)

**Spec:** `docs/superpowers/specs/2026-03-23-quality-gate-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `data_sources/modules/engagement_analyzer.py` | Modify | Re-enable mini-stories as 5th criterion; update patterns and outcome verbs for massage therapy; update all 4→5 references |
| `data_sources/modules/quality_gate.py` | **Create** | `QualityResult` dataclass + `QualityGate` class — check/rewrite loop, targeted prompt builder, HTML stripping |
| `data_sources/modules/google_sheets.py` | Modify | Add `REVIEW_REQUIRED_VALUE` constant |
| `src/geo_batch_runner.py` | Modify | Import gate + constant; replace `run_quality_check()` on normal write path; defer DONE/cost writes; remove old function |
| `tests/test_quality_gate.py` | **Create** | Unit tests for QualityGate: pass-through, rewrite on fail, max retries, API error handling, scorer error fail-safe |

---

## Task 1: Update `engagement_analyzer.py` — re-enable mini-stories as 5th criterion

**Files:**
- Modify: `data_sources/modules/engagement_analyzer.py`
- Test: `tests/test_engagement_analyzer.py` (create)

### Step 1.1: Write failing tests for updated mini-stories detection

- [ ] Create `tests/test_engagement_analyzer.py`:

```python
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
```

- [ ] Run tests to confirm they fail:

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_engagement_analyzer.py -v 2>&1 | head -40
```

Expected: failures on `test_mini_stories_detects_*` and `test_analyze_returns_five_criteria`

### Step 1.2: Update `_analyze_mini_stories()` patterns and outcome verbs

- [ ] In `data_sources/modules/engagement_analyzer.py`, replace the `NAME_PATTERNS` list and update `_analyze_mini_stories()`:

Replace the existing `NAME_PATTERNS` class attribute (lines ~54-59) with:

```python
# Client scenario patterns (massage therapy — named and unnamed)
STORY_PATTERNS = [
    r'\bOne of our (?:clients|regulars|customers|guests)\b',
    r'\b(?:A|One) (?:client|couple|guest|customer|visitor|person)\b',
    r'\b(?:Many|Some|Most) of our (?:clients|regulars|guests)\b',
    r'\b(?:Couples|People|Clients) (?:celebrating|coming|looking|dealing|suffering)\b',
    r'\b(?:imagine|picture) (?:coming|arriving|booking|feeling)\b',
    # Retain named patterns as secondary detection
    r'\b(?:Sarah|Mike|Marcus|Lisa|John|David|Emily|Chris|Alex|Tom|Anna|James|Maria|Rachel|Dan|Kate)\b',
    r'\b(?:The team at|At) [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b',
    r"\b[A-Z][a-z]+'s (?:massage|treatment|session|appointment|back|neck|shoulders)\b",
]

# Outcome verbs for massage therapy domain
STORY_OUTCOME_VERBS = r'felt|relieved|noticed|returned|booked|recommended|improved|relaxed|found|discovered|said|told us|shared'
```

- [ ] Update `_analyze_mini_stories()` to use the new patterns and outcome verbs:

```python
def _analyze_mini_stories(self, content: str) -> Dict[str, Any]:
    """Analyze presence of client scenarios/mini-stories."""
    stories_found = []

    for pattern in self.STORY_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 100)
            context = content[start:end]
            if re.search(self.STORY_OUTCOME_VERBS, context, re.IGNORECASE):
                stories_found.append({
                    'match': match.group(),
                    'context': context[:80].strip()
                })

    # Deduplicate by match text
    seen = set()
    unique_stories = []
    for story in stories_found:
        if story['match'] not in seen:
            seen.add(story['match'])
            unique_stories.append(story)

    return {
        'count': len(unique_stories),
        'stories': unique_stories[:3]
    }
```

### Step 1.3: Re-enable mini-stories in `analyze()` and update all 4→5 references

- [ ] In `analyze()` (around line 62), make these changes:

1. Change the comment from `"Analyze article for 4 engagement criteria (stories removed)"` to `"Analyze article for 5 engagement criteria"`

2. Add `'stories'` to the `results` dict:
```python
results = {
    'filename': filename,
    'hook': self._analyze_hook(content),
    'rhythm': self._analyze_rhythm(content),
    'ctas': self._analyze_ctas(content),
    'paragraphs': self._analyze_paragraphs(content),
    'stories': self._analyze_mini_stories(content),
}
```

3. Add `'stories'` to `results['scores']`:
```python
results['scores'] = {
    'hook': results['hook']['is_good'],
    'rhythm': results['rhythm']['score'] >= 45,
    'ctas': results['ctas']['distributed'],
    'paragraphs': results['paragraphs']['long_count'] <= 3,
    'stories': results['stories']['count'] >= 1,
}
```

4. Change `total_criteria` from `4` to `5`:
```python
results['total_criteria'] = 5
```

5. Update `all_passed` check:
```python
results['all_passed'] = results['passed_count'] == 5
```

- [ ] Update `format_results()` table header — add `Stories` column between `Hook` and `Rhythm`:

```python
lines.append(f"{'Article':<45} {'Hook':^8} {'Stories':^8} {'Rhythm':^8} {'CTAs':^8} {'Paras':^8} {'Score':^8}")
lines.append("-" * 97)
```

And the data row:
```python
stories = "✓" if r['scores']['stories'] else "✗"
score = f"{r['passed_count']}/5"
lines.append(f"{name:<45} {hook:^8} {stories:^8} {rhythm:^8} {ctas:^8} {paras:^8} {score:^8}")
```

Also update `totals` dict to include `'stories': 0` and the TOTALS row.

- [ ] Update the `TOTALS PASSING` line in `format_results()` to include stories column.

### Step 1.4: Run tests to confirm they pass

- [ ] Run:

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_engagement_analyzer.py -v
```

Expected: all tests PASS

### Step 1.5: Commit

- [ ] Commit:

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && git add data_sources/modules/engagement_analyzer.py tests/test_engagement_analyzer.py && git commit -m "feat: re-enable mini-stories as 5th engagement criterion with massage therapy patterns"
```

---

## Task 2: Add `REVIEW_REQUIRED_VALUE` to `google_sheets.py`

**Files:**
- Modify: `data_sources/modules/google_sheets.py:43`

### Step 2.1: Add the constant

- [ ] In `data_sources/modules/google_sheets.py`, after line 43 (`IMAGES_PENDING_VALUE = 'Images o/s'`), add:

```python
REVIEW_REQUIRED_VALUE = 'Review Required'
```

### Step 2.2: Verify `read_pending()` already skips this status

- [ ] Read `read_pending()` in `google_sheets.py` and confirm it only picks up `QUEUE_VALUE` (`Write Now`) and `IMAGES_PENDING_VALUE` (`Images o/s`) rows. `Review Required` rows will be skipped automatically — no code change needed.

### Step 2.3: Commit

- [ ] Commit:

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && git add data_sources/modules/google_sheets.py && git commit -m "feat: add REVIEW_REQUIRED_VALUE constant to google_sheets"
```

---

## Task 3: Create `quality_gate.py`

**Files:**
- Create: `data_sources/modules/quality_gate.py`
- Test: `tests/test_quality_gate.py` (create)

### Step 3.1: Write failing tests for QualityGate

- [ ] Create `tests/test_quality_gate.py`:

```python
"""Unit tests for QualityGate."""
import sys
from dataclasses import dataclass
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
<p>Imagine coming home after a long week and sinking into total relaxation.</p>
<p>One of our regulars, a nurse who works long shifts, found that monthly sessions
improved her sleep and reduced her neck tension significantly. Short sentence here.
Then a longer one. Then short again. Mix it up throughout.</p>
<p>Our couples massage is perfect for anniversaries. Book your session today and
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

def test_passes_without_rewrite_when_content_is_good():
    from quality_gate import QualityGate
    gate = QualityGate(make_mock_anthropic(), make_client_config())
    with patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
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
    # First rewrite call fails, second returns passing content
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        Exception("API unavailable"),   # rewrite 1 fails
        MagicMock(                       # rewrite 2 succeeds with passing content
            content=[MagicMock(text=PASSING_CONTENT)],
            usage=MagicMock(input_tokens=1000, output_tokens=500),
        ),
    ]
    gate = QualityGate(mock_client, make_client_config())
    with patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
        result = gate.check_and_improve(FAILING_CONTENT, 'Deep Tissue', 'service')
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


def test_failures_list_only_contains_current_attempt_failures():
    from quality_gate import QualityGate
    mock_client = make_mock_anthropic(FAILING_CONTENT)
    gate = QualityGate(mock_client, make_client_config())
    with patch('quality_gate.Path.read_text', return_value='# Brand Voice\nBe warm.'):
        result = gate.check_and_improve(FAILING_CONTENT, 'Deep Tissue', 'service')
    # failures should be a list of strings
    assert isinstance(result.failures, list)
    assert all(isinstance(f, str) for f in result.failures)
```

- [ ] Run tests to confirm they fail with `ModuleNotFoundError`:

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_quality_gate.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'quality_gate'`

### Step 3.2: Create `data_sources/modules/quality_gate.py`

- [ ] Create the file:

```python
"""
Quality Gate

Checks generated content against readability and engagement thresholds.
Rewrites with targeted instructions if it fails, up to MAX_REWRITES times.
Returns QualityResult with final content, pass/fail status, and costs.
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Project root is two levels up from data_sources/modules/
_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(Path(__file__).parent))

from engagement_analyzer import EngagementAnalyzer
from readability_scorer import ReadabilityScorer

# Sonnet 4.6 pricing
_INPUT_COST_PER_M = 3.00
_OUTPUT_COST_PER_M = 15.00

MAX_REWRITES = 2
FLESCH_THRESHOLD = 60        # Flesch Reading Ease ≥ 60
ENGAGEMENT_OPTIONAL_MIN = 2  # Must pass ≥2 of 3 optional criteria


@dataclass
class QualityResult:
    content: str
    passed: bool
    attempts: int
    failures: list = field(default_factory=list)
    cost_usd: float = 0.0


class QualityGate:
    """Check content quality and rewrite with targeted instructions if needed."""

    def __init__(self, anthropic_client, client_config: dict):
        self._client = anthropic_client
        self._config = client_config

    def check_and_improve(self, content: str, topic: str, content_type: str) -> QualityResult:
        """
        Check content and rewrite if needed. Returns QualityResult.

        Attempts:
          1 — original content
          2 — first rewrite (if attempt 1 fails)
          3 — second rewrite (if attempt 2 fails)
        """
        plain = self._to_plain(content)
        current_content = content
        total_cost = 0.0

        try:
            eng = EngagementAnalyzer().analyze(plain)
            read = ReadabilityScorer().analyze(plain)
        except Exception as e:
            print(f"    → Quality check error (skipped): {e}")
            return QualityResult(content=content, passed=True, attempts=1, cost_usd=0.0)

        failures = self._evaluate(eng, read)
        self._print_quality_line(eng, read, failures, attempt=1, rewriting=bool(failures))

        if not failures:
            return QualityResult(content=content, passed=True, attempts=1, cost_usd=0.0)

        # Rewrite loop
        for rewrite_num in range(1, MAX_REWRITES + 1):
            rewrite_content, rewrite_cost = self._rewrite(
                current_content, topic, content_type, failures, rewrite_num
            )
            total_cost += rewrite_cost

            if rewrite_content is None:
                # API error — treat as failed attempt, continue if retries remain
                failures = ['rewrite_api_error']
                if rewrite_num < MAX_REWRITES:
                    continue
                return QualityResult(
                    content=current_content,
                    passed=False,
                    attempts=1 + rewrite_num,
                    failures=['rewrite_api_error'],
                    cost_usd=total_cost,
                )

            current_content = rewrite_content
            plain = self._to_plain(current_content)

            try:
                eng = EngagementAnalyzer().analyze(plain)
                read = ReadabilityScorer().analyze(plain)
            except Exception as e:
                print(f"    → Quality check error (skipped): {e}")
                return QualityResult(
                    content=current_content, passed=True,
                    attempts=1 + rewrite_num, cost_usd=total_cost
                )

            failures = self._evaluate(eng, read)
            is_last = rewrite_num == MAX_REWRITES
            self._print_quality_line(
                eng, read, failures,
                attempt=1 + rewrite_num,
                rewriting=bool(failures) and not is_last
            )

            if not failures:
                return QualityResult(
                    content=current_content, passed=True,
                    attempts=1 + rewrite_num, cost_usd=total_cost
                )

        return QualityResult(
            content=current_content, passed=False,
            attempts=1 + MAX_REWRITES, failures=failures, cost_usd=total_cost
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _evaluate(self, eng: dict, read: dict) -> list:
        """Return list of failure keys. Empty list = passed."""
        failures = []

        # Readability
        flesch = read.get('readability_metrics', {}).get('flesch_reading_ease', 0)
        if flesch < FLESCH_THRESHOLD:
            failures.append('readability')

        # Mandatory engagement criteria
        scores = eng.get('scores', {})
        if not scores.get('hook', False):
            failures.append('hook')
        if not scores.get('ctas', False):
            failures.append('ctas')

        # Optional engagement criteria — need ≥2 of 3
        optional_passed = sum([
            scores.get('stories', False),
            scores.get('rhythm', False),
            scores.get('paragraphs', False),
        ])
        if optional_passed < ENGAGEMENT_OPTIONAL_MIN:
            optional_failures = [k for k in ('stories', 'rhythm', 'paragraphs') if not scores.get(k)]
            failures.extend(optional_failures)

        return failures

    def _build_fix_instructions(self, failures: list) -> str:
        """Build targeted fix instructions from a list of failure keys."""
        instructions = []
        if 'readability' in failures:
            instructions.append(
                "Simplify language throughout. Break any sentence over 20 words into two. "
                "Replace multi-syllable words with simpler alternatives. "
                "Target a Flesch Reading Ease score of 60+."
            )
        if 'hook' in failures:
            instructions.append(
                "Rewrite the opening paragraph. Don't start with a definition or 'X is a...'. "
                "Open with a question, a specific scenario, or a direct statement of benefit."
            )
        if 'ctas' in failures:
            instructions.append(
                "Add at least 2 calls to action — one before the halfway point, one near the end. "
                "Use natural language like 'Book a couples massage' or 'Get in touch to arrange your visit'."
            )
        if 'stories' in failures:
            instructions.append(
                "Include at least one brief client scenario — e.g. 'One of our regulars, a nurse who works "
                "long shifts, finds that...' or 'Couples celebrating anniversaries often tell us...'. "
                "Doesn't need a name."
            )
        if 'rhythm' in failures:
            instructions.append(
                "Vary sentence length. Mix short punchy sentences (5–8 words) with medium ones. "
                "Avoid 5+ sentences in a row at similar length."
            )
        if 'paragraphs' in failures:
            instructions.append(
                "Break any paragraph with more than 4 sentences into two shorter ones."
            )
        return "\n".join(f"- {inst}" for inst in instructions)

    def _rewrite(self, content: str, topic: str, content_type: str,
                 failures: list, attempt_num: int):
        """
        Call Claude API to rewrite content with targeted instructions.
        Returns (rewritten_content, cost_usd) or (None, 0.0) on API error.
        """
        brand_voice = self._load_brand_voice()
        fix_instructions = self._build_fix_instructions(failures)

        prompt = f"""You are rewriting an existing piece of content to improve its quality.

Topic: {topic}
Content type: {content_type}

Brand voice guidance:
{brand_voice}

The content needs the following specific improvements:
{fix_instructions}

Return ONLY the corrected HTML content. Do not add any explanation or commentary.
Keep the same structure (sections, FAQ, schema) — only improve the prose quality.

Content to rewrite:
{content}"""

        try:
            msg = self._client.messages.create(
                model='claude-sonnet-4-6',
                max_tokens=8096,
                messages=[{'role': 'user', 'content': prompt}],
            )
            rewritten = msg.content[0].text.strip()
            cost = (
                (msg.usage.input_tokens / 1_000_000 * _INPUT_COST_PER_M) +
                (msg.usage.output_tokens / 1_000_000 * _OUTPUT_COST_PER_M)
            )
            return rewritten, cost
        except Exception as e:
            print(f"    → Rewrite API error (attempt {attempt_num}): {e}")
            return None, 0.0

    def _load_brand_voice(self) -> str:
        """Load brand voice markdown for this client."""
        abbr = self._config.get('abbreviation', '').lower()
        brand_voice_path = _ROOT / 'clients' / abbr / 'brand-voice.md'
        try:
            return Path(brand_voice_path).read_text(encoding='utf-8')[:2000]
        except FileNotFoundError:
            return ''

    def _to_plain(self, html: str) -> str:
        """Strip HTML to plain text, preserving paragraph breaks for scoring."""
        text = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\n[ \t]+', '\n', text)
        text = re.sub(r' +', ' ', text).strip()
        return text

    def _print_quality_line(self, eng: dict, read: dict, failures: list,
                             attempt: int, rewriting: bool) -> None:
        """Print quality summary line to stdout."""
        scores = eng.get('scores', {})
        flesch = read.get('readability_metrics', {}).get('flesch_reading_ease', 0)

        def tick(key):
            return '✓' if scores.get(key) else '✗'

        flesch_tick = '✓' if flesch >= FLESCH_THRESHOLD else '✗'

        line = (
            f"    → Quality: Flesch {flesch:.0f} {flesch_tick} | "
            f"hook {tick('hook')} | ctas {tick('ctas')} | "
            f"stories {tick('stories')} | rhythm {tick('rhythm')} | paras {tick('paragraphs')}"
        )

        if failures and rewriting:
            # attempt=1 → about to do rewrite 1/2; attempt=2 → about to do rewrite 2/2
            line += f" — rewriting ({attempt}/{MAX_REWRITES})"
        elif failures and not rewriting:
            line += f" — FAILED after {MAX_REWRITES} rewrites → Review Required"
        else:
            line += " — passed"

        print(line)
```

### Step 3.3: Run tests to confirm they pass

- [ ] Run:

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_quality_gate.py -v
```

Expected: all tests PASS. If `test_rewrites_once_when_first_check_fails` or `test_returns_passed_false_after_max_rewrites_still_failing` fail due to `PASSING_CONTENT` actually passing, adjust the `FAILING_CONTENT` to be more definitively complex.

### Step 3.4: Commit

- [ ] Commit:

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && git add data_sources/modules/quality_gate.py tests/test_quality_gate.py && git commit -m "feat: add QualityGate class with check-rewrite loop and targeted instructions"
```

---

## Task 4: Integrate QualityGate into `geo_batch_runner.py`

**Files:**
- Modify: `src/geo_batch_runner.py`

### Step 4.1: Add imports at the top of `geo_batch_runner.py`

- [ ] In `geo_batch_runner.py`, update the `google_sheets` import (line 44-47) to also import `REVIEW_REQUIRED_VALUE`:

```python
from google_sheets import (
    read_pending, update_status, update_cost, update_file_path,
    send_email, IMAGES_PENDING_VALUE, REVIEW_REQUIRED_VALUE,
)
```

- [ ] Add `QualityGate` import after the existing module imports (after line 48):

```python
from quality_gate import QualityGate
```

### Step 4.2: Remove the `run_quality_check()` function

- [ ] Delete the entire `run_quality_check()` function (lines 317–343).

### Step 4.3: Replace `run_quality_check()` on the normal write path

The normal write path currently looks like this (around lines 587–598):

```python
# Mark DONE and record cost in Column C immediately after saving
update_status(row, 'DONE')
cost_str = f"${cost_usd:.4f}"
try:
    update_cost(row, cost_str)
except Exception:
    pass  # Cost tracking is non-critical

total_cost_usd += cost_usd
written_files.append(str(filepath.relative_to(ROOT)))
print(f"[{i}/{total}] ✓ Written: {filepath.relative_to(ROOT)} ({word_count} words, {cost_str})")
run_quality_check(content)
```

- [ ] Replace that entire block with:

```python
# Quality gate — checks and rewrites if needed before publishing
gate = QualityGate(client, business_config)
gate_result = gate.check_and_improve(content, address, content_type)
content = gate_result.content       # use final (possibly rewritten) version
cost_usd += gate_result.cost_usd    # add rewrite costs to row total

if not gate_result.passed:
    update_status(row, REVIEW_REQUIRED_VALUE)
    update_file_path(row, str(filepath.relative_to(ROOT)))
    total_cost_usd += cost_usd
    written_files.append(str(filepath.relative_to(ROOT)))
    print(f"[{i}/{total}] ⚠ Review Required: {filepath.relative_to(ROOT)} ({word_count} words, ${cost_usd:.4f})")
    print(f"    Failed: {', '.join(gate_result.failures)}")
    if i < total:
        time.sleep(65)
    continue

# Gate passed — write DONE status and cost, then publish
total_cost_usd += cost_usd
written_files.append(str(filepath.relative_to(ROOT)))
cost_str = f"${cost_usd:.4f}"
print(f"[{i}/{total}] ✓ Written: {filepath.relative_to(ROOT)} ({word_count} words, {cost_str})")
update_status(row, 'DONE')
try:
    update_cost(row, cost_str)
except Exception:
    pass  # Cost tracking is non-critical
```

### Step 4.4: Verify Images o/s path is unchanged

- [ ] Read the Images o/s deferral path (around line 572–585) and confirm `run_quality_check(content)` has been removed from it (it was called at line 582). Since we deleted the function in Step 4.2, if it's still called there it will now error. Remove the call from the Images o/s path only — do not add the gate there.

The Images o/s path after Step 4.4 should end with:
```python
print(f"[{i}/{total}] ✓ Written (Images o/s): {filepath.relative_to(ROOT)} ({word_count} words, ${cost_usd:.4f})")
if i < total:
    time.sleep(65)
continue
```

### Step 4.5: Smoke test — dry run (no publish)

- [ ] Confirm the runner starts cleanly without import errors:

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -c "import sys; sys.argv=['geo_batch_runner']; exec(open('src/geo_batch_runner.py').read().split('def main')[0])" 2>&1 | head -5
```

Expected: no `ImportError` or `NameError`

### Step 4.6: Commit

- [ ] Commit:

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && git add src/geo_batch_runner.py && git commit -m "feat: integrate QualityGate into batch runner — blocking gate with auto-rewrite and Review Required fallback"
```

---

## Task 5: End-to-end verification

### Step 5.1: Run all new tests together

- [ ] Run:

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_engagement_analyzer.py tests/test_quality_gate.py -v
```

Expected: all tests PASS

### Step 5.2: Confirm STATUS.md is up to date

- [ ] Add the following under `## What's Built and Working` in `STATUS.md`:

```markdown
### Quality gate (session 12)
- [x] `QualityGate` class in `data_sources/modules/quality_gate.py` — check/rewrite loop, max 2 rewrites
- [x] Pass thresholds: Flesch Reading Ease ≥ 60 + Hook (mandatory) + CTAs (mandatory) + 2/3 optional (stories, rhythm, paragraphs)
- [x] Targeted rewrite instructions built from specific failures
- [x] On final failure: row marked `Review Required` in Sheet, file saved locally, publish skipped
- [x] Mini-stories re-enabled as 5th criterion with massage therapy patterns (unnamed client scenarios)
- [x] `REVIEW_REQUIRED_VALUE` added to `google_sheets.py`
- [x] `geo_batch_runner.py` — DONE/cost writes now deferred until after gate passes
```

### Step 5.3: Final commit

- [ ] Commit STATUS.md:

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && git add STATUS.md && git commit -m "docs: update STATUS.md — quality gate complete"
```
