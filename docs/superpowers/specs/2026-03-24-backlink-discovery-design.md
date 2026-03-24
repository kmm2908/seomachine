# Backlink Discovery & Tracking — Design Spec

**Date:** 2026-03-24
**Project:** SEO Machine
**Status:** Approved

---

## Overview

A backlink opportunity discovery and tracking system for local SMB clients (massage therapy). Focuses on the three highest-ROI, most automatable strategies: competitor backlink replication, resource page finding, and unlinked brand mentions. Results are written to a dedicated Google Sheet per client and a dated markdown report. A slash command runs the full pipeline and adds Claude's strategic analysis on top.

Designed so that outreach email generation can be added later as a thin extension — the data structures and sheet columns are already outreach-ready.

---

## Architecture

### New Files

| Path | Purpose |
|------|---------|
| `src/research/research_backlinks.py` | Discovery script — three passes, scores, deduplicates, writes to Sheet |
| `.claude/commands/backlinks.md` | Slash command — runs script, Claude adds strategic layer |

### Modified Files

| Path | Change |
|------|--------|
| `data_sources/modules/dataforseo.py` | Add `get_backlinks(domain, filters)` method |
| `clients/[abbr]/config.json` | Add `backlinks_sheet_id` field per client |

### Output Files (per run)

| Path | Purpose |
|------|---------|
| `research/[abbr]/backlinks-YYYY-MM-DD.md` | Dated opportunity report (same pattern as `blog-topics-*.md`) |

---

## Google Sheet Structure

One dedicated Sheet per client. `backlinks_sheet_id` stored in `clients/[abbr]/config.json`.

| Col | Field | Type | Notes |
|-----|-------|------|-------|
| A | Prospect URL | string | Primary key — used for duplicate detection on re-runs |
| B | Page Title | string | Auto-populated |
| C | Type | enum | `competitor-backlink` / `resource-page` / `brand-mention` |
| D | Domain Authority | integer | DataForSEO rank score 0–100 |
| E | Monthly Traffic | integer | Estimated organic visits |
| F | Referring Domains | integer | Quality signal for the linking domain |
| G | Outreach Angle | string | One-line pitch rationale — feeds outreach module later |
| H | Status | enum | `New` / `Contacted` / `Won` / `Lost` / `Skipped` |
| I | Date Found | date | Auto-set by script on insert |
| J | Date Contacted | date | Updated manually (or by future outreach module) |
| K | Notes | string | Free text — responses, follow-up reminders |
| L | Link Won URL | string | Filled in when link is secured |

**Behaviour on re-runs:** The script only inserts rows where Column A is not already present. Existing rows (including manual status updates) are never overwritten.

---

## Discovery Script — Three Passes

### Pass 1: Competitor Backlink Replication

- Source: `clients/[abbr]/competitor-analysis.md` (already populated by `research_competitors.py`)
- API: DataForSEO Backlinks API (`/v3/backlinks/backlinks`)
- Filters: dofollow only · DR 20+ · in-content links · linking domain 500+ monthly visits
- Domain blocklist: reuses existing directory/aggregator blocklist from `research_competitors.py`
- Outreach angle template: `"Links to [competitor] on [topic] — pitch guest post or link insert"`
- Type: `competitor-backlink`

### Pass 2: Resource Page Finding

- API: DataForSEO SERP API (existing)
- Queries (4–5 per client, derived from `niche` and `area` in config):
  - `[niche] "useful resources"`
  - `[niche] "helpful links"`
  - `[location] inurl:resources [niche]`
  - `[niche] "recommended sites"`
  - `[niche] resource guide`
- Top 10 results per query, deduped across queries
- Outreach angle: `"Curated resource list — ask to be included"`
- Type: `resource-page`

### Pass 3: Unlinked Brand Mentions

