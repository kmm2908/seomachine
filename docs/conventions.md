# Conventions

Rules derived from real problems solved in this project. Read before any WordPress or publishing work.
Added to via `/wrap` at the end of each session — any new class of problem gets recorded here.

---

## Use WP-CLI over SSH, never direct REST, on SiteGround
**Why:** SiteGround's CDN returns 202 bot-challenge pages for unauthenticated REST requests from non-browser IPs. SSH port forwarding is also blocked (`AllowTcpForwarding no`), so tunnelling is not an option.
**How to apply:** When `ssh.wp_path` is set in a client's `config.json`, `WordPressPublisher` automatically routes all publishing through WP-CLI over SSH. Never attempt direct REST publish to SiteGround without this path set.

---

## CSS cache-busting requires a filename rename, not a version bump
**Why:** SG Optimizer strips `?ver=` query strings from static asset URLs, making `wp_enqueue_style` version parameters completely ineffective.
**How to apply:** When a CSS change needs to reach users immediately, rename the file (e.g. `seomachine-hub.css` → `seomachine-hub-v2.css`) and update both the PHP `wp_enqueue_style` call and the GitHub Actions deploy workflow to reference the new filename.

---

## Wrap Elementor JSON with wp_slash() before update_post_meta()
**Why:** WordPress internally calls `wp_unslash()` on meta values, which strips backslashes and corrupts Elementor JSON (breaks all `\"` escaped quotes in the JSON string).
**How to apply:** In `_publish_via_wpcli()`, always call `wp_slash()` on the Elementor JSON string before passing it to `update_post_meta()` via `wp eval`.

---

## Always pass queue_name explicitly to save_queue()
**Why:** `save_queue()` has a default of `topic-queue.json`. When called from an exception handler without `queue_name`, it silently writes the failed/updated status to the wrong file, leaving the actual queue unchanged and causing topics to be retried indefinitely.
**How to apply:** Every call to `save_queue(abbr, queue)` in `publish_scheduled.py` must include `queue_name=queue_name`. Check exception handlers specifically — they're the most common omission point.

---

## wp elementor flush-css does not regenerate CSS, only deletes it
**Why:** The WP-CLI command `wp elementor flush-css` deletes generated CSS files but does NOT trigger regeneration. Pages will load without Elementor styles until the CSS is rebuilt on first page load, or until explicitly regenerated.
**How to apply:** After flushing CSS (e.g. after a plugin update), regenerate by running `wp eval` with a loop over all published Elementor posts calling `Elementor\Core\Files\CSS\Post::create($id)->update()`. Never assume flush alone is sufficient.

---

## Filter non-HTML content types before running detect_issues() in the crawler
**Why:** `/wp-sitemap.xml` is crawled as a page and triggers a false "Missing H1" warning because it returns XML, not HTML. The issue detector has no content-type awareness.
**How to apply:** In `detect_issues()` in `crawler.py`, skip H1/title/meta checks for pages where `content_type` does not start with `text/html`. This fix is currently deferred — be aware that sitemap URLs in crawl reports will show false H1 warnings until resolved.

---

## Plugin must be in wp-content/mu-plugins/ (plural), not mu-plugin/
**Why:** SiteGround has both a `mu-plugin/` (singular) folder which is display-only and a `mu-plugins/` (plural) folder which WordPress actually auto-loads. Deploying to the wrong one silently fails — the plugin appears in the UI but never runs.
**How to apply:** All GitHub Actions deploy jobs target `wp-content/mu-plugins/seomachine.php`. Verify the path when adding new hosting accounts.

---

## [seo_hub] shortcode must use Elementor Shortcode widget, not HTML widget
**Why:** The Elementor HTML widget does not process WordPress shortcodes — it outputs them as literal text.
**How to apply:** Always insert `[seo_hub type="X"]` via the Elementor Shortcode widget. If a hub list shows as plain text on the frontend, this is the cause.

---

## MCP tools cost tokens even when deferred — audit per project
**Why:** Even deferred MCP tool definitions appear in the system prompt at session start. 60+ tool definitions loading for MCPs that a project never uses (browsermcp, Gmail, Google Calendar, Google Drive, claudeus-wp-mcp) wastes context on every message.
**How to apply:** Add `deniedMcpServers` (for user-scoped MCP servers) and `enabledPlugins: {plugin: false}` (for plugin MCPs) to the project's `.claude/settings.json`. Audit by running `claude mcp list` and cross-referencing against the project's source code. Exception: keep Playwright MCP enabled for UI projects that use it for interactive visual QA (not just Python playwright in scripts).

