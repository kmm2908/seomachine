# AI Brand Visibility — Config & Batch Runner Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-client `ai_visibility` block to `config.json` and inject it as an explicit `## AI Brand Positioning` section in the batch runner system prompt for `blog` and `topical` content types only.

**Architecture:** The `ai_visibility` block lives in each client's `config.json`. `build_system_prompt()` in the batch runner reads it from `business_config` (already passed in) and appends a formatted section to `parts` — only when `content_type` is `blog` or `topical`. No new files; no new dependencies.

**Tech Stack:** Python 3, existing `geo_batch_runner.py` pattern (`if x: parts.append(...)`), JSON config files, markdown command files.

---

## File Map

| File | Action |
|------|--------|
| `src/content/geo_batch_runner.py` | Modify — add `ai_visibility` extraction in `build_system_prompt()` |
| `clients/gtm/config.json` | Modify — add `ai_visibility` block |
| `clients/sdy/config.json` | Modify — add `ai_visibility` block |
| `clients/gtb/config.json` | Modify — add `ai_visibility` block |
| `clients/README.md` | Modify — document `ai_visibility` in schema reference |
| `.claude/commands/new-client.md` | Modify — add canonical description + positioning prompts |
| `tests/test_ai_visibility.py` | Create — smoke test for the injection logic |

---

## Task 1: Write the failing test

**Files:**
- Create: `tests/test_ai_visibility.py`

The batch runner's `build_system_prompt()` imports from the project root. The test calls it directly with a synthetic `business_config` containing an `ai_visibility` block.

- [ ] **Step 1: Create the test file**

```python
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


if __name__ == '__main__':
    test_ai_visibility_injected_for_blog()
    test_ai_visibility_injected_for_topical()
    test_ai_visibility_not_injected_for_location()
    test_ai_visibility_not_injected_for_service()
    test_ai_visibility_missing_block_no_error()
    test_ai_visibility_partial_fields()
    print("All tests passed.")
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine"
python3 tests/test_ai_visibility.py
```

Expected: `AssertionError` on `test_ai_visibility_injected_for_blog` — the section doesn't exist yet.

---

## Task 2: Add `ai_visibility` injection to the batch runner

**Files:**
- Modify: `src/content/geo_batch_runner.py:194-199` (after the comp-alt block, before Output Instructions)

- [ ] **Step 1: Open `src/content/geo_batch_runner.py` and locate the insertion point**

Find lines 194–199 (the comp-alt block):

```python
    # Competitor analysis — only needed for comp-alt pages
    if content_type == 'comp-alt':
        competitor_analysis = load_file(client_dir / 'competitor-analysis.md')
        if competitor_analysis:
            parts.append(f"\n\n## Competitor Analysis\n\n{competitor_analysis}")

    parts.append(          ← Output Instructions start here
```

- [ ] **Step 2: Insert the ai_visibility block immediately after the comp-alt block**

Add these lines between the comp-alt block and `parts.append("\n\n## Output Instructions...`:

```python
    # AI brand positioning — blog and topical only
    if content_type in ('blog', 'topical') and business_config:
        ai_vis = business_config.get('ai_visibility', {})
        if ai_vis:
            canonical = ai_vis.get('canonical_description', '')
            associations = ', '.join(ai_vis.get('brand_associations', []))
            note = ai_vis.get('positioning_note', '')
            section = "## AI Brand Positioning\n\n"
            if canonical:
                section += f"Use this description (verbatim or close to it) when introducing the business:\n> {canonical}\n\n"
            if associations:
                section += f"Weave these brand-problem associations naturally into the content: {associations}\n\n"
            if note:
                section += f"Positioning guidance: {note}"
            parts.append(f"\n\n{section.strip()}")
```

- [ ] **Step 3: Run the tests**

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine"
python3 tests/test_ai_visibility.py
```

Expected: `All tests passed.`

- [ ] **Step 4: Commit**

```bash
git add src/content/geo_batch_runner.py tests/test_ai_visibility.py
git commit -m "feat: inject ai_visibility brand positioning into blog/topical system prompts"
```

---

## Task 3: Add `ai_visibility` to all three client configs

**Files:**
- Modify: `clients/gtm/config.json`
- Modify: `clients/sdy/config.json`
- Modify: `clients/gtb/config.json`

- [ ] **Step 1: Add to `clients/gtm/config.json`**

Add after the `"niche"` field:

```json
"ai_visibility": {
  "canonical_description": "Glasgow Thai Massage is a traditional Thai massage studio in Glasgow city centre, offering authentic Thai massage, deep tissue, and sports massage from experienced therapists.",
  "brand_associations": ["thai massage glasgow", "traditional thai massage", "sports massage glasgow city centre"],
  "positioning_note": "Emphasise: authenticity of technique, city centre convenience, experienced therapists. Avoid: spa-style luxury language — this is a skilled therapy studio."
}
```

- [ ] **Step 2: Add to `clients/sdy/config.json`**

Add after the `"niche"` field:

```json
"ai_visibility": {
  "canonical_description": "Serendipity Massage Therapy & Wellness is a holistic massage and wellness studio offering therapeutic massage, relaxation treatments, and wellbeing services.",
  "brand_associations": ["massage therapy", "holistic wellness", "relaxation massage", "therapeutic massage"],
  "positioning_note": "Emphasise: holistic wellbeing, therapeutic benefit, personal care. Tone is warm and nurturing — not clinical, not luxury spa."
}
```

- [ ] **Step 3: Add to `clients/gtb/config.json`**

Add after the `"niche"` field:

```json
"ai_visibility": {
  "canonical_description": "Glasgow Thai Massage is a traditional Thai massage studio in Glasgow city centre, offering authentic Thai massage, deep tissue, and sports massage from experienced therapists.",
  "brand_associations": ["thai massage glasgow", "traditional thai massage", "sports massage glasgow"],
  "positioning_note": "Blog content should reinforce the studio's authority on Thai massage technique and therapeutic benefits. Same brand as GTM — consistent positioning across both properties."
}
```

- [ ] **Step 4: Validate all three files are valid JSON**

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine"
python3 -c "
import json
for f in ['clients/gtm/config.json', 'clients/sdy/config.json', 'clients/gtb/config.json']:
    json.load(open(f))
    print(f'✓ {f}')
"
```

