# Project Status

Last updated: 2026-03-30 (session 24 — wp-elementor skill improved with workshop safe-editing approach)

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
- [x] GHL location IDs populated: GTM/GTB = `HbhlMeHmDvc4pB9eEAZQ`, SDY = `RXcT7rTaqfcrcUWtpdyO`, TMG = `xRaKh2rHTuvOQ3w8bSn5`

### Content agents (7 writers)
- [x] `service-page-writer.md`, `location-page-writer.md`, `pillar-page-writer.md`, `topical-writer.md`, `blog-post-writer.md`, `competitor-alt-writer.md`, `problem-page-writer.md`
- [x] **FAQ accordion** — all 7 agents output `<details>`/`<summary>` collapsible FAQ (no JS/CSS needed)
- [x] **Schema markup** — all 7 agents output `<!-- SCHEMA -->` block with JSON-LD `@graph` (primary type + FAQPage + LocalBusiness)
- [x] **Inline booking CTAs** — all 7 agents include 2-3 inline booking links to `booking_url` (session 22)
- [x] **Short anchor text** — all 7 agents: 3-6 words per anchor, never wrap full sentences (session 22)
- [x] **Short paragraphs** — all 7 agents: maximum 3 sentences per paragraph (session 22)

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
- [x] `upload_media()` — returns `(media_id, source_url)` tuple; uses `self.session.post` (session 22 fix: was bypassing SSL skip with bare `requests.post`)
- [x] `_upload_and_replace_images()` — uploads all local images, rewrites relative src to absolute WP URLs before creating draft
- [x] `_wrap_schema_block()` — wraps schema in Gutenberg `wp:html` block (non-Elementor path)
- [x] `publish_html_content()` — HTML publishing path; branches on Elementor vs plain; accepts `excerpt` param
- [x] **SSL skip for `.local` domains** (session 22) — `self.session.verify = False` when WP URL ends in `.local`; applies to all requests including media upload

### Elementor template injection
- [x] `src/fetch_elementor_template.py` — one-time CLI: fetches `elementor_library/{id}` from WP, saves to `clients/[abbr]/elementor-template.json`
- [x] `_inject_elementor()` — injects article HTML into HTML widget; strips first H2; appends schema script; fixes list spacing inline
- [x] `_find_html_widget()` — depth-first walk; matches "Paste HTML Here" marker, fallback to first HTML widget
- [x] `_create_elementor_page()` — POSTs to correct CPT endpoint with `_elementor_data` + `_elementor_edit_mode: builder` meta + excerpt
- [x] Auto-detected: if `clients/[abbr]/elementor-template.json` exists, Elementor path is used automatically
- [x] GTM template fetched and saved — `clients/gtm/elementor-template.json`

### WordPress Custom Post Types
- [x] `wordpress/seomachine.php` v2.8.0 — MU-plugin; must be in `wp-content/mu-plugins/` (not inside `plugins/`)
- [x] 7 CPTs registered: `seo_service`, `seo_location`, `seo_pillar`, `seo_topical`, `seo_blog`, `seo_comp_alt`, `seo_problem`
- [x] All CPTs grouped under "SEO Content" parent menu in wp-admin
- [x] `seo_meta` REST field registered on all CPTs — Yoast-compatible meta keys, works without Yoast installed
- [x] Elementor filter — all 5 CPTs available in Elementor builder (must be enabled in Elementor → Settings first)
- [x] `content_type_map` in client config — batch runner resolves correct CPT from content type

### Hub page shortcode (new session 5, updated session 22)
- [x] `[seo_hub type="location"]` shortcode in `seomachine.php` — renders published posts as `<ul class="seo-hub-links">` with `<li><h3><a>` structure
- [x] Display text = post excerpt if set, otherwise post title (fallback)
- [x] Supports all 7 types: location, service, pillar, topical, blog, comp_alt, problem
- [x] Sorted A–Z by title; auto-updates on publish/unpublish (WP_Query, status=publish only)
- [x] Must use Elementor **Shortcode widget** (not HTML widget) — HTML widget does not process shortcodes
- [x] CSS: `li h3 a { font-size: 0.8rem }` from Elementor Kit applies automatically — no custom CSS needed
- [x] Line-height for wrapped items: add `.elementor-shortcode .seo-hub-links h3 { line-height: 1.2; }` to site custom CSS if needed
- [x] **Problem grid layout** (session 22) — `[seo_hub type="problem"]` renders a 3-column CSS grid with bordered cards, disc bullets, inherited link colours, mobile-responsive (stacks to 1 column); items wrapped in `<h3>` tags via `seo_hub_problem_grid()` function

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

