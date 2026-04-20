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
