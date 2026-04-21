# /fix-review [abbr]

Find and fix all quality-flagged posts (marked ★★★★★) across client WordPress sites.

## Usage
```
/fix-review        — scan all clients
/fix-review gtb    — scan GTB only
```

## Steps

### 1 — Find flagged posts

Read `logs/scheduled-publish-log.csv` for all `published_review` rows. Filter by abbr if given.

Then cross-check via WP-CLI to confirm ★ is still in the title (some may already be cleared):

```python
import json, subprocess
config = json.load(open(f'clients/{abbr}/config.json'))
ssh_host = f"{config['ssh']['user']}@{config['ssh']['host']}"
wp_path = config['ssh']['wp_path']
result = subprocess.run(
    ['ssh', ssh_host, f'wp post list --post_status=publish --s="★" --fields=ID,post_title,post_type --format=json --path={wp_path} --allow-root'],
    capture_output=True, text=True
)
```

Show: client, post ID, title, type, failure reason (from log notes column), wp-admin edit URL.

### 2 — Fix each post

Work through them one at a time. For each:

**a. Fetch the Elementor content:**
```bash
ssh [host] "wp post meta get [ID] _elementor_data --path=[wp_path] --allow-root"
```

**b. Parse the JSON.** Find the HTML widget containing the article body. Remove the review notice block — it looks like:
```html
<p>⚠️ <strong>Quality Review Required</strong>...★★★★★...</p>
```

**c. Fix the specific quality failure(s) from the log notes:**
- `paragraphs` — break any body paragraph longer than 3 sentences into two shorter ones
- `readability` — simplify the most complex sentences; reduce passive voice
- `ctas` — add at least 2 booking links in the body text (use the client's `booking_url` from config.json)
- `hook` — rewrite the opening paragraph with a stronger hook (problem/question/surprising fact)

Do NOT touch the FAQ section or schema block.

**d. Clean the title** — strip `★★★★★` prefix.

**e. Update via WP-CLI:**
```bash
ssh [host] "wp post update [ID] --post_title='[clean title]' --path=[wp_path] --allow-root"
ssh [host] "wp post meta update [ID] _elementor_data '[escaped json]' --path=[wp_path] --allow-root"
```

**f. Verify:**
```bash
ssh [host] "wp post get [ID] --field=post_status --path=[wp_path] --allow-root"
```
Must return `publish`.

### 3 — Purge cache

After all fixes for a client:
```bash
ssh [host] "wp eval 'sg_cachepress_purge_everything();' --path=[wp_path] --allow-root"
```

### 4 — Report

```
✓ Fixed N posts for [client]: [title 1], [title 2], ...
⚠ Could not fix [title]: [reason]
```
