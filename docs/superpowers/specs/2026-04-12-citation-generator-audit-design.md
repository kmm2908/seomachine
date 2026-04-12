# Citation Generator & Listing Audit — Design Spec

**Date:** 2026-04-12
**Status:** Approved

---

## Context

Local SEO citation consistency is a significant ranking factor. Services like BrightLocal charge ongoing fees to manage citations across directories. This feature brings that capability in-house: automated creation for new clients and ongoing NAP audit for all clients, with no manual staff time for the sites that can be automated.

Two primary modes:
- **New clients:** Creation run — get them listed on every major UK citation site from scratch
- **Existing clients:** Audit run — check every listing, flag NAP mismatches, find duplicates, prioritise cleanup

Citation health integrates into the existing `/audit` report as a scored section (replaces the old NAP-only section).

---

## Site List & Tiers

~35 UK-focused citation sites, each assigned a tier and a priority score (1–10). The tier determines the automation method; the priority score controls report ordering and scoring weight.

### Tier 1 — Direct API (fully automated, read + write)
| Site | API | Priority |
|------|-----|----------|
| Google Business Profile | Existing GBP module | 10 |
| Bing Places | Bing Places API | 9 |
| Foursquare | Places API v3 | 7 |
| Yelp | Yelp Fusion API (read only; creation → Tier 4) | 7 |

### Tier 2 — DataForSEO Business Data (automated check; creation falls to Tier 3/4)
Facebook, TripAdvisor, Trustpilot, Apple Maps, Hotfrog, Bark.com

### Tier 3 — Playwright (automated check + attempted form submission)
Yell.com, Thomson Local, Scoot, 192.com, Cylex UK, FreeIndex, Brownbook, Misterwhat, Tupalo

### Tier 4 — Manual pack (check attempted; creation is human-assisted)
Apple Business Connect, Yelp (creation), Treatwell, Fresha, Nextdoor, Checkatrade

---

## Architecture

### File Structure

```
src/citations/
  run_citations.py          ← CLI entry point
  citation_manager.py       ← orchestrator (audit / create / full)

data_sources/modules/
  citation_checker.py       ← per-site presence check (all 4 tiers)
  citation_submitter.py     ← per-site creation (Tier 1, Tier 3, Tier 4 pack)
  citation_sites.py         ← master site list + per-site metadata

clients/[abbr]/citations/
  state.json                ← known listing URLs, last check date, submit status per site
  manual-pack.html          ← pre-filled submission kit for Tier 4 (and fallback) sites
```

### Data Structures

```python
@dataclass
class CitationSite:
    id: str
    name: str
    url: str
    tier: int                        # 1–4
    priority: int                    # 1–10, affects report ordering and score weight
    submission_url: str
    api_module: str | None           # Tier 1 only
    dataforseo_endpoint: str | None  # Tier 2 only
    search_url_template: str | None  # Tier 3: e.g. "https://www.yell.com/search?keywords={name}&location={city}"

@dataclass
class CitationResult:
    site: CitationSite
    status: str           # 'found' | 'not_found' | 'unknown' | 'duplicate'
    nap_match: bool | None
    listing_url: str | None
    issues: list[str]     # ['phone_mismatch', 'address_missing', 'duplicate_found']
    submit_status: str | None  # 'submitted' | 'manual_required' | 'pending_verification' | None

@dataclass
class CitationReport:
    abbr: str
    date: str
    results: list[CitationResult]
    score: int            # out of 20
    grade: str            # A–F
    total_sites: int
    found_count: int
    missing_count: int
    nap_issues: int
    duplicates: int
```

---

## Data Flow

### Audit Mode

1. Load business ground truth from `clients/[abbr]/config.json` (name, address, phone, hours, categories)
2. Load `state.json` — skip sites checked within last 30 days unless `--force` passed
3. For each due site: `citation_checker` checks presence and extracts NAP using tier method
4. Compare extracted NAP against config ground truth — populate `CitationResult.issues`
5. Roll up into `CitationReport` with score
6. Save updated `state.json`
7. Append citation section to audit report (if called from `/audit`)

### Creation Mode

