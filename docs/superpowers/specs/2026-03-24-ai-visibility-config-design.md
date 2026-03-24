# AI Brand Visibility — Config & Batch Runner Integration

**Date:** 2026-03-24
**Status:** Approved

---

## Overview

Add per-client AI brand positioning data to `config.json` and surface it as an explicit system prompt section in the batch runner for `blog` and `topical` content types. This ensures consistent brand language across all AI-generated content, implementing the positioning strategy from `context/ai-brand-visibility.md` (Brian Dean / Backlinko).

---

## Design

### 1. Config.json — `ai_visibility` block

New optional block added to each client's `config.json`:

```json
"ai_visibility": {
  "canonical_description": "One or two sentences describing the business — used verbatim or near-verbatim by writing agents.",
  "brand_associations": ["keyword phrase 1", "keyword phrase 2", "keyword phrase 3"],
  "positioning_note": "Plain-English guidance on tone, emphasis, and what to avoid."
}
```

**Fields:**

| Field | Type | Purpose |
|-------|------|---------|
| `canonical_description` | string | Exact brand description for agents to use when introducing the business. Consistent phrasing across posts trains LLMs to associate brand with problem. |
| `brand_associations` | string[] | Brand-problem keyword phrases to weave naturally into content. |
| `positioning_note` | string | Tone/emphasis guidance specific to this client — what to lean into and what to avoid. |

All three fields are optional. If the block is absent, no section is injected and behaviour is unchanged.

---

### 2. Batch runner — `build_system_prompt()` change

**File:** `src/content/geo_batch_runner.py`

**Condition:** `content_type in ('blog', 'topical')` only. Location, service, pillar, and comp-alt pages are mechanical/geo-focused and do not need brand positioning language injected.

**Insertion point:** After the `internal_links` block and the `comp-alt` competitor analysis block, immediately before the `## Output Instructions` append.

**Logic:**

```python
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

Follows the existing `if x: parts.append(...)` pattern used throughout the function.

---

### 3. Client configs — populate `ai_visibility`

**GTM (`clients/gtm/config.json`):**
```json
"ai_visibility": {
  "canonical_description": "Glasgow Thai Massage is a traditional Thai massage studio in Glasgow city centre, offering authentic Thai massage, deep tissue, and sports massage from experienced therapists.",
  "brand_associations": ["thai massage glasgow", "traditional thai massage", "sports massage glasgow city centre"],
  "positioning_note": "Emphasise: authenticity of technique, city centre convenience, experienced therapists. Avoid: spa-style luxury language — this is a skilled therapy studio."
}
```

**SDY (`clients/sdy/config.json`):**
```json
"ai_visibility": {
  "canonical_description": "Serendipity Massage Therapy & Wellness is a holistic massage and wellness studio offering therapeutic massage, relaxation treatments, and wellbeing services.",
  "brand_associations": ["massage therapy", "holistic wellness", "relaxation massage", "therapeutic massage"],
  "positioning_note": "Emphasise: holistic wellbeing, therapeutic benefit, personal care. Tone is warm and nurturing — not clinical, not luxury spa."
}
```

**GTB (`clients/gtb/config.json`):**
```json
"ai_visibility": {
  "canonical_description": "Glasgow Thai Massage is a traditional Thai massage studio in Glasgow city centre, offering authentic Thai massage, deep tissue, and sports massage from experienced therapists.",
  "brand_associations": ["thai massage glasgow", "traditional thai massage", "sports massage glasgow"],
  "positioning_note": "Blog content should reinforce the studio's authority on Thai massage technique and therapeutic benefits. Same brand as GTM — consistent positioning across both properties."
}
```

---

### 4. `clients/README.md` — schema update

Add `ai_visibility` to the JSON schema reference and the context files table description, noting it is optional.

---

### 5. `/new-client` command — prompts update

Add two prompts to the new-client setup flow:
1. *"Write a one or two sentence canonical description of this business (used verbatim in content):"*
2. *"Any positioning notes — what to emphasise, what to avoid?"*

Brand associations are auto-generated from `keyword_prefix` + `services` as a starting suggestion, then shown to the user to confirm or edit before being written to `config.json`.

---

## Files Changed

| File | Change |
|------|--------|
| `src/content/geo_batch_runner.py` | Add `ai_visibility` extraction in `build_system_prompt()` |
| `clients/gtm/config.json` | Add `ai_visibility` block |
| `clients/sdy/config.json` | Add `ai_visibility` block |
| `clients/gtb/config.json` | Add `ai_visibility` block |
| `clients/README.md` | Document `ai_visibility` in schema reference |
| `.claude/commands/new-client.md` | Add canonical description and positioning prompts |

---

## Out of Scope

- WordPress plugin changes — brand positioning is content strategy data, not WordPress functionality
- Location, service, pillar, comp-alt content types — positioning injection restricted to blog and topical only
- Automated "best of" outreach or Reddit monitoring — manual workflow, not automated