- API: DataForSEO SERP API
- Queries:
  - `"[business name]" -site:[domain]`
  - `"[business name]" -site:[domain] -site:twitter.com -site:facebook.com -site:instagram.com`
- Filters out known social/directory domains
- Outreach angle: `"Already mentions the brand — just ask for the link"`
- Type: `brand-mention`
- Gets highest priority bonus in scoring (lowest-effort wins)

### Shared Data Model

All three passes normalise results into a common `Opportunity` dataclass:

```python
@dataclass
class Opportunity:
    url: str
    title: str
    type: str           # competitor-backlink | resource-page | brand-mention
    domain_authority: int
    monthly_traffic: int
    referring_domains: int
    outreach_angle: str
    score: float        # computed
```

This makes it straightforward to add a fourth pass (e.g. broken link building) without touching the Sheet writer or scoring logic.

### Scoring Formula

```
score = (domain_authority / 100) × 0.4
      + (traffic_score)          × 0.3
      + (type_bonus)             × 0.3

type_bonus:  brand-mention = 1.0 | resource-page = 0.7 | competitor-backlink = 0.5
traffic_score: normalised 0–1 within the result set
```

Results written to Sheet ordered by score descending (highest-priority at top).

---

## Script CLI

```bash
# Full discovery run
python3 src/research/research_backlinks.py --abbr gtm

# Run one pass only
python3 src/research/research_backlinks.py --abbr gtm --type brand-mention

# Cap total results written to sheet
python3 src/research/research_backlinks.py --abbr gtm --limit 50

# Re-run all passes and add new prospects (won't overwrite existing rows)
python3 src/research/research_backlinks.py --abbr gtm --refresh
```

Default `--limit` is 30. Script prints a summary table on completion:

```
→ Backlinks: 8 brand-mention · 12 resource-page · 18 competitor-backlink — 38 total, 6 dupes skipped
→ Written to sheet: 30 new rows (capped at --limit)
→ Report: research/gtm/backlinks-2026-03-24.md
```

---

## Slash Command: `/backlinks [abbr]`

1. Runs `python3 src/research/research_backlinks.py --abbr [abbr]`
2. Reads the generated markdown report
3. Claude outputs:
   - **Quick wins** — top 3 brand mentions with a ready-to-use outreach note
   - **Priority targets** — top 5 resource pages + competitor backlinks ranked by score with suggested angle
   - **This month's action list** — recommended 2–3 to pursue first, with suggested sequence

Follows the same pattern as `/research-blog-topics` — Python handles data, Claude handles strategy.

---

## Outreach Hook Points (Future Extension)

The following are deliberately left as stubs — no code written now, but the design accommodates them cleanly:

- **Column G (Outreach Angle)** is populated now. A future `generate_outreach_email(opportunity)` function reads it and drafts a personalised email.
- **Column H (Status)** = `New` is the trigger. An outreach script would filter for `New` rows, generate drafts, and set status to `Contacted` + fill Column J.
- **Column J (Date Contacted)** and **Column K (Notes)** are reserved for outreach tracking.
- The `Opportunity` dataclass can be extended with `outreach_email: str = ""` without breaking existing code.

---

## Config Changes

`clients/[abbr]/config.json` — add at root level:

```json
"backlinks_sheet_id": "YOUR_GOOGLE_SHEET_ID_HERE"
```

Sheet ID is the long string in the Google Sheets URL. Created manually by the user; the script writes to it via the existing `google_sheets.py` module.

---

## Error Handling

- DataForSEO API errors: log and continue to next pass (partial results are still useful)
- Missing `backlinks_sheet_id` in config: exit with clear message
- Missing `competitor-analysis.md`: skip Pass 1 with a warning, continue Passes 2 and 3
- Sheet write failure: results still saved to markdown report (data never lost)

---

## Out of Scope (This Version)

- Outreach email generation
- Automated email sending
- Link monitoring (checking if a won link goes dead)
- Broken link building pass
- Scheduling / cron integration