Expected:
```
✓ clients/gtm/config.json
✓ clients/sdy/config.json
✓ clients/gtb/config.json
```

- [ ] **Step 5: Re-run the test suite to confirm end-to-end with real GTM config**

```bash
python3 tests/test_ai_visibility.py
```

Expected: `All tests passed.`

- [ ] **Step 6: Commit**

```bash
git add clients/gtm/config.json clients/sdy/config.json clients/gtb/config.json
git commit -m "feat: add ai_visibility brand positioning to GTM, SDY, GTB configs"
```

---

## Task 4: Update `clients/README.md` schema docs

**Files:**
- Modify: `clients/README.md`

- [ ] **Step 1: Add `ai_visibility` to the JSON schema example**

In the `## JSON Schema` section, add after the `"keyword_prefix"` field:

```json
  "niche": "slug identifying the client's market niche e.g. thai-massage, massage-therapy",
  "ai_visibility": {
    "canonical_description": "One or two sentences used verbatim or near-verbatim when introducing the business in blog/topical content.",
    "brand_associations": ["brand-problem phrase 1", "brand-problem phrase 2"],
    "positioning_note": "Plain-English tone guidance — what to emphasise and what to avoid."
  }
```

- [ ] **Step 2: Add a row to the Key fields table**

Under `### Key fields`, add:

```
- **ai_visibility** — Optional. Injected as `## AI Brand Positioning` in system prompts for `blog` and `topical` content types. Implements the consistent-phrasing strategy from `context/ai-brand-visibility.md`. All three sub-fields are optional; omit the block entirely to disable.
```

- [ ] **Step 3: Commit**

```bash
git add clients/README.md
git commit -m "docs: document ai_visibility schema in clients/README.md"
```

---

## Task 5: Update `/new-client` command

**Files:**
- Modify: `.claude/commands/new-client.md`

- [ ] **Step 1: Add two questions to the Step 1 question list**

After Question 10 (Services), add:

```
11. **Canonical brand description** — one or two sentences describing the business, used verbatim in AI-generated content. Suggest a draft based on Q1, Q9, and Q10, then ask the user to confirm or edit.
    - Auto-draft format: "[Business name] is a [keyword_prefix] studio in [area], offering [services joined with commas]."
    - Show the draft and ask: "Does this description work, or would you like to edit it?"
12. **Positioning note** — plain-English guidance on tone: what to emphasise and what to avoid. Enter "skip" to leave blank.
```

Re-number the original Q11–Q13 (WordPress fields) to Q13–Q15. Also update the three `"answer to Q..."` references inside the existing `wordpress` block in the config.json template (Step 3 of new-client.md) from Q11→Q13, Q12→Q14, Q13→Q15.

- [ ] **Step 2: Add `ai_visibility` to the config.json template in Step 3**

In the `Write: clients/[abbr_lowercase]/config.json` block, add after `"services"`:

```json
  "ai_visibility": {
    "canonical_description": "[answer to Q11]",
    "brand_associations": ["[keyword_prefix] [area]", "[keyword_prefix]"],
    "positioning_note": "[answer to Q12, or omit key if skipped]"
  }
```

Note: if Q12 was skipped, omit `positioning_note` from the JSON. The `brand_associations` array is auto-derived from `keyword_prefix` and `area` — no user prompt needed.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/new-client.md
git commit -m "feat: add ai_visibility prompts to /new-client command"
```

---

## Smoke Test

After all tasks complete, verify end-to-end with a real batch run:

- [ ] **Add a test row to the Google Sheet**: Column D = `GTM`, Column E = `blog`, Column A = any blog topic
- [ ] **Run with `--dry-run` equivalent** (single row, no publish):

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine"
python3 src/content/geo_batch_runner.py A2:A2
```

- [ ] **Open the generated HTML file** and confirm the intro paragraph uses wording close to the canonical description
- [ ] **Verify a `location` row** does NOT have brand positioning language changed (run a location row if available, or inspect the system prompt by adding a temporary `print(system_prompt[:3000])` debug line)