### Quality gate (session 12, updated session 22)
- [x] `QualityGate` class in `data_sources/modules/quality_gate.py` — check/rewrite loop, max 2 rewrites
- [x] Pass thresholds: Hook (mandatory) + CTAs (mandatory) + 2/3 optional (stories, rhythm, paragraphs); Flesch per type: default ≥ 55, location ≥ 50, comp-alt ≥ 48, problem ≥ 48
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
- [x] **CTA body-only analysis** (session 22) — CTA distribution now runs on body text only (excludes FAQ section via `_to_body_plain()`); rule simplified to ≥2 CTAs + first within 500 words
- [x] **Paragraph body-only analysis** (session 22) — paragraph length check excludes FAQ section (FAQ answers naturally run 4 sentences); threshold tightened from >4 to >3 sentences; paragraphs now **mandatory** (was optional); pass: ≤3 long paragraphs in body
- [x] **Code fence stripping** (session 22) — `quality_gate.py` strips markdown code fences from rewrite output; `geo_batch_runner.py` strips fences from initial generation too
- [x] **Location Flesch threshold** (session 22) — `location` content type config added: Flesch ≥ 50 (place names and geographic terms drag down readability scores)
- [x] **Problem Flesch threshold** (session 22) — `problem` content type: Flesch lowered from 55 to 48 (medical/health content is naturally denser)
- [x] **Rate limit retry sleep** (session 22) — 65-second sleep between rewrite retry attempts when API returns rate limit error (was failing immediately before)
- [x] **`published_review` status** (session 23) — quality gate failures now publish to WordPress as drafts with ★★★★★ in title + failure notice paragraph; status `published_review` in queue; `✎` icon in `--status` display; user reviews directly in wp-admin instead of editing local HTML files

### Elementor template auto-refresh (session 12)
- [x] `fetch_elementor_template.py` — saves `elementor-template-meta.json` sidecar with WP `modified` date on every fetch
- [x] `refresh_if_stale(abbr, wp_config)` — lightweight REST check; auto-re-fetches template if WP modified date is newer
- [x] Batch runner calls `_ensure_template_fresh()` once per client per run before every publish (Images o/s, Publish, and Write Now paths)
- [x] `clients/sdy/elementor-template-meta.json` — created; baseline `modified` date stored

### Auto-deploy pipeline (session 17, expanded session 21)
- [x] `.github/workflows/deploy-plugin.yml` — GitHub Actions workflow; deploys `wordpress/seomachine.php` to all 5 sites via SFTP on every push to main that touches the file
- [x] SSH key pair generated (`~/.ssh/seomachine_deploy`); public key added to SiteGround SSH Manager on all 3 accounts; private key stored as `SITEGROUND_SSH_KEY` GitHub Actions secret
- [x] Three parallel jobs: GTM/GTB (`u2168-sqqieazmgeuw@ukm1.siteground.biz`), SDY (`u2732-2mxetksmslhk@gukm1055.siteground.biz`), TMG/TMB (`u3520-kztrwuly6pid@uk1001.siteground.eu`)
- [x] All 3 jobs tested and confirmed working (session 21)
- [x] Correct SFTP paths: `www/[domain]/public_html/wp-content/mu-plugins/seomachine.php`