1. Load `state.json` — identify sites with `status: not_found` or `submit_status: None`
2. For each missing site:
   - Tier 1 → API create/claim call
   - Tier 3 → Playwright form fill + submit
   - Tier 4 → append entry to `manual-pack.html`
3. Update `state.json` with `submit_status` result
4. Save `manual-pack.html` if any Tier 4 entries were written

### Full Mode (default)

Audit run → creation run on all `not_found` results → save outputs.

---

## Error Handling

| Tier | Failure | Behaviour |
|------|---------|-----------|
| 1 | API rate limit / error | Retry ×3 with backoff; fall back to Tier 2 check; mark `unknown` if both fail |
| 2 | No DataForSEO data for site | Mark `unknown` — does not count against score |
| 3 | CAPTCHA detected / form fails | Log failure; mark `submit_status: manual_required`; add to manual pack; check result still recorded |
| Any | Unhandled exception | Log and continue — single site failure never aborts the run |

The manual pack is always generated as a final fallback. No run ends with zero output.

---

## Manual Pack (`manual-pack.html`)

Self-contained HTML file — same pattern as the existing directions snippet. Contains:

- **NAP block at top** — exact copy-paste format for each site
- **Description block** — 150-word SEO-optimised description + 50-word short version
- **Hours block** — formatted for directory submission
- **Per-site sections (Tier 4 + any Tier 3 fallbacks):**
  - Direct submission URL as a clickable button
  - Pre-filled field values listed below
  - Checkbox to tick off when done

---

## Integration with `/audit`

The existing NAP section (15 pts, schema-only) is replaced by **NAP & Citations** (15 pts). Total remains 100 pts.

| Criterion | Points |
|-----------|--------|
| Present on 80%+ of priority sites | 6 |
| NAP consistent across all found listings | 5 |
| Zero duplicate listings | 2 |
| No critical sites missing (GBP, Bing, Yelp) | 2 |
| **Total** | **15** |

Overall audit total remains 100 pts. `collect_citations()` added to `collectors.py`; `CitationReport` added to `scoring.py`; citation section added to `report.py` HTML/markdown templates.

---

## CLI

```bash
python3 src/citations/run_citations.py --abbr gtm                  # full: audit + create missing
python3 src/citations/run_citations.py --abbr gtm --mode audit     # check only, no submissions
python3 src/citations/run_citations.py --abbr gtm --mode create    # create missing only
python3 src/citations/run_citations.py --abbr gtm --status         # citation status table
python3 src/citations/run_citations.py --abbr gtm --dry-run        # audit without submitting
python3 src/citations/run_citations.py --abbr gtm --force          # re-check all sites regardless of last_checked
```

Output:
```
→ Citations: 24/35 found | 3 NAP issues | 1 duplicate | score 14/20
  ✓ Google Business Profile — NAP match
  ✓ Bing Places — NAP match
  ✗ Yell.com — not found → submitted via Playwright
  ⚠ Thomson Local — found, phone mismatch
  ✎ Apple Business Connect — manual pack entry written
```

---

## State File (`state.json`)

```json
{
  "last_run": "2026-04-12",
  "sites": {
    "google_business_profile": {
      "status": "found",
      "listing_url": "https://g.co/...",
      "nap_match": true,
      "issues": [],
      "submit_status": null,
      "last_checked": "2026-04-12"
    },
    "yell": {
      "status": "not_found",
      "listing_url": null,
      "nap_match": null,
      "issues": [],
      "submit_status": "submitted",
      "last_checked": "2026-04-12"
    }
  }
}
```

---

## Testing

`tests/test_citations.py`:
- NAP comparison logic (exact match, normalised match, mismatch detection)
- Scoring calculation (coverage, consistency, duplicates, critical sites)
- Manual pack generation (correct fields, all sites present)
- `--dry-run` flag runs Playwright scrape without submitting

---

## Scheduling

Citation audit integrates into the existing `~/.seomachine-cron.sh` pattern. Recommended cadence: monthly check per client. Full creation run at client onboarding only.

```bash
# Example: monthly citation audit for GTM (1st of month, 08:00)
0 8 1 * * ~/.seomachine-cron.sh gtm citations
```
