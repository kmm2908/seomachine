# Project Status

Last updated: 2026-03-24 (session 13 — directions snippets, src/ reorganisation, comp-alt content type, seomachine.php v2.5)

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

### SDY batch publishing live + image pipeline hardening (session 11)
- [x] `clients/sdy/writing-examples.md` — populated with GTM examples as style reference
- [x] `seomachine.php` — added explicit `rest_base` to all 5 CPTs; restructured registration with `did_action('init')` fallback; **must deploy to `mu-plugins` (plural) on SiteGround** — `mu-plugin` (singular) is display-only
- [x] SDY SiteGround hosting fix — plugin must live in `wp-content/mu-plugins/` (not `mu-plugin/`)
- [x] `geo_batch_runner.py` — fixed `datetime` UnboundLocalError (removed inline import at line 556)
- [x] `geo_batch_runner.py` — fixed image injection bug: content now reloaded from disk after `generate_for_post()` so published HTML includes `<img>` tags
- [x] **Image retry + fallback pipeline** — Gemini retries 3× (30s/60s/120s backoff) on 503, then auto-falls back to DALL-E 3
- [x] **"Images o/s" status** — on image failure, row marked `Images o/s` + file path written to Column F; next batch run retries images only (no content regeneration); marks DONE on success
- [x] `google_sheets.py` — `IMAGES_PENDING_VALUE`, `update_file_path()`, Column F support; `read_pending()` picks up both `Write Now` and `Images o/s` rows
- [x] `image_generator.py` — `_generate_gemini()` / `_generate_dalle()` split; `_generate()` wrapper handles retry + fallback; returns per-image cost
- [x] SDY Phase 3 batch test — location + service posts published to live site with images, Elementor two-section template confirmed working (ID 606)
- [x] `clients/sdy/elementor-template.json` — re-fetched after layout adjustment

### SDY go-live + two-section injection (session 10)
- [x] SDY Elementor template built locally — S1 and S2 sections replaced with HTML widgets using `<!-- S1 CONTENT -->` and `<!-- S2 CONTENT -->` markers; Button CTA left between them
- [x] `src/fetch_elementor_template.py` — SSL verification skipped for `.local` domains (self-signed cert fix)
- [x] Local template fetched (ID 635), live template imported and fetched (ID 564) — both markers confirmed present
- [x] `data_sources/modules/wordpress_publisher.py` — `_inject_elementor()` updated to support two-section mode; detects S1/S2 markers automatically; falls back to single-widget mode for GTM
- [x] `_find_html_widget_marked()` updated to accept configurable `marker` string
- [x] `clients/sdy/config.json` — `wordpress` block switched to live (`serendipitymassage.co.uk`); app password updated; template ID 564; local credentials preserved in `wordpress_local`

