# /refill-queue [abbr]

Check all client topic queues and refill any running low (≤3 pending topics).

## Usage
```
/refill-queue        — check all clients
/refill-queue gtb    — GTB queues only
```

## Steps

### 1 — Scan queue files

For each client (or the one specified), read every `*.json` file in `research/[abbr]/`. Count entries with `"status": "pending"`.

Report per queue:
```
gtb/thai-massage-queue.json:    2 pending  ⚠ LOW
gtb/stay-healthy-queue.json:    5 pending  ✓
gtb/yoga-stretching-queue.json: 0 pending  ✗ EMPTY
```

### 2 — Research new topics for each low/empty queue

Determine what type of content each queue needs, then research accordingly:

| Queue file | Research approach |
|---|---|
| `thai-massage-queue.json` | `/research-blog-topics [abbr]` — filter for massage-specific topics |
| `stay-healthy-queue.json` | Health/wellness angles relevant to client niche |
| `glasgow-news-queue.json` | Web search for current Glasgow news relevant to wellness/city life |
| `yoga-stretching-queue.json` | Yoga/stretching topics — or prompt: add a `/youtube-to-post` URL instead |
| `comp-alt-queue.json` | Check `clients/[abbr]/competitor-analysis.md` for unwritten alternatives |
| `problem-queue.json` | Compare existing problems against `clients/[abbr]/target-keywords.md` for gaps |
| `topic-queue.json` | `/research-blog-topics [abbr]` |

Target: enough topics for 4 weeks at the queue's cadence.

### 3 — Write new entries

Append accepted topics to the queue JSON file. Preserve the array and existing entries.

**Standard format:**
```json
{"topic": "Topic Title Here", "content_type": "blog", "status": "pending", "cadence": 7}
```

**GTB blog queues — always include `wp_category`:**
```json
{"topic": "Topic Title Here", "content_type": "blog", "status": "pending", "wp_category": "Thai Massage", "cadence": 7}
```

Category values per GTB queue:
- `thai-massage-queue.json` → `"Thai Massage"`
- `stay-healthy-queue.json` → `"Stay Healthy"`
- `glasgow-news-queue.json` → `"Glasgow News"` + `"content_type": "news"`
- `yoga-stretching-queue.json` → `"Yoga & Stretching"`

Validate the file is valid JSON after writing.

### 4 — Confirm

```
✓ Added 6 topics to research/gtb/thai-massage-queue.json
✓ Added 4 topics to research/gtb/yoga-stretching-queue.json
```

List each topic title added. Note: topics with `status: pending` will be picked up by the next cron run.
