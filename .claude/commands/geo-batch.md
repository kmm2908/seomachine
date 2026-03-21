# Content Batch Command

Run batch content generation across multiple items from a Google Sheet, tracking progress and status back to the sheet automatically. Supports all content types: service, location, pillar, topical, blog.

## Usage

`/geo-batch` — process all items queued as `Write Now` from the configured Google Sheet

`/geo-batch [A2:E10]` — process only a specific range (useful for partial runs or testing)

`python3 geo_batch_runner.py --publish` — also publish each generated file to WordPress as a draft

---

## What This Command Does

1. Reads items from a Google Sheet where Column B = `Write Now`
2. For each item, selects the correct content agent based on Column E (content type)
3. Generates content using the appropriate agent and client context
4. Saves to `content/[abbr]/[type]/[slug]-[date].md`
5. Updates each row's Column B to `DONE` immediately after completion
6. Optionally publishes each file to WordPress as a draft (`--publish` flag)
7. Reports progress as it goes
8. Sends a single summary email when the full batch is complete

---

## Setup Requirements

The Google Sheet must be shared with the service account email from `credentials/ga4-credentials.json` with **Editor** access.

Add to `.env` at the project root:
```
GEO_LOCATIONS_SHEET_ID=<the sheet ID from the Google Sheets URL>
GEO_EMAIL_SMTP_HOST=smtp.gmail.com
GEO_EMAIL_SMTP_PORT=587
GEO_EMAIL_SMTP_USER=you@example.com
GEO_EMAIL_SMTP_PASS=your-app-password
GEO_EMAIL_FROM=you@example.com
GEO_EMAIL_TO=recipient1@example.com,recipient2@example.com
```

The Sheet ID is the long string in the URL:
`https://docs.google.com/spreadsheets/d/[THIS_PART]/edit`

### Google Sheet Format

| Column A | Column B | Column C | Column D | Column E |
|----------|----------|----------|----------|----------|
| **Location / Topic** | **Status** | **Cost** | **Business** | **Content Type** |
| Byres Road Glasgow G12 | Write Now | | GTM | location |
| Thai Massage Glasgow | Write Now | | GTM | service |
| 5 Benefits of Deep Tissue Massage | Write Now | | GTM | blog |
| Merchant City Glasgow G1 | DONE | $0.43 | GTM | location |
| Sauchiehall Street | pause | | GTM | location |

**Column B dropdown values:**
- `Write Now` — queue this item for the next batch run
- `pause` — skip this item without removing it
- `DONE` — content has been written, skip permanently

**Column C (Cost):** Written automatically by the script after each article is generated (e.g. `$0.43`). Do not edit manually.

**Column D (Business):** The client abbreviation — must match a file in `clients/` (e.g. `GTM` → `clients/gtm.json`). Add this as a dropdown in the Sheet to prevent typos.

**Column E (Content Type):** Controls which agent and writing rules are used. Valid values:

| Value | Agent | Word Count | Use for |
|-------|-------|------------|---------|
| `service` | service-page-writer | 400-600 | Individual treatment or service pages |
| `location` | location-page-writer | 450+ | District, neighbourhood, or postcode-level location pages |
| `pillar` | pillar-page-writer | 700-1000 | GBP category landing pages (hub pages) |
| `topical` | topical-writer | 600-1000 | Informational/question-based articles |
| `blog` | blog-post-writer | 600-1200 | Conversational blog posts |

If Column E is empty, defaults to `blog`.

Row 1 is the header row (skipped automatically). Set a row back to `Write Now` to re-queue it.

---

## Running the Batch

The batch is run directly via Python (not as a slash command):

```bash
# Process all queued rows
python3 geo_batch_runner.py

# Process a specific range
python3 geo_batch_runner.py A2:E5

# Process and publish to WordPress
python3 geo_batch_runner.py --publish

# Specific range + publish
python3 geo_batch_runner.py A2:E5 --publish
```

---

## Output Location

Files are saved to `content/[abbreviation]/[type]/[slug]-[date].md`

Examples:
```
content/gtm/geo/byres-road-g12-2026-03-12.md
content/gtm/service/thai-massage-glasgow-2026-03-12.md
content/gtm/blog/5-benefits-deep-tissue-2026-03-12.md
```

---

## Failure Handling

If an item fails (research returns nothing, write fails, unknown content type, etc.):
- The Sheet is **not** updated — the row stays as `Write Now` and retries on the next run
- The failure is logged: `[3/8] ✗ Failed: Merchant City G1 — research returned no results`
- The batch continues with the next item

---

## Tips

- **Test first**: Run `python3 geo_batch_runner.py A2:E3` to process just 2 items before a full batch
- **Interruptions**: Re-run the script — rows already marked `DONE` are skipped automatically
- **Large batches**: For 20+ items, consider running in segments to review quality between runs
- **Re-queue an item**: Set Column B back to `Write Now` to generate fresh content
- **WordPress publishing**: Add `"wordpress": {...}` to the client JSON and run with `--publish`
- **Rate limits**: The script sleeps 65 seconds between API calls to avoid rate limiting