### Quality gate (session 12)
- [x] `QualityGate` class in `data_sources/modules/quality_gate.py` — check/rewrite loop, max 2 rewrites
- [x] Pass thresholds: Flesch Reading Ease ≥ 55 + Hook (mandatory) + CTAs (mandatory) + 2/3 optional (stories, rhythm, paragraphs)
- [x] Targeted rewrite instructions built from specific failures — only failing criteria included per attempt
- [x] Preserve instructions — passing criteria explicitly protected from regression in each rewrite
- [x] API error on rewrite: continues loop if retries remain, returns failed after exhausting
- [x] Scorer error: fail-safe (returns passed=True, skips gate)
- [x] `_to_plain()` strips `<script>` tag content — JSON-LD schema was being scored as prose (caused Flesch 0 and false paragraph failures)
- [x] On final failure: best rewrite saved to disk, row marked `Review` in Sheet, failures written to Column G, cost recorded, publish skipped
- [x] Mini-stories re-enabled as 5th engagement criterion with massage therapy patterns (unnamed client scenarios)
- [x] CTA patterns updated for massage therapy — 10 domain-specific patterns replacing SaaS-era defaults
- [x] `google_sheets.py` — `REVIEW_REQUIRED_VALUE` (`Review`), `PUBLISH_VALUE` (`Publish`), `update_notes()` (Column G), `update_review_count()` (Column H)
- [x] `geo_batch_runner.py` — DONE/cost writes deferred until after gate passes; rewrite costs added to row total
- [x] `Publish` status — batch runner reads file from Column F, publishes without regenerating, marks DONE
- [x] Column G (Notes) — quality failures written on Review, cleared on DONE
- [x] Column H (Review #) — increments each time a row is flagged Review, retained on DONE
- [x] `logs/quality-log.csv` — append-only log of every Review event (date, client, type, topic, attempts, failures)
- [x] End-to-end tested: Glasgow Central Station passed gate (Flesch 55, 2 rewrites), published to SDY live (ID 677)

### Elementor template auto-refresh (session 12)
- [x] `fetch_elementor_template.py` — saves `elementor-template-meta.json` sidecar with WP `modified` date on every fetch
- [x] `refresh_if_stale(abbr, wp_config)` — lightweight REST check; auto-re-fetches template if WP modified date is newer
- [x] Batch runner calls `_ensure_template_fresh()` once per client per run before every publish (Images o/s, Publish, and Write Now paths)
- [x] `clients/sdy/elementor-template-meta.json` — created; baseline `modified` date stored

### src/ folder reorganisation (session 13)
- [x] `src/` split into module subfolders: `src/content/`, `src/research/`, `src/publishing/`, `src/snippets/`, `src/competitors/`
- [x] All scripts moved: `geo_batch_runner.py` + `republish_existing.py` → `src/content/`; all `research_*.py` → `src/research/`; `fetch_elementor_template.py` → `src/publishing/`; `generate_directions_snippet.py` → `src/snippets/`
- [x] All ROOT paths updated from `Path(__file__).parent.parent` to `Path(__file__).parent.parent.parent`
- [x] Batch runner import paths updated to use `ROOT / 'src' / 'publishing'` and `ROOT / 'src' / 'snippets'`
- [x] CLAUDE.md updated with new paths throughout (batch runner commands, research script paths, fetch_elementor_template path, Project Structure section)

### Directions snippet generator (session 13)
- [x] `src/snippets/generate_directions_snippet.py` — reads client config, outputs self-contained HTML+JS Google Maps directions widget
- [x] GTM Place ID `ChIJnQImbT5FiEgRon5L9CbTr28` added to `clients/gtm/config.json`
- [x] Snippets saved to `clients/[abbr]/snippets/[abbr]-directions.html`
- [x] `_ensure_directions_snippet()` added to batch runner — auto-generates on first publish run per client (runs alongside `_ensure_template_fresh`)
- [x] GTM snippet: `clients/gtm/snippets/gtm-directions.html`
- [x] SDY snippet: `clients/sdy/snippets/sdy-directions.html`

### comp-alt content type (session 13)
- [x] `.claude/agents/competitor-alt-writer.md` — new agent for "X alternative" competitor comparison pages
- [x] `comp-alt` added to `CONTENT_TYPE_AGENTS` and `PROMPT_BUILDERS` in batch runner
- [x] `build_comp_alt_prompt()` — loads directions widget from snippets folder and injects into user prompt
- [x] `competitor-analysis.md` loaded in system prompt when `content_type == 'comp-alt'`
- [x] Maps to `seo_comp_alt` CPT in `clients/gtm/config.json` and `clients/sdy/config.json`
- [x] Column E value in Google Sheet: `comp-alt`
- [x] Two competitor alternative pages written for GTM:
  - `content/gtm/competitor-alternatives/tiger-lily-thai-spa-alternative/tiger-lily-thai-spa-alternative.html`
  - `content/gtm/competitor-alternatives/thai-house-massage-glasgow-alternative/thai-house-massage-glasgow-alternative.html`

### seomachine.php v2.5 (session 13)
- [x] New `seo_comp_alt` CPT registered: "Competitor Alternatives" / "Competitor Alternative", REST base `seo_comp_alt`
- [x] Permalink: `/comp-alt/[slug]/` — rewrite slug derived via `str_replace('_', '-', str_replace('seo_', '', $slug))`
- [x] Added to convert metabox labels, Quick Edit dropdown, SEO Type column, and hub shortcode type map
- [x] Elementor auto-enable filter covers `seo_comp_alt` automatically (via the constant)
- [ ] **Needs deploying to GTM and SDY live sites** — upload to `wp-content/mu-plugins/`, then Settings → Permalinks → Save on each site

### WordPress permalink fix (session 12)
- [x] `seomachine.php` — `register_activation_hook` added; flushes rewrite rules on plugin activation so CPT permalinks work immediately on new installs
- [x] SDY live site — permalink flush resolved `/location/[slug]/` 404 (Settings → Permalinks → Save)

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

### Priority 6 — Session 13 (needs testing)
- [ ] Deploy `wordpress/seomachine.php` v2.5 to GTM live (`wp-content/mu-plugins/`) — flush permalinks after upload
- [ ] Deploy `wordpress/seomachine.php` v2.5 to SDY live (`wp-content/mu-plugins/`) — flush permalinks after upload
- [ ] Confirm `seo_comp_alt` CPT appears in wp-admin on both sites
- [ ] Confirm `/comp-alt/[slug]/` permalink routing works on both sites
- [ ] Test `comp-alt` batch run — set Column E to `comp-alt`, run with `--publish`, confirm Elementor page created under correct CPT
- [ ] Verify directions snippet auto-generates on first batch publish run (check `clients/[abbr]/snippets/` folder)

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
- [x] Build location page template in Elementor library — S1/S2 HTML widgets with markers
- [x] Get template ID (635) and run `python3 src/fetch_elementor_template.py sdy`

#### Phase 2 — Push to live
- [x] Deploy seomachine.php to live `wp-content/mu-plugins/`
- [x] Confirm CPTs active and Elementor auto-enabled on live
- [x] Import Elementor template to live — template ID 564
- [x] Update `clients/sdy/config.json` — `wordpress` block now points to live; app password set; template ID 564
- [x] Run `python3 src/fetch_elementor_template.py sdy` against live — S1/S2 markers confirmed

#### Phase 3 — Content (after Phase 2)
- [x] Add `SDY` to Column D dropdown in Google Sheet
- [x] Add Column E (Content Type) dropdown if not already present
- [ ] Populate `clients/sdy/internal-links-map.md` with confirmed service page URLs
- [x] Add writing examples to `clients/sdy/writing-examples.md` — using GTM examples as style reference
- [x] Test batch: location + service posts published successfully with images (IDs 596, 606)
- [x] Verify content lands in correct CPT with Elementor template — confirmed two-section injection working

### Still Needs Human Input (SDY)
- [ ] Deploy `wordpress/seomachine.php` v2.5 to SDY live `wp-content/mu-plugins/` — then Settings → Permalinks → Save to flush rewrite rules
- [x] Local WP URL and credentials — in config.json (`wordpress` block = local, `wordpress_live` = live)
- [x] Live credentials and app password — set in config.json; `wordpress` block now live
- [x] Elementor template — built (local ID 635, live ID 564); fetched and stored
- [ ] `clients/sdy/internal-links-map.md` — confirm service page URLs on live site
- [x] `clients/sdy/writing-examples.md` — populated with GTM style examples
- [x] `clients/sdy/competitor-analysis.md` — auto-populated: 7 organic competitors profiled by research_competitors.py
- [ ] GBP verification — needed before publishing location pages publicly
- [x] Add `SDY` to Column D dropdown in Google Sheet

---

## Still Needs Human Input (GTM)

- [ ] Deploy `wordpress/seomachine.php` v2.5 to GTM live `wp-content/mu-plugins/` — then Settings → Permalinks → Save to flush rewrite rules
- [x] `clients/gtm/seo-guidelines.md` — all Castos/podcast placeholder content replaced with GTM massage-specific examples and guidance
- [x] `clients/gtm/internal-links-map.md` — populated from live site crawl (main site + blog subdomain, 58 + 62 pages)
- [x] `clients/gtm/competitor-analysis.md` — auto-populated by research_competitors.py (10 map pack + 8 organic, 15 profiles)
- [x] `clients/gtm/target-keywords.md` — fully populated: GBP categories, 8 active services, pipeline services, condition-based, location modifier matrix
- [x] `clients/gtm/writing-examples.md` — 3 real blog posts added (Thai massage, nutrition, Glasgow news) with extracted style notes
- [x] Google Sheet — Column E (Content Type) dropdown added with values: service, location, pillar, topical, blog
- [x] Elementor template — FAQ section removed; local template JSON refreshed via fetch_elementor_template.py
- [x] Existing posts (16637–16667) — excerpts set manually in wp-admin for cleaner hub display
- [x] Hub section — line-height confirmed not needed; all titles display cleanly at default
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