### AI brand visibility & positioning (session 16)
- [x] `context/ai-brand-visibility.md` — Brian Dean (Backlinko) YouTube video transcribed, summarised, and stored; covers 4 strategies for getting brands cited in LLM/AI answers; includes section translating strategies for local service clients (GTM, SDY)
- [x] `ai_visibility` block added to `clients/gtm/config.json`, `clients/sdy/config.json`, `clients/gtb/config.json` — fields: `canonical_description`, `brand_associations`, `positioning_note`
- [x] `build_system_prompt()` in `src/content/geo_batch_runner.py` — injects `## AI Brand Positioning` section for `blog` and `topical` content types only; gracefully handles missing block or partial fields; empty dict guard prevents bare heading injection
- [x] `src/content/publish_scheduled.py` — inherits `ai_visibility` automatically (imports `build_system_prompt` from batch runner; no code change needed)
- [x] `tests/test_ai_visibility.py` — 9 tests: injection for blog + topical, exclusion for location/service/pillar/comp-alt, missing block, partial fields, empty dict
- [x] `clients/README.md` — `ai_visibility` schema documented with field descriptions
- [x] `.claude/commands/new-client.md` — Q11 (canonical description with auto-draft) and Q12 (positioning note) added; WordPress questions renumbered Q13–Q15
- [x] `docs/superpowers/specs/2026-03-24-ai-visibility-config-design.md` — approved spec
- [x] `docs/superpowers/plans/2026-03-24-ai-visibility-config.md` — reviewed implementation plan
- [x] `CLAUDE.md` — `ai_visibility` field documented; `context/ai-brand-visibility.md` added to global context list

### Blog topic research pipeline (session 14)
- [x] `"niche"` field added to all 3 client configs: GTM=`thai-massage`, GTB=`thai-massage`, SDY=`massage-therapy`
- [x] `src/research/research_blog_topics.py` — keyword research + competitor SERP scoring; niche cache at `research/niches/[niche]/` (30-day TTL, shared across clients in same niche)
- [x] Thresholds: vol ≥ 50, competition ≤ 40%; informational intent filter; location-keyword filter
- [x] `--sheet` flag pushes topics to Google Sheet with status `pause` for human review before running
- [x] `--refresh` flag forces cache refresh; `--limit` controls output count (default 25)
- [x] `google_sheets.py` — DEFAULT_RANGE expanded to `A2:I1000`; `niche` added to `read_pending()` output; `update_niche()` added (Column I)
- [x] `/research-blog-topics [abbr]` command — runs script, then Claude adds cluster analysis, angle suggestions, cross-linking chains, and publishing cadence recommendation
- [x] `/research-blog-topics gtb` — run and tested; 19 topics generated, report at `research/gtb/blog-topics-2026-03-24.md`

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

### Static direction maps (session 21)
- [x] SDY static maps: `clients/sdy/snippets/sdy-static-maps.html` — 6 Google Maps embeds from Glasgow landmarks (Central Station, Buchanan Bus Station, Queen Street, St Enoch Subway, George Square, Cowcaddens Subway) to Central Chambers
- [x] Settings: zoom `!1d1000`, height `400px`, walking directions, building name in address
- [ ] Generate static maps for GTM (same landmarks, different destination address)
- [ ] Generate static maps for TMG (Greenock landmarks to South Street)

### Problem content type (session 21, expanded session 22)
- [x] `seo_problem` CPT registered in `seomachine.php` v2.8.0 — URL pattern `/problem/[slug]/`
- [x] `.claude/agents/problem-page-writer.md` — 600–800 word condition/symptom pages with mandatory outbound links to authoritative sources (Wikipedia, NHS, PubMed) via live web search
- [x] `build_problem_prompt()` in batch runner — web search queries for condition + massage benefits + NHS guidance
- [x] `CONTENT_TYPE_CONFIG['problem']` in quality gate — Flesch ≥ 48 (lowered from 55, session 22), rhythm/paragraphs, no stories
- [x] `problem` → `seo_problem` added to GTM, SDY, and TMG content_type_maps
- [x] `research/gtm/problem-queue.json` — 12 conditions queued (sciatica, stiff neck, headaches, etc.)
- [x] `research/tmg/problem-queue.json` — same 12 conditions, unique content per site via brand voice + local context
- [x] `research/sdy/problem-queue.json` — 13 conditions queued (session 22)
- [x] Hub shortcode supports `[seo_hub type="problem"]` with 3-column grid layout (session 22)
- [x] **Problem grid h3 fix** (session 22) — `seo_hub_problem_grid()`: h3 wrapping now happens BEFORE `array_chunk()` so chunks contain the wrapped items (was wrapping after chunking, so h3 tags never appeared in output)
- [x] SDY Sciatica test page published successfully (post 956, session 22)
- [x] SDY service queue created and completed: `research/sdy/service-queue.json` — 8/8 published (session 22)
- [x] SDY location queue created and completed: `research/sdy/location-queue.json` — 10/10 (9 clean + 1 review, session 23)
- [x] SDY problem queue completed: `research/sdy/problem-queue.json` — 13/13 (10 clean + 3 review, session 23)
- [x] Batch publish all 13 SDY problem pages — complete (10 clean + 3 published_review)
- [ ] Batch publish all 12 for GTM
- [ ] Batch publish all 12 for TMG

