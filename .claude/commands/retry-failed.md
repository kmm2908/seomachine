# /retry-failed [abbr]

Find failed publish attempts in the log and retry them with corrected settings.

## Usage
```
/retry-failed        — scan all clients (last 30 days)
/retry-failed gtb    — GTB only
```

## Steps

### 1 — Find failed rows

Read `logs/scheduled-publish-log.csv`. Filter rows where `status == failed` in the past 30 days. Skip `queue_empty` rows — those are not failures.

Show: date | client | topic | error message.

### 2 — Diagnose each failure

| Error pattern | Cause | Fix |
|---|---|---|
| `400 Bad Request /wp/v2/categories` | SiteGround blocking REST categories endpoint | Ensure `ssh.wp_path` is set in config — routes through WP-CLI |
| `400 Bad Request /wp/v2/posts` | SiteGround bot protection on REST | Same — need WP-CLI path |
| `401` / `403` | App password rejected or expired | Check `clients/[abbr]/config.json` credentials; regenerate app password in WP |
| `SSH connection refused / timeout` | Network issue or SSH key problem | Check `~/.ssh/seomachine_deploy` key; retry |
| `500 Server Error` | Transient WP server issue | Retry — likely to succeed |
| `Quality gate exhausted` | Content failed after 2 rewrites | Regenerate: delete content file, reset queue to pending, re-run |

### 3 — Fix and retry

For each failure:

**a. Locate the queue entry:**
Search `research/[abbr]/*.json` for the topic name.

**b. Fix the root cause** (credentials, config, SSH key) if needed before retrying.

**c. Reset the queue entry to pending:**
Change `"status": "failed"` → `"status": "pending"` in the queue JSON.

**d. Re-run immediately:**
```bash
python3 src/content/publish_scheduled.py --abbr [abbr] --queue [queue-file-name]
```

Don't wait for the next cron — run it now to confirm the fix worked.

### 4 — Report outcome

**Success:**
```
✓ [Topic] — republished as post [ID] on [site]
```

**Failed again:**
```
✗ [Topic] — failed again: [error]
  Recommended: [manual wp-admin publish / check credentials / contact host]
```

Do not auto-retry more than once. If a second attempt fails, stop and report — do not loop.
