# /audit [abbr or URL]

Run a full SEO audit for a client or prospect and produce three outputs:
1. **Internal report** — `audits/[abbr]/[date]/audit-internal.md`
2. **Prospect PDF** — `audits/[abbr]/[date]/audit-prospect.pdf` (OMG branded, PAS framework)
3. **Pending queue** — `audits/[abbr]/[date]/pending-queue.json` (all items `status: pending`)

The PDF is emailed to `kmmsubs@gmail.com` on completion.

## Usage

```
/audit gtm           — audit an existing client (uses clients/gtm/config.json)
/audit sdy           — audit SDY
/audit https://...   — prospect audit (no client config needed)
```

## Steps

1. Determine mode:
   - If argument is a known abbreviation (2–4 chars, no dots), run as existing client
   - If argument looks like a URL (`https://...`), run as prospect audit
   - If no argument given, ask the user for an abbreviation or URL

2. For **prospect audits** without a config file:
   - Ask for business name if not provided
   - Run with `--url [url] --name "[name]"`

3. Run the audit (use a background agent for the main collection):
   ```
   python3 src/audit/run_audit.py --abbr [abbr]
   ```
   or
   ```
   python3 src/audit/run_audit.py --url [url] --name "[name]"
   ```

4. After the script completes, report the results to the user:
   - Overall score and grade
   - Top 3 findings per category
   - Location of output files
   - Confirm email was sent (or warn if it failed)

5. Ask: "Would you like to review the pending queue and move any items to active publishing?"
   - If yes: open `audits/[abbr]/[date]/pending-queue.json` and walk through each item
   - User approves which to activate → copy approved items to the appropriate queue file
     (e.g. `research/[abbr]/topic-queue.json`)

## Flags

- `--no-pdf` — skip PDF generation (produces HTML instead)
- `--no-email` — skip email delivery

## Output Files

| File | Description |
|------|-------------|
| `audit-internal.md` | Full raw data report — for internal use |
| `audit-prospect.html` | OMG-branded HTML (fallback if PDF fails) |
| `audit-prospect.pdf` | PDF version of prospect report |
| `pending-queue.json` | Content gap queue (all `status: pending`) |

## Prerequisites

Playwright must be installed for PDF generation:
```bash
pip install playwright
playwright install chromium
```

If not installed, the audit still runs — it saves HTML instead of PDF, and notes that
Playwright is missing.