### SDY batch results (sessions 22–23)
- [x] Services: 8/8 published (post IDs 985–1030), zero failures, $5.15 total
- [x] Problems: 13/13 complete — 10 published clean, 3 published for review (Injury Rehabilitation 1149, Injury Prevention 1154, Diabetic Neuropathy 1159)
- [x] Locations: 10/10 complete — 9 published clean, 1 published for review (Cowcaddens 1164)
- [x] Total: 31/31 complete — all SDY content queues finished

### Batch summary email (planned, session 22)
- [ ] Daily digest email instead of per-article emails — standalone script reading `logs/scheduled-publish-log.csv`, sends summary of all publishes/failures for the day

### comp-alt scheduled publishing pipeline (session 18)
- [x] `research/gtm/comp-alt-queue.json` — 3 competitors queued: Tiger Lily, Thai House, Phuket; cadence 7 days
- [x] `research/sdy/comp-alt-queue.json` — 3 competitors queued: Nina Thai, Phuket, Lan Thai; cadence 7 days
- [x] `publish_scheduled.py` — `--queue` flag added; default `topic-queue.json`; pass `comp-alt-queue.json` for comp-alt schedule
- [x] `quality_gate.py` — per-content-type config (`CONTENT_TYPE_CONFIG`); comp-alt: Flesch ≥ 48, no stories criterion, optional min 1 of 2 (rhythm/paragraphs); hook + CTAs mandatory on all types
- [x] `competitor-alt-writer.md` — early booking CTA after step 2; closing CTA paragraph after FAQ section
- [x] `engagement_analyzer.py` — added `book directly`, `book here`, `you can book` to CTA patterns
- [x] All 6 comp-alt pages published as WordPress drafts — GTM: 16690/16695/16700; SDY: 702/707/712
- [x] **Standard process:** multi-run publish batches always use background agent (`run_in_background: true`) — documented in CLAUDE.md

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
- [x] Deployed to GTM live, SDY live, and GTB (`blog.glasgowthaimassage.co.uk`) — permalinks flushed on all three sites

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
- [x] Deploy `wordpress/seomachine.php` v2.5 to GTM live — done
- [x] Deploy `wordpress/seomachine.php` v2.5 to SDY live — done
- [x] Confirm `seo_comp_alt` CPT appears in wp-admin on GTM, SDY, and GTB — confirmed all three
- [x] Confirm `/comp-alt/[slug]/` permalink routing works on GTM, SDY, and GTB — confirmed all three
- [x] Test `comp-alt` batch run — 3 GTM + 3 SDY published via scheduled publisher (post IDs: GTM 16690/16695/16700, SDY 702/707/712)
- [ ] Verify directions snippet auto-generates on first batch publish run (check `clients/[abbr]/snippets/` folder)

### Priority 7 — GTB client setup (session 14)
- [x] `clients/gtb/` folder created — config.json, brand-voice.md, seo-guidelines.md, internal-links-map.md, features.md, target-keywords.md, writing-examples.md, competitor-analysis.md
- [x] `clients/gtb/config.json` — WP URL `blog.glasgowthaimassage.co.uk`, app password, template ID 22538
- [x] `clients/gtb/elementor-template.json` — re-fetched after user added S1/S2 markers in Elementor; two-section mode confirmed (S1 depth 2, S2 depth 3)
- [ ] Confirm CPTs appear in wp-admin on `blog.glasgowthaimassage.co.uk`
- [ ] Add `GTB` to Column D dropdown in Google Sheet
- [ ] Test batch publish run — single blog row with `--publish`, confirm Elementor page created on blog site

