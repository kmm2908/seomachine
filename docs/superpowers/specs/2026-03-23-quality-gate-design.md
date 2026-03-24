# Quality Gate — Design Spec

**Date:** 2026-03-23
**Status:** Approved

---

## Overview

Add a blocking quality gate to the batch content pipeline. After an article is written, it is checked against readability and engagement criteria. If it fails, Claude rewrites it with targeted fix instructions and re-checks. After 2 failed rewrites the row is flagged for human review and publishing is skipped.

---

## Pass Thresholds

Two checks must both pass before an article can proceed to publishing.

### 1. Readability — Flesch Reading Ease ≥ 60

Measured by `ReadabilityScorer.analyze()` → `readability_metrics.flesch_reading_ease`.

Flesch 60 = "fairly easy to read" — accessible to a general adult audience. Appropriate for local service pages targeting the general public. Articles scoring below 60 are too complex for the target audience.

### 2. Engagement — 5 criteria, mandatory + optional

| Criterion | Type | Pass condition |
|---|---|---|
| Hook | **Mandatory** | Must pass — opening is not generic/definitional |
| CTAs | **Mandatory** | Must pass — ≥2 CTAs, one in first half, one after 70% |
| Mini-stories | Optional | Client scenarios detected in content |
| Rhythm | Optional | Sentence length variety score ≥ 45 |
| Paragraphs | Optional | ≤3 paragraphs with 5+ sentences |

**Overall engagement pass = Hook ✓ AND CTAs ✓ AND ≥2 of 3 optional criteria**

---

## QualityGate Class

**New file:** `data_sources/modules/quality_gate.py`

### Interface

```python
result = QualityGate(anthropic_client, client_config).check_and_improve(
    content: str,
    topic: str,
    content_type: str
) -> QualityResult
```

`client_config` is the parsed dict from `clients/[abbr]/config.json` (as returned by `load_business_config()`). The QualityGate derives the brand voice path from `client_config['abbreviation']` and reads `clients/[abbr]/brand-voice.md` directly to include in the rewrite prompt.

### QualityResult

```python
@dataclass
class QualityResult:
    content: str        # final content (original or rewritten)
    passed: bool        # whether all thresholds were met on any attempt
    attempts: int       # total writes (1 = original passed, up to 3)
    failures: list[str] # list of failed criteria on the final attempt
    cost_usd: float     # cumulative API cost of all rewrite attempts (not original write)
```

### Internal Loop

1. Run `EngagementAnalyzer` + `ReadabilityScorer` on content
2. Evaluate against thresholds — if both pass, return immediately (`passed=True`, `attempts=1`, `cost_usd=0.0`)
3. Build targeted rewrite prompt from specific failures (see Targeted Rewrite Instructions)
4. Call Claude API → get rewritten content. Accumulate token cost into `cost_usd`
5. Re-run checks on rewritten content
6. If pass → return `passed=True`. If fail and total rewrites < 2 → go to step 3
7. After 2 rewrites still failing → return `passed=False`, `content` = last rewritten version, `failures` = failures from final check

Max rewrites: 2 (attempts 2 and 3). Original write is attempt 1.

### Error Handling

**If Claude API call throws during a rewrite attempt** (network error, rate limit, etc.):
- Treat as a failed rewrite attempt — increment attempt counter, retain the previous content unchanged
- Continue to the next attempt if retries remain, otherwise return `passed=False` with `failures=['rewrite_api_error']`
- Do not propagate the exception

**If `EngagementAnalyzer` or `ReadabilityScorer` throws** (malformed content, zero-length input, etc.):
- Fail-safe: treat as passed and return immediately (`passed=True`, `attempts=1`, `cost_usd=0.0`)
- Log a warning to stdout: `→ Quality check error (skipped): {error}`
- This preserves the existing non-blocking behaviour for edge cases

---

## Targeted Rewrite Instructions

Only failures from the current attempt are included in the rewrite prompt. The prompt also includes the client brand voice (read from `clients/[abbr]/brand-voice.md`) and the original topic.

| Failure | Instruction injected |
|---|---|
| Flesch < 60 | "Simplify language throughout. Break any sentence over 20 words into two. Replace multi-syllable words with simpler alternatives. Target a Flesch Reading Ease score of 60+." |
| Hook fails | "Rewrite the opening paragraph. Don't start with a definition or 'X is a...'. Open with a question, a specific scenario, or a direct statement of benefit." |
| CTAs not distributed | "Add at least 2 calls to action — one before the halfway point, one near the end. Use natural language like 'Book a couples massage' or 'Get in touch to arrange your visit'." |
| Mini-stories absent | "Include at least one brief client scenario — e.g. 'One of our regulars, a nurse who works long shifts, finds that...' or 'Couples celebrating anniversaries often tell us...'. Doesn't need a name." |
| Rhythm fails | "Vary sentence length. Mix short punchy sentences (5–8 words) with medium ones. Avoid 5+ sentences in a row at similar length." |
| Long paragraphs | "Break any paragraph with more than 4 sentences into two shorter ones." |

---

## Mini-Stories Pattern Update

`engagement_analyzer.py` currently checks for a hardcoded list of specific first names (Sarah, Mike, Lisa etc.) plus outcome verbs. This does not match massage therapy content.

