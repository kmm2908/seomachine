# /weekly-check

Monday morning health check across all clients — publishing activity, queue status, failures, costs.

## Usage
`/weekly-check`

## Steps

### 1 — Publishing digest (last 7 days)

Read `logs/scheduled-publish-log.csv`. Filter rows from the past 7 days.

Per client, show:
- Posts published (clean)
- Posts flagged for review (`published_review`) — list titles + failure reasons
- Failed publishes — list topics + error
- Days with `queue_empty` — these are missed publishing slots
- Cost subtotal

### 2 — Outstanding review posts

From the log, find all `published_review` rows. Cross-check via WP-CLI for each client with SSH config to confirm ★ is still in the post title:

```bash
ssh [host] "wp post list --post_status=publish --s='★' --fields=ID,post_title --format=json --path=[wp_path] --allow-root"
```

List: client | title | failure reason | wp-admin URL.

### 3 — Queue status

For every queue JSON file across all clients, count `"status": "pending"` entries.

Flag thresholds:
- `0` → ✗ EMPTY — cron will find nothing to publish
- `1–3` → ⚠ LOW — will run out within the week
- `4+` → ✓ OK

### 4 — Cron health (GTB schedule)

Expected GTB runs per week:
- Mon → thai-massage-queue.json
- Tue → stay-healthy-queue.json
- Wed → glasgow-news-queue.json
- Thu → thai-massage-queue.json
- Fri → yoga-stretching-queue.json

Check the log for entries from each expected day. Flag any day with no entry or a `queue_empty` for the relevant queue.

### 5 — Cost summary

| Client | Posts | Cost |
|--------|-------|------|
| GTB    | N     | $X.XX |
| GTM    | N     | $X.XX |
| SDY    | N     | $X.XX |
| **Total** | N | **$X.XX** |

Compare to same period last week if data is available.

### 6 — Action list

Close with a prioritised list of what needs doing today:

```
Priority actions:
1. /fix-review gtb       — 3 posts outstanding (paragraphs, readability)
2. /retry-failed gtb     — Thai Yoga Massage failed Apr 17
3. /refill-queue gtb     — thai-massage-queue LOW (2 pending)
4. /youtube-to-post URL  — yoga slot empty, needs a video this week
```

Only include items that are actually needed.