### Priority 8 — AI brand visibility (session 16)
- [ ] Run a blog batch row for GTM and confirm `## AI Brand Positioning` wording appears in the intro of the generated HTML
- [ ] Run a location batch row and confirm no positioning language was changed
- [ ] Run `publish_scheduled.py --dry-run --abbr gtb` and confirm AI positioning section appears in output (scheduled path)

### Scheduled publishing pipeline (session 15)
- [x] `src/content/publish_scheduled.py` — cron-driven publisher; reads `research/[abbr]/topic-queue.json`; one topic per run; full pipeline (generate → quality gate → WP publish → log → email)
- [x] `--status` flag — formatted queue table with icons (✓ published · · pending · ⚠ review · ✗ failed), next-due date, overdue warning
- [x] `--dry-run` flag — generates and quality-checks content, skips WordPress publish
- [x] Missed-run detection — compares last published date from log vs cadence + 2-day buffer; warning appended to email
- [x] `logs/scheduled-publish-log.csv` — append-only log (date, abbr, topic, content_type, status, post_id, cost, notes)
- [x] `research_blog_topics.py --queue` — generates `research/[abbr]/topic-queue.json` from top topics; `--cadence N` sets days between runs (default 7)
- [x] `~/.claude/settings.json` — PreCompact hook added: injects instruction to run `/wrap` before context is compacted
- [x] `.claude/commands/wrap.md` — multi-window / parallel agent policy added (section ownership, sequencing rules)
- [ ] Set up cron job for GTB scheduled publishing (once first test batch passes)

---

## Client: GTB (Glasgow Thai Massage — Blog Site)

Blog subdomain for Glasgow Thai Massage. Separate WordPress install at `blog.glasgowthaimassage.co.uk`. Same business/brand as GTM. Architecture decision: blog subdomain = separate client entry; if a future client has blog on main domain, they use the same abbreviation.

### Setup Status
- [x] `clients/gtb/` folder — all context files created (brand voice, SEO guidelines, features, target keywords, writing examples, competitor analysis)
- [x] `clients/gtb/config.json` — URL `blog.glasgowthaimassage.co.uk`, username `kmm_st65inj7`, template ID 22545 (updated session 21)
- [x] `clients/gtb/elementor-template.json` — fetched; S1/S2 markers confirmed (two-section mode, same as SDY)
- [x] `seomachine.php` v2.5 deployed to `blog.glasgowthaimassage.co.uk`
- [ ] Confirm 6 CPTs appear in wp-admin
- [ ] Add `GTB` to Google Sheet Column D dropdown
- [ ] Test batch publish run

### Blog Category Schedule (session 25)

Four WordPress post categories with separate queue files per category.

| Category | Queue file | Initial batch | Ongoing |
|----------|-----------|--------------|---------|
| Thai Massage | `thai-massage-queue.json` | 4 posts | 2/week (Mon + Thu) |
| Stay Healthy | `stay-healthy-queue.json` | 2 posts | 1/week (Tue) |
| Glasgow News | `glasgow-news-queue.json` | 2 posts | 1/week (Wed) |
| Yoga & Stretching | `yoga-stretching-queue.json` | 2 posts | 1/week (Fri) |

- [x] Queue files created in `research/gtb/` — all 4 categories, topics populated from existing research
- [x] `wp_category` field added to queue entry format — publisher assigns WP category on publish
- [x] `seomachine.php` — `category` taxonomy registered for `seo_blog` CPT
- [x] `wordpress_publisher.py` — `category` param added to `publish_html_content()`; `_create_elementor_page()` forwards category IDs
- [x] `publish_scheduled.py` — reads `wp_category` from queue entry and passes to publisher
- [ ] Set up cron jobs for all 4 category queues (once first dry-run passes)
- [ ] Glasgow News topics: curate 2 real local news/wellness angles before publishing
- [ ] Yoga & Stretching: find YouTube URLs, use `/ingest-youtube` + `/write` to produce content before publishing

**Cron schedule (to set up):**
```
0 9 * * 1 python3 src/content/publish_scheduled.py --abbr gtb --queue thai-massage-queue.json
0 9 * * 2 python3 src/content/publish_scheduled.py --abbr gtb --queue stay-healthy-queue.json
0 9 * * 3 python3 src/content/publish_scheduled.py --abbr gtb --queue glasgow-news-queue.json
0 9 * * 4 python3 src/content/publish_scheduled.py --abbr gtb --queue thai-massage-queue.json
0 9 * * 5 python3 src/content/publish_scheduled.py --abbr gtb --queue yoga-stretching-queue.json
```

