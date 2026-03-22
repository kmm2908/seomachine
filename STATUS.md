# Project Status

Last updated: 2026-03-22 (session 9 — SDY client onboarded + seomachine.php Elementor auto-enable fix)

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
- [x] Paragraph preservation fix (session 7) — `</p>` converted to `\n\n` before stripping HTML so `ReadabilityScorer` correctly detects paragraph count (was returning 1 paragraph for all content)

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

### Competitor research script (new session 8)
- [x] `src/research_competitors.py` — standalone script: geocodes client area via Nominatim, pulls top 10 map pack + top 10 organic from DataForSEO, scrapes competitor sites, extracts structured profiles via Claude Haiku, writes `clients/[abbr]/competitor-analysis.md`
- [x] Geocoding fix — strips "City Centre" / "Town Centre" etc. before Nominatim query (bare city name geocodes correctly)
- [x] Map pack approach — uses `location_name` (e.g. `"Glasgow,Scotland,United Kingdom"`) instead of coordinates; `keyword_prefix` only (no city in keyword) for better map results
- [x] `dataforseo.get_maps_pack()` — updated to accept both `location_name` and `location_coordinate`
- [x] Integrated into `/new-client` workflow as Step 5 — competitor-analysis.md auto-populated for every new client
- [x] `clients/gtm/competitor-analysis.md` — fully populated: 10 map pack results (GTM at #9), 8 organic competitors, 15 sites profiled

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

### Schema quality improvements (session 6)
- [x] Google Rich Results Test — 15 valid items detected on live location page (FAQPage, Article, LocalBusiness, Organization, Review snippets)
- [x] Non-critical issues identified and fixed in all 5 agent schema templates:
  - `author`/`publisher` changed from `LocalBusiness` to `Organization` (removes telephone/address/priceRange requirements on nested objects)
  - `url` added to `author`/`publisher` Organization nodes
  - `image: [BANNER_IMAGE_URL]` added to Article/BlogPosting/Service nodes (injected from banner after upload)
  - `telephone`, `priceRange`, `image` tokens added to main `LocalBusiness` node in all agents
  - `publisher` added to pillar page `WebPage` node
- [x] `datePublished` format fixed — was `YYYY-MM-DD`, now full ISO 8601 `YYYY-MM-DDT12:00:00+00:00`
- [x] `clients/gtm/config.json` — `schema` block added with `price_range` and `logo_url`
- [x] Batch runner — replaces `[BUSINESS_PHONE]`, `[BUSINESS_URL]`, `[BUSINESS_PRICE_RANGE]`, `[BUSINESS_LOGO]` tokens at publish time
- [x] `WordPressPublisher` — replaces `[BANNER_IMAGE_URL]` with actual WP media URL after image upload
- [x] `.claude/settings.json` created for project — `bypassPermissions` mode; all Playwright MCP tools added to global allow list

### SDY client onboarding (session 9)
- [x] `clients/sdy/` created — config.json, brand-voice.md, features.md, seo-guidelines.md (clean, not Castos template), target-keywords.md, internal-links-map.md, competitor-analysis.md, writing-examples.md
- [x] `clients/sdy/config.json` — `wordpress` block points to local (`https://sdy.local`); `wordpress_live` block stores live credentials for Phase 2 swap
- [x] `seomachine.php` updated — added `option_elementor_cpt_support` + `default_option_elementor_cpt_support` filters; CPTs now auto-enabled in Elementor without manual checkbox step
- [x] Deployed to SDY local (`~/Local Sites/Sdy/app/public/wp-content/mu-plugins/`)
- [x] `research_competitors.py --abbr sdy` run — 7 organic competitors profiled, map pack pending (keyword tuning needed)
- [x] GTM local site deleted — GTM is live-only from session 9 onwards

### End-to-end batch publishing (tested session 5)
- [x] 5 location + 2 service posts republished clean to correct CPTs (IDs 16637–16667)
- [x] CPT permalink routing confirmed working — `/location/[slug]/` resolves correctly
- [x] Elementor data saving correctly now that CPTs are enabled in Elementor settings
- [x] Hub shortcode displaying correct links and styling on live pages

---

## Needs Testing (Next Session)

### Priority 1 — Content quality checks
- [x] Validate schema with Google Rich Results Test — 15 valid items; non-critical issues identified and fixed in agents + batch runner
- [x] Check `seo_meta` REST field is writable — confirmed all 3 fields (seo_title, meta_description, focus_keyphrase) write and read back correctly via REST API
- [x] Check FAQ accordion renders in browser — `<details>`/`<summary>` expands/collapses

### Priority 2 — Hub shortcode
- [x] Publish a post and confirm it appears in hub list automatically (no manual step)
- [x] Unpublish a post and confirm it disappears from hub list
- [x] Check excerpt shows correctly for a post with manually-set excerpt vs title fallback

### Priority 3 — Batch runner edge cases
- [x] Single blog row — check output lands in `content/gtm/blog/` and publishes to `seo_blog` CPT
- [x] Invalid content type in Column E — verify clear error message

### Priority 4 — Slash commands
- [x] `/research thai massage glasgow` — Social Research Step 0 confirmed first; Entity Map as Section 1; Section Plan table in output — all present in command file
- [x] `/research-serp "thai massage glasgow"` — entity extraction step confirmed in command file (Step 2)
- [x] `/write` — verify it loads from `clients/gtm/` context files (not `context/`) — fixed: updated write.md to use @clients/gtm/ paths

### Priority 5 — Quality gate
- [x] Run batch on a single row — confirm quality check line appears after "✓ Written" — confirmed in code (line 507, called after ✓ Written print)
- [x] Trigger a failing engagement check (e.g. no CTAs) — confirm ⚠ fix label appears — confirmed: engagement 3/4 ⚠ fix: ctas on location content
- [x] Confirm quality check failure does not block publishing (`--publish` still works) — confirmed: run_quality_check() is try/except wrapped, publish block runs independently

---

## Client: SDY (Serendipity Massage Therapy & Wellness)

New client added 2026-03-21. Brand-new WordPress site, same stack as GTM (Elementor + Hello theme).
GBP applied for but not yet verified. Abbreviation: `SDY`.

### Deployment Plan

**Rule: local for setup/design, live for all batch runner content.**
Reason: caching on the live front-end doesn't affect the REST API. Running content against two environments causes DB divergence. Push local → live once, then stay on live for all publishing.

#### Phase 1 — Local setup (in progress)
- [x] Get local site URL and credentials — added to config.json (`wordpress` = local, `wordpress_live` = live)
- [x] Deploy `wordpress/seomachine.php` to local `wp-content/mu-plugins/`
- [x] Confirm 5 CPTs appear via REST API (`seo_service`, `seo_location`, `seo_pillar`, `seo_topical`, `seo_blog`)
- [x] Elementor CPTs auto-enabled via `option_elementor_cpt_support` filter — confirmed all 5 showing in Elementor → Settings
- [ ] Build location page template in Elementor library (in progress — user building)
- [ ] Get template ID and run `python3 src/fetch_elementor_template.py sdy`

#### Phase 2 — Push to live
- [ ] Export local DB, import to live server
- [ ] Confirm seomachine.php is in `wp-content/mu-plugins/` on live (or redeploy)
- [ ] Confirm CPTs and Elementor settings survived the push
- [ ] Run `python3 src/fetch_elementor_template.py sdy` against **live** URL
- [ ] Update `clients/sdy/config.json` with live `elementor_template_id`

#### Phase 3 — Content (after Phase 2)
- [ ] Add `SDY` to Column D dropdown in Google Sheet
- [ ] Add Column E (Content Type) dropdown if not already present
- [ ] Populate `clients/sdy/internal-links-map.md` with confirmed service page URLs
- [ ] Add writing examples to `clients/sdy/writing-examples.md` from live site
- [ ] Test batch on one row: `python3 src/geo_batch_runner.py A2:E3 --publish`
- [ ] Verify content lands in correct CPT with Elementor template

### Still Needs Human Input (SDY)
- [x] Local WP URL and credentials — in config.json (`wordpress` block = local, `wordpress_live` = live)
- [ ] `clients/sdy/internal-links-map.md` — confirm service page URLs on live site
- [ ] `clients/sdy/writing-examples.md` — pull 2–3 examples from live site
- [x] `clients/sdy/competitor-analysis.md` — auto-populated: 7 organic competitors profiled by research_competitors.py
- [ ] GBP verification — needed before publishing location pages publicly
- [ ] Elementor template — complete build, provide template ID for fetch_elementor_template.py

---

## Still Needs Human Input (GTM)

- [x] `clients/gtm/seo-guidelines.md` — all Castos/podcast placeholder content replaced with GTM massage-specific examples and guidance
- [x] `clients/gtm/internal-links-map.md` — populated from live site crawl (main site + blog subdomain, 58 + 62 pages)
- [x] `clients/gtm/competitor-analysis.md` — auto-populated by research_competitors.py (10 map pack + 8 organic, 15 profiles)
- [x] `clients/gtm/target-keywords.md` — fully populated: GBP categories, 8 active services, pipeline services, condition-based, location modifier matrix
- [x] `clients/gtm/writing-examples.md` — 3 real blog posts added (Thai massage, nutrition, Glasgow news) with extracted style notes
- [ ] Google Sheet — add Column E (Content Type) dropdown with values: service, location, pillar, topical, blog
- [x] Elementor template — FAQ section removed; local template JSON refreshed via fetch_elementor_template.py
- [x] Existing posts (16637–16667) — excerpts set manually in wp-admin for cleaner hub display
- [ ] Hub section — set `line-height: 1.2` in Elementor site custom CSS if long titles wrap awkwardly
- [x] `clients/gtm/config.json` — `schema.logo_url` confirmed and updated to correct WP media URL

---

## Known Issues / Limitations

- The `/article` command and other non-core interactive slash commands still reference `@context/` paths rather than `@clients/gtm/`. Not multi-client aware.
- `clients/gtm/seo-guidelines.md` — entity optimisation section complete but rest still has Castos template content.
- Rate limit contention — batch runner competes with active Claude Code conversation on the same API key. Run batch when Claude Code is idle.
- Duplicate Finnieston post (ID 16642) — old bad batch run artefact, can be deleted from wp-admin.
- Media library accumulating duplicate images from repeated republish runs — consider cleaning up old uploads.
- GTM local site removed (2026-03-21) — GTM now live-only. No local environment for GTM.

---

## Deferred / Future

- Multi-client Sheet support — currently one Sheet per project; future: Sheet per client or client column filtering
- FAQ accordion styling — `<details>`/`<summary>` uses browser-default arrow; can be styled with custom CSS in WordPress
- `/write` command entity-awareness — interactive write command doesn't yet follow entity-first research flow
- WordPress parent-page support — location pages should be child pages of their location/pillar parent
- Hub shortcode: consider adding a `limit` attribute and/or grouping by taxonomy for large link lists
