# Project Status

Last updated: 2026-03-21 (session 6)

---

## Starting a New Session

Paste this as your opening message:

```
Read STATUS.md and pick up where we left off. Start with the first unchecked item under "Needs Testing", confirm what you're about to do, then proceed.
```

---

## What's Built and Working

### Project structure (new session 6)
- [x] All executable Python scripts moved to `src/` — `geo_batch_runner.py`, `republish_existing.py`, `fetch_elementor_template.py`, all `research_*.py`
- [x] Test scripts moved to `tests/` — `test_dataforseo.py`, `test_image_generation.py`
- [x] GCP service account key moved to `config/` and gitignored
- [x] All `ROOT` and `sys.path` references updated — scripts resolve project root as `parent.parent`
- [x] `seo_baseline_analysis.py`, `seo_bofu_rankings.py`, `seo_competitor_analysis.py` deleted — orphaned, overlapped with active research scripts

### Core batch system
- [x] `src/geo_batch_runner.py` — reads Google Sheet, generates content via Claude API, saves to `content/[abbr]/[type]/`
- [x] 5 content types with dispatch map (service, location, pillar, topical, blog) — `geo` type retired and merged into `location`
- [x] Per-client context loading from `clients/[abbr]/`
- [x] Rate limiting (65s between requests, 70s retry on 429)
- [x] Cost tracking written back to Sheet Column C
- [x] Summary email on batch completion
- [x] `--publish` flag for WordPress auto-publishing
- [x] `excerpt=address` passed on publish — topic from Sheet becomes hub display text automatically

### Client config system
- [x] `clients/gtm/config.json` — client config with WordPress block, `elementor_template_id: 16508`, and `content_type_map` for CPTs
- [x] `clients/gtm/` — context folder with brand-voice, seo-guidelines, internal-links-map, features, competitor-analysis, target-keywords, writing-examples
- [x] `clients/README.md` — schema documentation and onboarding guide

### Content agents (5 writers)
- [x] `service-page-writer.md`, `location-page-writer.md`, `pillar-page-writer.md`, `topical-writer.md`, `blog-post-writer.md`
- [x] **FAQ accordion** — all 5 agents output `<details>`/`<summary>` collapsible FAQ (no JS/CSS needed)
- [x] **Schema markup** — all 5 agents output `<!-- SCHEMA -->` block with JSON-LD `@graph` (primary type + FAQPage + LocalBusiness)

### SEO guidelines
- [x] Entity optimisation section added to `clients/gtm/seo-guidelines.md`
- [x] Entity rules explicitly override keyword density rules

### Research commands
- [x] `/research` — entity mapping now Step 1; output includes Entity Map section
- [x] `/research` — Step 0 social research added (Reddit/YouTube queries, pain points, user language, story seeds)
- [x] `/research` — Section Plan table added to brief output (heading, type, word target, CTA, hook per H2)
- [x] `/research-serp` — entity extraction step added after Python script

### Content quality gate (new session 6)
- [x] `run_quality_check()` in `geo_batch_runner.py` — runs after every article is written
- [x] `EngagementAnalyzer` — checks hook quality, sentence rhythm, CTA distribution, paragraph length (4 criteria, pass/fail)
- [x] `ReadabilityScorer` — Flesch reading ease, grade level, passive voice, sentence length
- [x] Output: `→ Quality: engagement 3/4 | readability 74/100 (B)  ⚠ fix: ctas`
- [x] Non-blocking — wrapped in try/except, never stops publishing

### WordPress publisher
- [x] `WordPressPublisher.from_config(wp_config)` — accepts credentials from client JSON
- [x] `upload_media()` — returns `(media_id, source_url)` tuple
- [x] `_upload_and_replace_images()` — uploads all local images, rewrites relative src to absolute WP URLs before creating draft
- [x] `_wrap_schema_block()` — wraps schema in Gutenberg `wp:html` block (non-Elementor path)
- [x] `publish_html_content()` — HTML publishing path; branches on Elementor vs plain; accepts `excerpt` param

### Elementor template injection
- [x] `src/fetch_elementor_template.py` — one-time CLI: fetches `elementor_library/{id}` from WP, saves to `clients/[abbr]/elementor-template.json`
- [x] `_inject_elementor()` — injects article HTML into HTML widget; strips first H2; appends schema script; fixes list spacing inline
- [x] `_find_html_widget()` — depth-first walk; matches "Paste HTML Here" marker, fallback to first HTML widget
- [x] `_create_elementor_page()` — POSTs to correct CPT endpoint with `_elementor_data` + `_elementor_edit_mode: builder` meta + excerpt
- [x] Auto-detected: if `clients/[abbr]/elementor-template.json` exists, Elementor path is used automatically
- [x] GTM template fetched and saved — `clients/gtm/elementor-template.json`

### WordPress Custom Post Types
- [x] `wordpress/seomachine.php` v2.2 — MU-plugin; must be in `wp-content/mu-plugins/` (not inside `plugins/`)
- [x] 5 CPTs registered: `seo_service`, `seo_location`, `seo_pillar`, `seo_topical`, `seo_blog`
- [x] All CPTs grouped under "SEO Content" parent menu in wp-admin
- [x] `seo_meta` REST field registered on all CPTs — Yoast-compatible meta keys, works without Yoast installed
- [x] Elementor filter — all 5 CPTs available in Elementor builder (must be enabled in Elementor → Settings first)
- [x] `content_type_map` in client config — batch runner resolves correct CPT from content type