**YouTube workflow (Yoga & Stretching category):**
1. Find a relevant yoga/stretching YouTube video
2. `/ingest-youtube [URL]` — extracts transcript + summary
3. `/write [topic]` — use transcript as source material
4. Add to `yoga-stretching-queue.json` with `status: pending`

---

## Client: SDY (Serendipity Massage Therapy & Wellness)

New client added 2026-03-21. Brand-new WordPress site, same stack as GTM (Elementor + Hello theme).
GBP applied for but not yet verified. Abbreviation: `SDY`.

### Deployment Plan

**Rule: local for setup/design, live for all batch runner content.**
Reason: caching on the live front-end doesn't affect the REST API. Running content against two environments causes DB divergence. Push local → live once, then stay on live for all publishing.

#### Phase 1 — Local setup (done, returned to session 22)
- [x] Get local site URL and credentials — added to config.json (`wordpress` = local, `wordpress_live` = live)
- [x] Deploy `wordpress/seomachine.php` to local `wp-content/mu-plugins/`
- [x] Confirm 5 CPTs appear via REST API (`seo_service`, `seo_location`, `seo_pillar`, `seo_topical`, `seo_blog`)
- [x] Elementor CPTs auto-enabled via `option_elementor_cpt_support` filter — confirmed all 5 showing in Elementor → Settings
- [x] Build location page template in Elementor library — S1/S2 HTML widgets with markers
- [x] Get template ID (635) and run `python3 src/fetch_elementor_template.py sdy`
- [x] **Returned to local** (session 22) — switched back to `https://sdy.local/` due to server caching issues on live; app password updated; new Elementor template ID 663 (replacing 635); problem grid shortcode deployed to local mu-plugins

#### Phase 2 — Push to live
- [x] Deploy seomachine.php to live `wp-content/mu-plugins/`
- [x] Confirm CPTs active and Elementor auto-enabled on live
- [x] Import Elementor template to live — template ID 564
- [x] Update `clients/sdy/config.json` — `wordpress` block now points to live; app password set; template ID 564
- [x] Run `python3 src/fetch_elementor_template.py sdy` against live — S1/S2 markers confirmed
- **Note:** SDY currently targeting local (`sdy.local`) as of session 22. Will switch back to live once caching issues are resolved.

#### Phase 3 — Content (after Phase 2)
- [x] Add `SDY` to Column D dropdown in Google Sheet
- [x] Add Column E (Content Type) dropdown if not already present
- [ ] Populate `clients/sdy/internal-links-map.md` with confirmed service page URLs
- [x] Add writing examples to `clients/sdy/writing-examples.md` — using GTM examples as style reference
- [x] Test batch: location + service posts published successfully with images (IDs 596, 606)
- [x] Verify content lands in correct CPT with Elementor template — confirmed two-section injection working

### Still Needs Human Input (SDY)
- [x] Deploy `wordpress/seomachine.php` v2.5 to SDY live — done (session 14)
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

- [x] Deploy `wordpress/seomachine.php` v2.5 to GTM live — done (session 14)
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

## Content Repurposing Pipeline (session 19 — designed and implemented)

Design spec: `docs/superpowers/specs/2026-03-26-content-repurposing-pipeline-design.md`

Fully automated pipeline that takes each published blog article and creates video + social media content:
- **Video:** ElevenLabs TTS voiceover + FFmpeg composition (slides, Ken Burns, text overlays) → 8-12 min long-form YouTube video
- **Shorts:** AI-driven extraction of 3-5 best moments (20-45s each) → YouTube Shorts, TikTok, FB Reels, IG Reels
- **Social posts:** LinkedIn, Facebook, X (thread/standalone alternating weeks), Instagram, Pinterest, GBP — all platform-specific
- **Publishing:** GoHighLevel Social Planner API as single gateway to all platforms (clients already have GHL accounts)
- **Architecture:** Two-stage pipeline — blog publishes first (existing), then `src/social/repurpose_content.py` runs 2hrs later via cron, generates all assets, schedules everything via GHL with staggered weekly spread
- **Future:** HeyGen AI avatar swap-in (clean TTS interface), per-client schedule config in config.json

