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
from typing import List

# Project root is two levels up from data_sources/modules/
_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(Path(__file__).parent))

from engagement_analyzer import EngagementAnalyzer
from readability_scorer import ReadabilityScorer

# Sonnet 4.6 pricing
_INPUT_COST_PER_M = 3.00
_OUTPUT_COST_PER_M = 15.00

MAX_REWRITES = 2
FLESCH_THRESHOLD = 60        # Flesch Reading Ease >= 60
ENGAGEMENT_OPTIONAL_MIN = 2  # Must pass >=2 of 3 optional criteria


@dataclass
class QualityResult:
    content: str
    passed: bool
    attempts: int
    failures: List[str] = field(default_factory=list)
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
        passing = self._get_passing(eng, read)
        self._print_quality_line(eng, read, failures, attempt=1, rewriting=bool(failures))

        if not failures:
            return QualityResult(content=content, passed=True, attempts=1, cost_usd=0.0)

        # Rewrite loop
        for rewrite_num in range(1, MAX_REWRITES + 1):
            rewrite_content, rewrite_cost = self._rewrite(
                current_content, topic, content_type, failures, rewrite_num, passing
            )
            total_cost += rewrite_cost

            if rewrite_content is None:
                # API error — keep original failures so next retry still gets correct instructions
                if rewrite_num < MAX_REWRITES:
                    continue
                # Exhausted all retries
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
            passing = self._get_passing(eng, read)  # update for next iteration
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

    def _evaluate(self, eng: dict, read: dict) -> List[str]:
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

        # Optional engagement criteria — need >=2 of 3
        optional_passed = sum([
            scores.get('stories', False),
            scores.get('rhythm', False),
            scores.get('paragraphs', False),
        ])
        if optional_passed < ENGAGEMENT_OPTIONAL_MIN:
            optional_failures = [k for k in ('stories', 'rhythm', 'paragraphs') if not scores.get(k)]
            failures.extend(optional_failures)

        return failures

    def _get_passing(self, eng: dict, read: dict) -> List[str]:
        """Return list of criterion keys that currently pass."""
        passing = []
        flesch = read.get('readability_metrics', {}).get('flesch_reading_ease', 0)
        if flesch >= FLESCH_THRESHOLD:
            passing.append('readability')
        scores = eng.get('scores', {})
        for key in ('hook', 'ctas', 'stories', 'rhythm', 'paragraphs'):
            if scores.get(key, False):
                passing.append(key)
        return passing

    def _build_fix_instructions(self, failures: List[str], passing: List[str] = None) -> str:
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
                "Add at least 2 calls to action distributed through the article — one in the first half, one near the end. "
                "Use natural massage therapy CTAs like: 'Book your session today', 'Call us now to arrange your visit', "
                "'Get in touch to book your appointment', 'Book online now', or 'Contact us today'. "
                "Do not put both CTAs at the end — spread them through the content."
            )
        if 'stories' in failures:
            instructions.append(
                "Include at least one brief client scenario — e.g. 'One of our regulars, a nurse who works "
                "long shifts, finds that...' or 'Couples celebrating anniversaries often tell us...'. "
                "Doesn't need a name."
            )
        if 'rhythm' in failures:
            instructions.append(
                "Vary sentence length. Mix short punchy sentences (5-8 words) with medium ones. "
                "Avoid 5+ sentences in a row at similar length."
            )
        if 'paragraphs' in failures:
            instructions.append(
                "Break any paragraph with more than 4 sentences into two shorter ones."
            )
        # Preserve instructions — tell Claude not to break what already works
        preserve_instructions = {
            'readability': "Readability is already good — keep sentences short and clear. Do not make sentences longer or more complex.",
            'hook':        "The opening paragraph is already effective — do not change it.",
            'ctas':        "CTAs are already well distributed — keep them as they are.",
            'stories':     "The client scenario is already present — keep it.",
            'rhythm':      "Sentence rhythm is already varied — maintain this variety.",
            'paragraphs':  "Paragraph lengths are already good — do not merge paragraphs together.",
        }
        if passing:
            preserve_lines = [preserve_instructions[k] for k in passing if k in preserve_instructions]
            if preserve_lines:
                instructions.append("PRESERVE (do not change these — they already pass):\n" + "\n".join(f"- {l}" for l in preserve_lines))
        return "\n".join(f"- {inst}" for inst in instructions)

    def _rewrite(self, content: str, topic: str, content_type: str,
                 failures: List[str], attempt_num: int, passing: List[str] = None):
        """
        Call Claude API to rewrite content with targeted instructions.
        Returns (rewritten_content, cost_usd) or (None, 0.0) on API error.
        """
        brand_voice = self._load_brand_voice()
        fix_instructions = self._build_fix_instructions(failures, passing)

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
        except OSError:
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

    def _print_quality_line(self, eng: dict, read: dict, failures: List[str],
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
            line += f" — FAILED after {MAX_REWRITES} rewrites → Review"
        else:
            line += " — passed"

        print(line)
