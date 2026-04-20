# Verification Checklist

Per-task verification steps. Run the relevant checks before handing back any completed task.
Surface results as a `✓ Verified:` block in the response. If a check fails: fix → re-verify → hand back.
If the failure reveals a new class of problem, add a rule to `docs/conventions.md`.

---

## WordPress Publish

```
✓ Verified: post [ID] at /[cpt]/[slug]/ returns 200, CPT = [type], Elementor JSON valid ([N] elements), cache purged
```

Checks:
- Post ID exists: `wp post get [ID] --fields=ID,post_status,post_type` via SSH or REST
- Correct CPT: post_type matches expected (`seo_service`, `seo_location`, `post`, etc.)
- Page returns 200: `curl -s -o /dev/null -w "%{http_code}" https://[domain]/[cpt]/[slug]/`
- Elementor JSON parseable: `wp post meta get [ID] _elementor_data` — should be valid JSON, not empty
- Cache purged: `→ Cache: purged` in console output (or trigger manually if missing)

---

## Script Change

```
✓ Verified: [script] ran clean — [N] items processed, no errors, log entry written
```

Checks:
- Run the script (or `--dry-run` if available) and confirm no Python exceptions
- Show the last few lines of output including any cost/status summary
- For publisher scripts: confirm log entry written to `logs/scheduled-publish-log.csv`
- For batch runner: confirm Google Sheet status updated correctly

---

## Config Change (config.json)

```
✓ Verified: config.json valid JSON, [script] imports cleanly
```

Checks:
- `python3 -c "import json; json.load(open('clients/[abbr]/config.json'))"` — no error
- Run a lightweight script that imports the config: `python3 src/content/publish_scheduled.py --abbr [abbr] --status`
- Confirm no KeyError or missing-field warnings in output

---

## Plugin or CSS Deploy (seomachine.php / seomachine-hub-v2.css)

```
✓ Verified: GitHub Actions job green, file present on [domain] server
```

Checks:
- GitHub Actions: check `.github/workflows/deploy-plugin.yml` run — all 3 jobs green
- File present on server: `ssh [host] "ls -la [wp_path]/wp-content/mu-plugins/seomachine.php"`
- If CSS changed: confirm new filename is referenced in PHP enqueue AND deploy workflow

---

## HTML / Content Change

```
✓ Verified: [URL] returns 200, H1 present, schema <script> present
```

Checks:
- Page returns 200: `curl -s -o /dev/null -w "%{http_code}" [URL]`
- H1 present: `curl -s [URL] | grep -o '<h1[^>]*>.*</h1>'`
- Schema script present: `curl -s [URL] | grep -o 'application/ld+json'`
- If Elementor: Elementor CSS files present (no 404 on stylesheet links)

---

## Queue Change (topic-queue.json / comp-alt-queue.json etc.)

```
✓ Verified: queue JSON valid, --status output clean, [N] pending topics
```

Checks:
- `python3 -c "import json; json.load(open('research/[abbr]/[queue].json'))"` — no error
- `python3 src/content/publish_scheduled.py --abbr [abbr] --queue [queue] --status` — table renders without error
- Confirm status values are valid (`pending`, `published`, `failed`, `review_required`)

---

## CLAUDE.md / docs Change

```
✓ Verified: all @file references exist, no broken paths
```

Checks:
- For every file referenced with `@path` or prose path, confirm the file exists
- `python3 src/content/publish_scheduled.py --abbr gtb --status` — confirm pipeline still works with updated context