---

## Use Python to write files when paths contain spaces
**Why:** `curl -o /path/with spaces/file.json` silently writes 0 bytes on macOS — the shell splits the path and curl discards it without erroring.
**How to apply:** Whenever saving a file to a path that may contain spaces (common in `/Volumes/Ext Data/...`), use Python: `pathlib.Path('the path').write_bytes(data)` or `write_text(...)`. This applies to curl saves, file copies, and any Bash redirection to such paths.

---

## Remote scheduled agents cannot access the local filesystem
**Why:** Scheduled triggers run in Anthropic's cloud infrastructure with no access to `/Volumes/`, `~/.claude/`, or any local paths.
**How to apply:** Remote agent prompts must use GitHub repos as sources (clone with `--depth=1`) and cloud MCP connectors (Gmail, Google Drive) for I/O. Never reference local file paths or local scripts in trigger prompts.

---

## Use wp eval-file for namespaced PHP classes, never wp eval inline

**Why:** Passing `wp eval 'Namespace\Sub\Class::method()'` via SSH fails with "Parse error: unexpected token '\'" — the backslash in the namespace is interpreted by the shell before it reaches WP-CLI. Even with escaping, inline PHP strings over SSH are fragile.
**How to apply:** Write the PHP to a local temp file (`/tmp/foo.php`) and run it with `wp eval-file /tmp/foo.php --allow-root` over SSH. This applies any time WP-CLI PHP calls use `\Elementor\`, `\WP_Query`, or any other namespaced class.

---

## GBP API: quota approval ≠ APIs enabled; CIDs ≠ resource names
**Why:** The GBP quota approval email (from Google Support) only grants QPM quota. The individual service APIs (`mybusinessaccountmanagement.googleapis.com`, `mybusinessbusinessinformation.googleapis.com`, etc.) must be enabled separately in Cloud Console. Additionally, Google Maps CIDs (from `?cid=` URLs or GBP Manager listing URLs) are a completely different ID space from the GBP API resource names (`accounts/{id}/locations/{id}`). Using CIDs directly in API calls returns 404. The correct flow: enable Account Management API → it returns resource names → use those for Business Information API calls.
**How to apply:** The module now uses `_discover_managed_locations()` to build a `{place_id: resource_name}` map via Account Management API. Store the Google Maps Place ID (`ChIJ...`) in client config as `gbp_place_id`. Never use numeric CIDs as GBP API identifiers. If Account Management API is disabled, the module logs the exact console URL to enable it and returns empty dict gracefully.

---

## GBP service account requires explicit manager invitation acceptance
**Why:** Adding a service account as Manager in GBP Manager sends an invitation that must be accepted — it is not auto-granted. Until accepted, all API calls return 404/empty as if the location doesn't exist. There is no error indicating "invitation pending" vs "no access".
**How to apply:** After adding a service account in GBP Manager, go back to Settings → Managers on the same business and confirm the service account appears as an active manager (not pending). If it still shows as pending invitation, re-send or try a different access level.

---

## GBP auth: use OAuth2 owner credentials, not service account

**Why:** Service accounts in Google's UNVERIFIED/NOT_VETTED state cannot accept GBP Manager invitations — they fail with `FAILED_PRECONDITION` (400) silently. There is no error distinguishing "invitation pending" from "no access". Since `kmmsubs@gmail.com` is Primary Owner of all 3 GBP locations, OAuth2 user credentials bypass invitations entirely and work without any GBP Manager setup.
**How to apply:** GBP module auto-uses OAuth2 when `config/gbp-oauth-client.json` + `config/gbp-oauth-token.json` exist. Service account remains as fallback. To re-generate a token, run `src/tools/gbp_auth.py` (or equivalent `InstalledAppFlow.run_local_server()`). If OAuth fails, verify the client file has `"installed"` as top-level key (Desktop app) not `"web"`.

---

## GBP OAuth2 client must be Desktop app type, not Web app

**Why:** `InstalledAppFlow.run_local_server()` generates a random-port redirect URI (`http://localhost:PORT/`). Web app OAuth clients require each redirect URI to be explicitly registered — you'd need every possible port. Desktop app clients (type: `installed`) allow any `localhost` URI automatically and require no redirect URI configuration.
**How to apply:** When creating an OAuth2 client in Cloud Console for CLI/script use, always choose "Desktop app". The downloaded JSON has `"installed"` as the top-level key. If you see `redirect_uri_mismatch` in a local flow, check the client type first.