### Implementation status
- [x] Design spec written and reviewed
- [x] ElevenLabs TTS wrapper (`data_sources/modules/elevenlabs_tts.py`) — uses `stream_with_timestamps` for audio + alignment — 4 tests passing
- [x] GoHighLevel publisher (`data_sources/modules/ghl_publisher.py`) — Private Integration tokens (not OAuth), media upload, post scheduling, week alternation — 5 tests passing
- [x] Social post generator (`src/social/social_post_generator.py`) — Claude-powered video script + social posts from blog HTML — 2 tests passing
- [x] Video producer (`src/social/video_producer.py`) — FFmpeg long-form + shorts, Ken Burns, slides, thumbnails, SRT captions — 4 tests passing
- [x] Orchestrator (`src/social/repurpose_content.py`) — CLI with `--abbr`, `--dry-run`, `--status`, `--topic`; CSV logging; email notifications; GHL scheduling — 3 tests passing
- [x] Client config updated — `elevenlabs.voice_id` + `ghl.location_id` + `ghl.accounts` for all 5 clients (GTM, GTB, SDY, TMG, TMB)
- [x] Pinterest support added (session 21) — schedule key, key map, dispatch handler, Claude prompt for pin generation; `pinterest` field in all client configs
- [x] Dependencies installed — `elevenlabs>=1.0.0`, `ffmpeg-python>=0.2.0`; FFmpeg binary at `/opt/homebrew/bin/ffmpeg`
- [x] All 18 unit tests passing
- [x] ElevenLabs API key set in `.env`; both voices (Maliwan, Jariya) verified working with real API
- [x] GHL Private Integration tokens set for all 4 clients; location endpoints verified working
- [ ] Connect social media accounts in GHL Social Planner (in progress — reconnecting expired accounts)
- [ ] Auto-populate `ghl.accounts` IDs from API (once social accounts are connected)
- [ ] End-to-end test with real article

### API credentials — current state
- [x] ElevenLabs API key in `.env`
- [x] ElevenLabs voice IDs: GTM/GTB = Maliwan (`7LUeVw...`), SDY/TMG = Jariya (`WthqhsW...`)
- [x] GHL Private Integration tokens: `clients/[abbr]/ghl-tokens.json` (gitignored, format: `{"token": "pit-..."}`)
- [x] GHL location IDs: GTM/GTB = `HbhlMeHmDvc4pB9eEAZQ`, SDY = `RXcT7rTaqfcrcUWtpdyO`, TMG = `xRaKh2rHTuvOQ3w8bSn5`
- [ ] GHL social account IDs (`ghl.accounts.*` in config.json) — waiting for social accounts to be reconnected in GHL

---

## Client: TMG (Thai Massage Greenock) + TMB (Blog Subdomain)

New client added 2026-03-26. Existing WordPress site at `thaimassagegreenock.co.uk`, blog subdomain at `blog.thaimassagegreenock.co.uk`. Same niche as GTM (`thai-massage`). Therapist: Jariya Malone (Wat Po trained). Inverclyde area.

### Setup Status (session 20)
- [x] `clients/tmg/` folder — config.json, brand-voice.md, seo-guidelines.md, internal-links-map.md, features.md, target-keywords.md, writing-examples.md
- [x] `clients/tmg/config.json` — WP credentials set, GHL location ID `xRaKh2rHTuvOQ3w8bSn5`, social accounts populated from website, ElevenLabs voice ID set
- [x] `clients/tmb/` folder — config.json for blog subdomain (`blog.thaimassagegreenock.co.uk`)
- [x] `clients/tmb/config.json` — WP credentials set (username `kmm-nlgeo-trust43S`, app password configured)
- [x] Internal links map populated from live site — 6 service pages, 6 location pages, 5 key pages
- [x] Deploy `wordpress/seomachine.php` to TMG main site — auto-deploy via GitHub Actions (session 21)
- [x] Deploy `wordpress/seomachine.php` to TMB blog site — auto-deploy via GitHub Actions (session 21)
- [x] SSH public key added to TMG SiteGround account (`u3520-kztrwuly6pid@uk1001.siteground.eu`)
- [ ] Fetch Elementor template (if using Elementor) and set `elementor_template_id` in both configs
- [ ] Run `research_competitors.py --abbr tmg` to generate `clients/tmg/competitor-analysis.md`
- [ ] Run `research_blog_topics.py --abbr tmb --queue` to generate topic queue
- [ ] Test batch publish run on TMB
- [ ] Add TMG/TMB to Google Sheet Column D dropdown