### Hub page shortcode (new session 5)
- [x] `[seo_hub type="location"]` shortcode in `seomachine.php` — renders published posts as `<ul class="seo-hub-links">` with `<li><h3><a>` structure
- [x] Display text = post excerpt if set, otherwise post title (fallback)
- [x] Supports all 5 types: location, service, pillar, topical, blog
- [x] Sorted A–Z by title; auto-updates on publish/unpublish (WP_Query, status=publish only)
- [x] Must use Elementor **Shortcode widget** (not HTML widget) — HTML widget does not process shortcodes
- [x] CSS: `li h3 a { font-size: 0.8rem }` from Elementor Kit applies automatically — no custom CSS needed
- [x] Line-height for wrapped items: add `.elementor-shortcode .seo-hub-links h3 { line-height: 1.2; }` to site custom CSS if needed

### Republish script (new session 5)
- [x] `src/republish_existing.py` — re-publishes existing HTML files to WordPress without regenerating content
- [x] Derives excerpt from filename slug (e.g. `glasgow-central-station` → "Glasgow Central Station")
- [x] Supports `--abbr` and `--type` flags

### Image generation pipeline
- [x] `ImageGenerator` class — Gemini 3.1 Flash via Google AI Studio REST API
- [x] Keyword-rich filenames: `{base-slug}-banner.jpg`, `{heading-slug}.jpg`, `{base-slug}-faq.jpg`
- [x] Banner prompt fix — "Editorial spa photograph" + "No other people visible"
- [x] Location content type: banner = local area/street scene; section image = spa treatment scene
- [x] Image placement with alignment classes (banner: aligncenter, section: alignright, FAQ: alignleft)
- [x] Pillow centre-crop: banner to 1200×500, sections to 400×300
- [x] Image cost added to per-row cost in Google Sheet

### Output structure
- [x] `content/[abbr]/[type]/[slug]-[date]/[slug]-[date].html` — per-article folder

### End-to-end batch publishing (tested session 5)
- [x] 5 location + 2 service posts republished clean to correct CPTs (IDs 16637–16667)
- [x] CPT permalink routing confirmed working — `/location/[slug]/` resolves correctly
- [x] Elementor data saving correctly now that CPTs are enabled in Elementor settings
- [x] Hub shortcode displaying correct links and styling on live pages

---

## Needs Testing (Next Session)

### Priority 1 — Content quality checks
- [ ] Validate schema with Google Rich Results Test — FAQPage, Article/Service, LocalBusiness
- [ ] Check `seo_meta` REST field is writable — confirm SEO title/description/keyphrase saved on drafts
- [ ] Check FAQ accordion renders in browser — `<details>`/`<summary>` expands/collapses

### Priority 2 — Hub shortcode
- [ ] Publish a post and confirm it appears in hub list automatically (no manual step)
- [ ] Unpublish a post and confirm it disappears from hub list
- [ ] Check excerpt shows correctly for a post with manually-set excerpt vs title fallback

### Priority 3 — Batch runner edge cases
- [ ] Single blog row — check output lands in `content/gtm/blog/` and publishes to `seo_blog` CPT
- [ ] Invalid content type in Column E — verify clear error message

### Priority 4 — Slash commands
- [ ] `/research thai massage glasgow` — verify Social Research (Step 0) runs first, Entity Map appears as Section 1, Section Plan table in output
- [ ] `/research-serp "thai massage glasgow"` — verify entity extraction step runs
- [ ] `/write` — verify it loads from `clients/gtm/` context files (not `context/`)

### Priority 5 — Quality gate
- [ ] Run batch on a single row — confirm quality check line appears after "✓ Written"
- [ ] Trigger a failing engagement check (e.g. no CTAs) — confirm ⚠ fix label appears
- [ ] Confirm quality check failure does not block publishing (`--publish` still works)

---

## Still Needs Human Input

- [ ] `clients/gtm/seo-guidelines.md` — rewrite for GTM (still has Castos/podcast placeholder content)
- [ ] `clients/gtm/internal-links-map.md` — populate with actual GTM website URLs
- [ ] `clients/gtm/competitor-analysis.md` — populate with GTM competitors
- [ ] `clients/gtm/target-keywords.md` — populate with GTM priority keywords
- [ ] `clients/gtm/writing-examples.md` — add example GTM content to guide tone
- [ ] Google Sheet — add Column E (Content Type) dropdown with values: service, location, pillar, topical, blog
- [ ] Elementor template — delete built-in FAQ section (our content includes FAQ; template has duplicate)
- [ ] Existing posts (16637–16667) — set short excerpts manually in wp-admin for cleaner hub display (future posts will auto-set from Sheet topic)
- [ ] Hub section — set `line-height: 1.2` in Elementor site custom CSS if long titles wrap awkwardly

---

## Known Issues / Limitations

- The `/write`, `/article`, and other interactive slash commands still reference `@context/` paths rather than `@clients/gtm/`. Not multi-client aware.
- `clients/gtm/seo-guidelines.md` — entity optimisation section complete but rest still has Castos template content.
- Rate limit contention — batch runner competes with active Claude Code conversation on the same API key. Run batch when Claude Code is idle.
- Duplicate Finnieston post (ID 16642) — old bad batch run artefact, can be deleted from wp-admin.
- Media library accumulating duplicate images from repeated republish runs — consider cleaning up old uploads.

---

## Deferred / Future

- Multi-client Sheet support — currently one Sheet per project; future: Sheet per client or client column filtering
- FAQ accordion styling — `<details>`/`<summary>` uses browser-default arrow; can be styled with custom CSS in WordPress
- `/write` command entity-awareness — interactive write command doesn't yet follow entity-first research flow
- WordPress parent-page support — location pages should be child pages of their location/pillar parent
- Hub shortcode: consider adding a `limit` attribute and/or grouping by taxonomy for large link lists