---

## GBP Reviews API is fully retired — do not attempt to enable it

**Why:** Both `mybusiness.googleapis.com/v4` and `mybusinessreviews.googleapis.com/v1` are permanently retired for self-service developers. They cannot be enabled in Cloud Console and will not return data regardless of OAuth scope or quota approval.
**How to apply:** `collect_reviews()` returns an informational message (not 0/15) so audits don't appear misconfigured. Do not add these URLs to any API-enable attempt. If reviews data is needed, consider DataForSEO or embedding `aggregateRating` in `LocalBusiness` schema from a manually maintained count.

---

## wp rewrite flush required after bulk WP-CLI post status changes

**Why:** `wp post update --post_status=publish` (bulk) does not trigger WordPress rewrite rule flushing. CPT pages with custom permalink structures return 404 (with `error404` CSS class in the body) until rewrites are regenerated.
**How to apply:** After any bulk WP-CLI status change on CPT posts, always run `wp rewrite flush --hard` over SSH before testing or serving the pages.

---

## Apify `run-sync-get-dataset-items` returns 201, not 200
**Why:** The Apify synchronous run endpoint creates a run object (HTTP 201 Created), not a simple data fetch (HTTP 200 OK). Treating 201 as a failure means the call always silently returns None even when the data is valid.
**How to apply:** When checking Apify response codes, use `status_code in (200, 201)`. This applies to any call to `https://api.apify.com/v2/acts/{id}/run-sync-get-dataset-items`.

---

## Google Maps reviews panel is blocked for all headless browsers
**Why:** Google Maps shows a "limited view" to any automated browser — headless Chromium, headless Chrome, or any browser with the automation fingerprint exposed. The reviews panel is restricted to authenticated users, making DOM scraping and screenshot approaches equally unviable.
**How to apply:** Never attempt to scrape Google Maps reviews via Playwright or similar. Use Apify (`compass~google-maps-reviews-scraper`) or another authenticated scraping service. The `responseFromOwnerText` field on each result is null/string and gives response rate directly.

---

## `except Exception: pass` in collectors silently swallows TypeError from wrong kwargs
**Why:** The Step A/B/C pattern in `collect_reviews()` uses broad exception suppression so a single source failure doesn't break the audit. But this also hides bugs like passing `known_review_count=` to a function that only accepts `max_reviews=`, causing all downstream data to be silently missing.
**How to apply:** When a Step A/B/C collector block produces None/zero for a metric that should have data, test the step in isolation first: `python3 -c "from collectors import collect_reviews; ..."` before running the full audit. Also run the module function directly to confirm it returns data.

---

## Python 3.13 MagicMock no longer supports comparison operators on subscript results

**Why:** In Python 3.13, `MagicMock.__le__`, `__ge__`, `__lt__`, `__gt__` return `NotImplemented` by default (changed from returning a truthy `MagicMock`). Accessing a subscript of a `MagicMock` (e.g. `mock_result['key']`) returns a child `MagicMock`, and comparing it to an int (e.g. `mock_result['key'] <= 3`) raises `TypeError: '<=' not supported between instances of 'MagicMock' and 'int'`. This is silent on 3.11/3.12 but hard-fails on 3.13.
**How to apply:** In any test that mocks a function returning a dict and the code under test performs arithmetic comparisons on its values, always use `side_effect` returning an explicit dict (e.g. `mock.return_value.analyze.side_effect = [{'key': 5}, {'key': 0}]`) rather than relying on auto-subscript MagicMock returns. This applies to `_analyze_ctas()`, `_analyze_paragraphs()`, and any other internal analyzer helpers in `quality_gate.py` tests.

---

## Backfill `competitor_gaps_run: true` in citation state files created before session 67
**Why:** `CitationState._load()` returns `competitor_gaps_run: False` when the key is absent (older files pre-date the feature). This causes `run_audit.py` to fire the full citation gap analysis (115 DataForSEO SERP calls, ~25 min) on every single audit run rather than just the first.
**How to apply:** When running an audit against a client whose `clients/{abbr}/citations/state.json` was created before session 67 (2026-04-21), first check whether the key exists: `python3 -c "import json,pathlib; d=json.loads(pathlib.Path('clients/{abbr}/citations/state.json').read_text()); print(d.get('competitor_gaps_run', 'MISSING'))"`. If missing or False and gap analysis has already run, set it to true before starting the audit.