---

## Cross-Site Hub Shortcode (session 21)

`seomachine.php` v2.7.0 — `[seo_hub]` shortcode now supports fetching posts from a remote WordPress site.

- [x] `seo_hub_remote_fetch()` — REST API fetch with pagination, 12-hour transient cache, graceful error handling
- [x] `seo_hub_source` wp_option — set on blog subdomains to point at main site URL
- [x] Settings → General field added — "SEO Hub Source URL" input for easy config in wp-admin
- [x] `source` shortcode attribute — per-shortcode override (optional)
- [x] `blog` type always queries locally — blog posts live on the subdomain
- [x] No auth required — CPTs are `public => true` / `show_in_rest => true`
- [x] Deployed to all 5 sites via GitHub Actions
- [x] Set `seo_hub_source` on GTB (`https://glasgowthaimassage.co.uk`) via Settings → General
- [x] Set `seo_hub_source` on TMB (`https://thaimassagegreenock.co.uk`) via Settings → General
- [ ] Test `[seo_hub type="location"]` on GTB — confirm links point to main site

---

## Claude Code Skills (session 20)

Global skills installed at `~/.claude/skills/`. Available across all projects.

### Installed this session
- [x] `skill-creator` (18 files) — Anthropic official; create, test, iterate on skills
- [x] `frontend-design` — Anthropic official; production-grade frontend UI with scroll-driven website guidelines
- [x] `video-to-website` — Turn video into scroll-driven animated website (GSAP, canvas frames)
- [x] `mcp-builder` — Anthropic official; guide for building MCP servers
- [x] `webapp-testing` — Anthropic official; Playwright-based web app testing
- [x] `pdf` — Anthropic official; PDF manipulation (3 files)
- [x] `php-pro` — PHP 8.1+ conventions, PSR standards (Jeff Allan collection)
- [x] `python-pro` — Python typing, pytest, async patterns (Jeff Allan collection)
- [x] `api-designer` — REST/GraphQL API design (Jeff Allan collection)
- [x] `nextjs-developer` — Next.js 14+ App Router (Jeff Allan collection)
- [x] `react-expert` — React 18+ / Server Components (Jeff Allan collection)
- [x] `security-reviewer` — Security audit and vulnerability detection (Jeff Allan collection)
- [x] `nano-banana-images` — Kie.ai image generation (~$0.04-0.09/image); API key in `.env`
- [x] `ingest-youtube` — Three-tier fallback YouTube transcript extraction (agentskill.sh)
- [x] `youtube-uploader` — YouTube upload with full metadata control (agentskill.sh)
- [x] `ghl-crm` — GoHighLevel CRM API v2 integration (agentskill.sh)
- [x] `ghl-ai-agents` — GHL Voice AI + Conversation AI setup guide (skillsmp.com)
- [x] `ghl-email-sms-marketing` — GHL email/SMS/WhatsApp campaign guide (skillsmp.com)

---

## Deferred / Future

- Multi-client Sheet support — currently one Sheet per project; future: Sheet per client or client column filtering
- FAQ accordion styling — `<details>`/`<summary>` uses browser-default arrow; can be styled with custom CSS in WordPress
- `/write` command entity-awareness — interactive write command doesn't yet follow entity-first research flow
- WordPress parent-page support — location pages should be child pages of their location/pillar parent
- Hub shortcode: consider adding a `limit` attribute and/or grouping by taxonomy for large link lists
- Per-client social media posting schedule override in config.json (default schedule hardcoded for now)
- Pinterest, Threads, Bluesky social posting (GHL supports them — add when needed)
- Social media analytics/performance tracking from platforms
- Stock video clip integration in video composition
- Batch summary email — daily digest replacing per-article notifications; script reads `logs/scheduled-publish-log.csv`