### Updated trigger patterns (unnamed client scenarios)

- `"One of our (clients|regulars|customers|guests)"`
- `"(A|One) (client|couple|guest|customer|visitor|person)"`
- `"(Many|Some|Most) of our (clients|regulars|guests)"`
- `"(Couples|People|Clients) (celebrating|coming|looking|dealing|suffering)"`
- `"(imagine|picture) (coming|arriving|booking|feeling)"`
- Retain existing name patterns as secondary detection

### Updated outcome verbs (massage therapy domain)

Replace the existing SaaS-domain verb list with:
`felt|relieved|noticed|returned|booked|recommended|improved|relaxed|found|discovered|said|told us|shared`

Scenario must include an outcome verb in surrounding context (±100 chars) to count.

### Re-enabling in `analyze()`

Mini-stories is currently dead code — `analyze()` has comment "4 criteria, stories removed" and only populates 4 keys. The following updates are required throughout `engagement_analyzer.py`:

1. Add `'stories': self._analyze_mini_stories(content)` to the `results` dict in `analyze()`
2. Add `'stories': results['stories']['count'] >= 1` to `results['scores']`
3. Change `total_criteria` from `4` to `5`
4. Update `passed_count` and `all_passed` to reflect 5 criteria
5. Update `format_results()` table header and column layout from 4 to 5 criteria
6. Update `main()` summary line if it references criterion count

The engagement pass logic in `QualityGate` implements the mandatory/optional split — `EngagementAnalyzer` itself just scores all 5 and returns results; the gate decides what "pass" means.

---

## Batch Runner Integration

### Quality gate runs on the normal write path only

The batch runner has two paths that currently call `run_quality_check()`:
- **Normal write path** (line 598) — gate runs here
- **Images o/s deferral path** (line 582) — gate does **not** run here; content was already saved and the row is already in a deferred state; adding the gate would interfere with the retry-images-only logic

### Replace `run_quality_check()` on the normal write path

The `DONE` status write and cost write currently happen before `run_quality_check()`. These must be deferred until after the gate passes.

New flow on the normal write path:
```python
# 1. Run quality gate
gate = QualityGate(client, client_config)
result = gate.check_and_improve(content, topic, content_type)
content = result.content          # use final version (may be rewritten)
total_cost_usd += result.cost_usd # add rewrite costs to running total

# 2. Handle gate result
if not result.passed:
    sheets.update_status(row_idx, REVIEW_REQUIRED_VALUE)
    sheets.update_file_path(row_idx, str(filepath.relative_to(ROOT)))
    # No cost write, no DONE status — only status + file path
    print(f"[{i}/{total}] ⚠ Review Required: {filepath.relative_to(ROOT)} — quality failed after 2 rewrites")
    print(f"   Failed: {', '.join(result.failures)}")
    if i < total:
        time.sleep(65)
    continue

# 3. Gate passed — now write DONE status and cost
cost_str = f"${total_cost_usd_for_row:.4f}"  # includes rewrite costs
sheets.update_status(row_idx, 'DONE')
sheets.update_cost(row_idx, cost_usd)

# 4. Publish (existing publish block, unchanged)
if publish:
    ...
```

The standalone `run_quality_check()` function in `geo_batch_runner.py` is removed once the gate is in place.

### Console Output Format

`(1/2)` in the rewriting label = rewrite attempt 1 of maximum 2.

Pass on first write:
```
→ Quality: Flesch 72 ✓ | hook ✓ | ctas ✓ | stories ✓ | rhythm ✓ | paras ✓ — passed
```

Fail then pass after rewrite:
```
→ Quality: Flesch 45 ✗ | hook ✓ | ctas ✗ | stories ✗ — rewriting (1/2)
→ Quality: Flesch 63 ✓ | hook ✓ | ctas ✓ | stories ✓ — passed
```

Fail after all rewrites:
```
→ Quality: Flesch 52 ✗ | hook ✓ | ctas ✗ — FAILED after 2 rewrites → Review Required
```

Quality check error (fail-safe):
```
→ Quality check error (skipped): <error message>
```

---

## Google Sheets Changes

**`google_sheets.py`:**
- Add `REVIEW_REQUIRED_VALUE = "Review Required"` constant alongside existing `IMAGES_PENDING_VALUE`
- `read_pending()` already skips `Review Required` rows correctly (it only picks up `Write Now` and `Images o/s`)
- On `Review Required`: call `update_status()` and `update_file_path()` only — do not write cost (Column C) or clear any other columns

---

## Files Changed

| File | Change |
|---|---|
| `data_sources/modules/quality_gate.py` | **New** — QualityGate class and QualityResult dataclass |
| `data_sources/modules/engagement_analyzer.py` | Re-enable mini-stories; update patterns and outcome verbs; update all 4→5 criterion references throughout |
| `data_sources/modules/google_sheets.py` | Add `REVIEW_REQUIRED_VALUE` constant |
| `src/geo_batch_runner.py` | Replace `run_quality_check()` on normal write path; defer DONE/cost writes until after gate; remove standalone `run_quality_check()` function |

---

## Out of Scope

- No changes to content agent `.md` files
- No changes to WordPress publisher
- No changes to image generation pipeline
- `republish_existing.py` is unaffected (no quality check on republishing)
- Quality gate does not run on the Images o/s retry path
