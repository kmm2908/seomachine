# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session Start

At the start of every new session, automatically invoke `/start` before responding to anything else.

## Agent Usage

Offload research, writing, file operations, and batch tasks to sub-agents wherever possible to keep the main conversation context clean. Prefer `run_in_background: true` for any task that doesn't need its result before the next step.

**Long-running publish runs must always use a background agent.** Any task that chains multiple `publish_scheduled.py` runs (e.g. publishing a full queue of 3–6 pages) will trip the Claude Code UI timeout ("Not responding") if run directly. The standard pattern:

```
Agent prompt: "Run these commands in sequence in /path/to/seomachine, one at a time, 300000ms timeout each:
  python3 src/content/publish_scheduled.py --abbr gtm --queue comp-alt-queue.json  (×N)
Report back: client, topic, status, post ID, cost per run."
run_in_background: true
```

This applies to: `publish_scheduled.py` multi-run batches, `geo_batch_runner.py` on large Sheet ranges, and any other task expected to take >2 minutes total.

## Project Overview

SEO Machine is a Claude Code workspace for creating SEO-optimised content at scale. It combines custom commands, specialised agents, a Python batch runner, and Google Sheets integration to research, write, optimise, and publish articles for multiple business clients.

## Setup

```bash
pip install -r data_sources/requirements.txt
```

API credentials go in `.env` at the project root (copy from `.env.example`):
- `ANTHROPIC_API_KEY` — required for the batch runner
- `GEO_LOCATIONS_SHEET_ID` — Google Sheet ID for the content queue
- `GA4_CREDENTIALS_PATH` — path to service account JSON
- DataForSEO, GSC, and SMTP email settings (optional)

WordPress credentials are configured per client in `clients/[abbr]/config.json` (not in `.env`).

## Client Structure

Each client lives in a single folder. To add a new client, run `/new-client`.

```
clients/
  gtm/                  ← Glasgow Thai Massage (live, publishing active)
  gtb/                  ← Glasgow Thai Massage Blog (blog.glasgowthaimassage.co.uk)
  sdy/                  ← Serendipity Massage Therapy & Wellness (live, batch publishing active)
  tmg/                  ← Thai Massage Greenock (thaimassagegreenock.co.uk)
  tmb/                  ← Thai Massage Greenock Blog (blog.thaimassagegreenock.co.uk)
    config.json         ← machine-readable config (name, address, WP creds, services)
    brand-voice.md      ← tone, messaging pillars, client-specific writing rules
    seo-guidelines.md   ← keyword strategy, entity optimisation rules
    internal-links-map.md
    features.md
    competitor-analysis.md
    target-keywords.md
    writing-examples.md
  README.md             ← schema docs and how to add new clients
```

**Local/live config pattern** — when a client has a local dev environment, `config.json` uses `wordpress` for the active target and `wordpress_live` to store live credentials. For Phase 2 (push to live), copy `wordpress_live` values into `wordpress`.

**Niche field** — `config.json` includes a `"niche"` key (e.g. `"thai-massage"`, `"massage-therapy"`). Used by `research_blog_topics.py` to cache keyword research at `research/niches/[niche]/` and share it across all clients in the same niche. Blog subdomain clients (e.g. GTB) use the same niche as their main site (GTM). Add a new niche slug when onboarding a client in a different market.

**GBP location ID field** — `config.json` supports an optional `"gbp_location_id"` key (numeric string, e.g. `"123456789012345678"`). When present, enables `data_sources/modules/google_business_profile.py` to fetch live data from the Google Business Profile API. Requires "My Business Business Information API" + "My Business Reviews API" enabled in GCP and a service account with Manager access added to the location in GBP Manager. Credentials path via `GBP_CREDENTIALS_PATH` in `.env`. Full setup in the module's top comment block and `clients/README.md`.

**AI visibility field** — `config.json` includes an optional `"ai_visibility"` block with three sub-fields: `canonical_description` (exact brand description used verbatim by writing agents), `brand_associations` (keyword phrases to weave into content), and `positioning_note` (tone guidance). Injected as a `## AI Brand Positioning` section in system prompts for `blog` and `topical` content types only — applies to both the batch runner and the scheduled publisher, which share the same `build_system_prompt()` function. See `context/ai-brand-visibility.md` for the strategy behind this. Full schema in `clients/README.md`.

Global context (not client-specific) stays in `context/`:
- `context/style-guide.md` — universal grammar, formatting, writing rules (including no-hyphens rule)
- `context/cro-best-practices.md` — conversion optimisation principles
- `context/ai-brand-visibility.md` — strategy for getting brands cited in LLM/AI answers (Brian Dean); consult when planning content marketing strategy, content distribution, or off-site brand building

## Content Pipeline

```
Google Sheet queue → src/content/geo_batch_runner.py → content/[abbr]/[type]/
Topic queue file  → src/content/publish_scheduled.py → content/[abbr]/[type]/  (cron-driven, no Sheet)
```

Slash command pipeline (interactive):
`topics/` → `research/` (briefs) → `drafts/` (articles) → `review-required/` → `published/`

Rewrites: `rewrites/` | Landing pages: `landing-pages/` | Audits: `audits/`

## Content Types

The batch runner and agents support 5 content types, selected via Column E in the Google Sheet:

| Type | Agent | Word Count | Use for |
|------|-------|------------|---------|
| `service` | `service-page-writer.md` | 400–600 | Individual treatment/service pages |
| `location` | `location-page-writer.md` | 450+ | District, neighbourhood, or postcode-level location pages |
| `pillar` | `pillar-page-writer.md` | 700–1000 | GBP category landing pages (hub pages) |
| `topical` | `topical-writer.md` | 600–1000 | Informational/question-based articles |
| `blog` | `blog-post-writer.md` | 600–1200 | Conversational blog posts |
| `news` | `blog-post-writer.md` | 600–1200 | News-angle posts (e.g. Glasgow News category); hook is optional in quality gate |
| `comp-alt` | `competitor-alt-writer.md` | 500–700 | Competitor alternative / comparison pages |
| `problem` | `problem-page-writer.md` | 600–800 | Condition/symptom pages with authority outbound links |

Default: `blog` if Column E is empty.

## Batch Runner

```bash
python3 src/content/geo_batch_runner.py             # process all "Write Now" rows
python3 src/content/geo_batch_runner.py A2:E5       # specific range only
python3 src/content/geo_batch_runner.py --publish   # generate + publish to WordPress as draft
```

Google Sheet columns: A=Topic/Location, B=Status (`Write Now`/`DONE`/`pause`/`Images o/s`/`Review`/`Publish`), C=Cost (auto), D=Business abbreviation, E=Content type, F=File path (auto-set on `Images o/s`/`Review`, cleared on DONE), G=Notes (quality failures on `Review`, cleared on DONE), H=Review count (increments each time a row is flagged `Review`), I=Niche (set by `research_blog_topics.py --sheet`; read-only for batch runner).

Output: `content/[abbr]/[type]/[slug]-[date]/[slug]-[date].html` (one folder per article; images saved alongside HTML)

**Scheduled publisher** — `src/content/publish_scheduled.py` publishes one topic per cron run from a JSON queue file, bypassing the Google Sheet entirely. Default queue: `research/[abbr]/topic-queue.json`. Use `--queue <filename>` to point at a different queue file (e.g. `comp-alt-queue.json`). Generate blog queues with `research_blog_topics.py --queue [--cadence N]`; comp-alt queues are hand-curated JSON files. Each run: picks next `pending` topic → generates content → quality gate → publishes to WordPress → marks topic `published`/`failed`/`review_required` in queue → appends to `logs/scheduled-publish-log.csv`. **No per-article emails** — email notifications are suppressed; a daily digest script is planned. Missed-run detection: checks gap since last publish vs cadence + 2-day buffer. `--status` flag prints a formatted queue table (icons: ✓ published · · pending · ⚠ review · ✗ failed). `--dry-run` skips WordPress publish.

**Queue entry format** — each entry supports a `wp_category` field to assign a WordPress category on publish, and a `brief` field to pass client-supplied description text to the writer (service pages only — used as source material, not verbatim copy):
```json
{"topic": "Thai Massage Benefits", "content_type": "blog", "status": "pending", "wp_category": "Thai Massage"}
{"topic": "Couples Thai Massage", "content_type": "service", "status": "pending", "brief": "A shared experience..."}
```

**Comp-alt queue files** — `research/[abbr]/comp-alt-queue.json`. Hand-curated list of competitor names (must match `###` headings in `competitor-analysis.md`). Run via: `python3 src/content/publish_scheduled.py --abbr gtm --queue comp-alt-queue.json`. Always publish via background agent when running multiple topics (see Agent Usage above).

**Problem queue files** — `research/[abbr]/problem-queue.json`. List of conditions/symptoms (e.g. sciatica, headaches, stiff neck). Same topic list shared across all Thai massage clients but content is unique per site (different brand voice, local area, therapist context). Run via: `python3 src/content/publish_scheduled.py --abbr gtm --queue problem-queue.json`. Problem pages include mandatory outbound links to authoritative sources (Wikipedia, NHS, PubMed) found via live web search.

Cron setup: all jobs run via `~/.seomachine-cron.sh <abbr> <queue>` wrapper (handles path-with-spaces; logs to `logs/cron-[abbr].log`). Live cron entries (active):
- GTB Thai Massage (Mon + Thu 09:00): `0 9 * * 1 ~/.seomachine-cron.sh gtb thai-massage-queue.json` and `0 9 * * 4 ~/.seomachine-cron.sh gtb thai-massage-queue.json`
- GTB Stay Healthy (Tue 09:00): `0 9 * * 2 ~/.seomachine-cron.sh gtb stay-healthy-queue.json`
- GTB Glasgow News (Wed 09:00): `0 9 * * 3 ~/.seomachine-cron.sh gtb glasgow-news-queue.json`
- GTB Yoga & Stretching (Fri 09:00): `0 9 * * 5 ~/.seomachine-cron.sh gtb yoga-stretching-queue.json`
- Comp-alt (Wednesdays GTM, Thursdays SDY): `0 10 * * 3 ... --abbr gtm --queue comp-alt-queue.json`

**Directions snippet** — `src/snippets/generate_directions_snippet.py` generates a self-contained HTML+JS Google Maps directions widget per client. Saved to `clients/[abbr]/snippets/[abbr]-directions.html`. The batch runner calls `_ensure_directions_snippet()` automatically on the first publish run per client — no manual step needed. The snippet is injected into `comp-alt` page prompts automatically.

**Quality gate** runs after every article is written. Thresholds are per-content-type (`CONTENT_TYPE_CONFIG` in `quality_gate.py`). Hook and CTAs are mandatory for all types. Default (blog/service/etc.): Flesch ≥ 55, need 2/3 of stories/rhythm/paragraphs. `location`: Flesch ≥ 50, need 2/3 (place names and geographic terms drag down readability scores). `comp-alt`: Flesch ≥ 48, no stories criterion, need 1/2 of rhythm/paragraphs. `problem`: Flesch ≥ 48, no stories, need 1/2 of rhythm/paragraphs (medical/health content is naturally denser). Paragraphs are mandatory for all types. CTA and paragraph analysis runs on body-only text (excludes FAQ section) — FAQ answers naturally run longer. CTA rule: ≥2 CTAs + first within 500 words. Paragraph rule: ≤3 long paragraphs (>3 sentences) in body. Code fences (` ```html ` / ` ``` `) are stripped from both initial generation and rewrite output. If it fails, Claude rewrites with targeted instructions, up to 2 rewrites; 65-second sleep between rewrite attempts to avoid API rate limits. Console output:
```
→ Quality: Flesch 55 ✓ | hook ✓ | ctas ✓ | stories ✗ | rhythm ✓ | paras ✓ — passed
```
On final failure: article is still published to WordPress as a draft with a review notice — `★★★★★` appended to the title and a failure-reasons paragraph injected after the `<h2>`. Status: `published_review` (scheduled publisher) or `Review` with WP draft (batch runner with `--publish`). This lets the user review and edit directly in wp-admin instead of hunting for local HTML files. Queue `--status` shows `✎` icon for these items.

**Review workflow:** open the draft in wp-admin (stars in title make it easy to spot), fix the flagged issues, remove the star notice paragraph and title suffix, then publish. No round-trip through SEO Machine needed.

Quality failures logged to `logs/quality-log.csv` (append-only, gitignored).

## Content Repurposing Pipeline

Two-stage automated pipeline: blog publishes first (existing), then `src/social/repurpose_content.py` runs ~2 hours later, generating video + social media content and scheduling via GoHighLevel.

```bash
python3 src/social/repurpose_content.py --abbr gtm           # process all unrepurposed articles
python3 src/social/repurpose_content.py --abbr gtm --dry-run  # generate content, skip GHL publishing
python3 src/social/repurpose_content.py --abbr gtm --status   # show social publishing status
python3 src/social/repurpose_content.py --abbr gtm --topic "Thai Massage Benefits"  # specific article
```

Cron example (2hr after blog publish):
```
0 11 * * 1 cd /path/to/seomachine && python3 src/social/repurpose_content.py --abbr gtm
```

**Pipeline flow:** Published article → Claude generates video script + social posts → ElevenLabs TTS voiceover → FFmpeg composes long-form video (slides, Ken Burns, text overlays) + 3-5 shorts → GoHighLevel API schedules everything with staggered weekly spread (YouTube Tue, LinkedIn/FB/GBP Wed, X Thu, Instagram Fri, remaining shorts Sat-Sun).

**Modules:**
- `src/social/social_post_generator.py` — Claude-powered video script + social post generation
- `src/social/video_producer.py` — ElevenLabs TTS + FFmpeg video composition (long-form + shorts)
- `data_sources/modules/elevenlabs_tts.py` — ElevenLabs TTS wrapper with timestamp support
- `data_sources/modules/ghl_publisher.py` — GoHighLevel Social Planner API client (Private Integration tokens, media upload, post scheduling)

**Client config:** `elevenlabs.voice_id` for per-client voice, `ghl.location_id` + `ghl.accounts` for platform account IDs. GHL Private Integration tokens stored in `clients/[abbr]/ghl-tokens.json` (gitignored, format: `{"token": "pit-..."}`).

**X format alternation:** Even ISO weeks → thread format, odd weeks → standalone tweets staggered across the week. Controlled by `get_x_format_for_date()` in `ghl_publisher.py`.

**Logging:** `logs/social-publish-log.csv` — tracks repurposed articles, video status, shorts count, GHL post IDs, cost.

**Cost:** ~$2.95/article (Claude ~$0.15 + ElevenLabs TTS ~$2.40 + FFmpeg/Pillow free + GHL free).

**Future:** HeyGen AI avatar swap-in (clean TTS interface), per-client schedule config in config.json.

Set `IMAGE_API_PROVIDER=gemini` in `.env` to generate images automatically. Requires `GOOGLE_AI_API_KEY` and `OPENAI_API_KEY`. Leave blank to skip image generation (content-only mode). Cost: ~$0.27/post (Gemini) or ~$0.16/post (gpt-image-1 fallback).

**Image failure handling:** if image generation fails after 3 Gemini retries (30s/60s/120s backoff), the runner automatically falls back to `gpt-image-1` (OpenAI). If both fail and `--publish` is set, the row is marked `Images o/s` and the file path written to Column F — content is saved locally but not published. Next batch run retries images only (no content regeneration) and publishes on success.

**Nano Banana images** — for standalone/on-demand image generation (not batch runner), use the `nano-banana-images` skill (Kie.ai API, ~$0.04–0.09/image). Say "make me a nano banana image of..." to generate hyper-realistic images via Gemini 3.1 Flash. API key: `KIE_AI_API_KEY` in `.env`.

**Image naming:** `{base-slug}-banner.jpg`, `{heading-slug}.jpg` (section 1), `{base-slug}-faq.jpg` (FAQ section). All names are keyword-rich — no generic `section-1.jpg` filenames.

**Image placement and alignment:**
- Banner (1200×500): `class="aligncenter"`, injected after the first sentence of section 1
- Section image (400×300): `class="alignright"`, after the 3rd paragraph of section 1
- FAQ image (400×300): `class="alignleft"`, 3 paragraphs before the end of section 1
- Section 2 (FAQ accordion): no image injected — both body images appear before FAQ starts

**Banner subject by content type:**
- `location`: banner shows the local area/street scene; section image shows spa treatment
- All other types: banner shows spa/treatment scene

**Image prompt architecture (session 37, corrected sessions 38–41):**
- No template wrapper — each treatment type gets its own topic-specific scene description from `TOPIC_CONTEXT_MAP` in `data_sources/modules/image_generator.py`
- Banner entries show therapist + client performing the treatment (medium/wide shot); section entries show close-up of the specific technique — both always have people
- Unmatched topics fall back to Claude Haiku which generates a treatment-specific prompt (~$0.001/call); console logs `→ Image prompt: Claude fallback (no map match for "X")`
- Treatment reference photo passed to Gemini for both banner and section images (not section only)
- **`SECTION_PHOTO_SUFFIX`** includes universal anatomical grounding rule — all visible body parts must be clearly attached to a person in the scene, never floating or disembodied
- **Image validation layer** — `_validate_image(path, image_type)` sends generated image to Claude Haiku vision API; checks banner for therapist+client visibility and no disembodied parts; checks section for anatomical grounding; returns `(True, '')` or `(False, "ISSUE: reason")`; never raises (returns True on API error). `_generate_validated()` wraps `_generate()` with validation + 1 auto-retry before saving; logs warning if retry also flagged
- **FAQ image variety** — `FAQ_SCENE_POOL` in `image_generator.py` is a list of 6 distinct "client at rest" scenes (foot bath, herbal tea, lying on table, reclining in chair, floating candles, salt lamp); scene selected deterministically by `sum(ord(c) for c in base_slug) % 6` so same page always regenerates to same scene but different pages get different images

**Room reference images (per-client):** `image_settings.room_reference_image` in `clients/[abbr]/config.json` — path to a photo of the actual treatment room. Passed to Gemini as a visual reference so generated images match the real space. `image_settings.room_description` provides the text fallback for gpt-image-1 (which doesn't support image input). Currently configured for SDY only; add to other clients when room photos are available.

**Treatment reference pool (shared):** `assets/image-references/treatments/` — common photos used as style references for banner and section images across all clients. Maps to keywords via `TREATMENT_REFERENCE_MAP` in `image_generator.py`. Current pool: aromatherapy, couples-massage, foot-massage, hair-oiling, oil-massage, swedish-massage, thai-massage. Add new files and map entries here as more treatment photos become available.

**Gemini payload structure:** banners: room reference image (1st) + treatment reference image (2nd) + text prompt. Section images: same. FAQ images: room reference only (no treatment reference — client-at-rest scene, no anatomy risk). gpt-image-1 fallback uses text description only.

## Commands (Slash)

All commands are in `.claude/commands/`. Key commands:

**Research:**
- `/research [topic]` — social research (Reddit/YouTube) → entity mapping → keyword research → section plan; generates brief in `research/`
- `/research-serp "keyword"` — SERP analysis with entity extraction
- `/research-gaps` — competitor keyword gap analysis
- `/research-topics` — topical authority cluster analysis
- `/research-trending` — trending queries from GSC
- `/research-performance` — analytics-driven priorities
- `/research-blog-topics [abbr]` — keyword-driven blog topic ideas with competitor SERP analysis; niche cache shared across clients (30-day TTL); add `--sheet` to push to Google Sheet (status: pause)

**Writing:**
- `/write [topic]` — full article in `drafts/`, auto-triggers SEO agents
- `/article [topic]` — simplified article creation
- `/rewrite [topic]` — update existing content
- `/geo-batch` — batch content from Google Sheet (runs `src/content/geo_batch_runner.py`)

**Publishing & Optimisation:**
- `/publish-draft [file]` — publish to WordPress via REST API
- `/optimize [file]` — final SEO polish pass
- `/analyze-existing [URL or file]` — content health audit
- `/audit [abbr or URL]` — full 6-category SEO audit; outputs internal markdown report + OMG-branded prospect PDF + pending content queue; runs `src/audit/run_audit.py`
- `/cluster [topic]` — topic cluster strategy

**Landing Pages:**
- `/landing-write`, `/landing-audit`, `/landing-research`, `/landing-publish`, `/landing-competitor`

## Agents

Located in `.claude/agents/`. Content writers:
- `service-page-writer.md`, `location-page-writer.md`, `pillar-page-writer.md`
- `topical-writer.md`, `blog-post-writer.md`, `competitor-alt-writer.md`, `problem-page-writer.md`

All 7 content writers include 2-3 inline booking CTAs (short anchor text, 3-6 words), maximum 3 sentences per paragraph, and output **three HTML blocks**:
1. `<!-- SECTION 1 -->` — main body
2. `<!-- SECTION 2 FAQ -->` — collapsible accordion using `<details>`/`<summary>` (no JS/CSS)
3. `<!-- SCHEMA -->` — JSON-LD with `@graph` containing the primary type (`Article`/`BlogPosting`/`Service`/`WebPage`), `FAQPage`, and `LocalBusiness` on every page; primary type includes `speakable: {"@type": "SpeakableSpecification", "cssSelector": [...]}` targeting headings, first paragraph, and FAQ elements; service pages also include a `WebPage` node (speakable not valid on `Service` type)

SEO/optimisation agents (auto-run after `/write`):
- `seo-optimizer.md`, `meta-creator.md`, `internal-linker.md`, `keyword-mapper.md`
- `content-analyzer.md`, `editor.md`, `headline-generator.md`, `cro-analyst.md`
- `performance.md`, `cluster-strategist.md`

## SEO Approach

Content is written entity-first, not keyword-first. See `clients/[abbr]/seo-guidelines.md`.

Key principle: identify the primary entity and 3–5 secondary entities before writing. Entity co-occurrence and salience take priority over keyword density targets. The `/research` command now outputs an Entity Map as its first section.

## WordPress Integration

Publishing uses the WordPress REST API. Credentials are stored in `clients/[abbr]/config.json` under the `wordpress` key. The custom MU-plugin (`wordpress/seomachine.php`) registers 5 custom post types and exposes SEO meta fields via REST — no Yoast dependency.

**SiteGround hosting note:** deploy to `wp-content/mu-plugins/` (plural). SiteGround also has a `mu-plugin/` (singular) folder which is display-only — WordPress does not auto-load PHP files from it.

**Auto-deploy:** `.github/workflows/deploy-plugin.yml` deploys `wordpress/seomachine.php` and `wordpress/seomachine-hub.css` to all 5 sites automatically on every push to `main` that touches either file. Three parallel jobs: GTM/GTB (`u2168-sqqieazmgeuw@ukm1.siteground.biz`), SDY + staging2 (`u2732-2mxetksmslhk@gukm1055.siteground.biz`), and TMG/TMB (`u3520-kztrwuly6pid@uk1001.siteground.eu`). The SDY job deploys to both `serendipitymassage.co.uk` and `staging2.serendipitymassage.co.uk`. Uses `SITEGROUND_SSH_KEY` GitHub Actions secret (private key at `~/.ssh/seomachine_deploy`).

`WordPressPublisher.from_config(wp_config)` accepts credentials directly from the client JSON.

**Batch runner publishing** uses `publish_html_content()` — extracts title from `<h2>`, uploads all local images to WP media library (rewriting relative `src` to absolute URLs), sets first image as featured image. The original topic/address from the Sheet is passed as `excerpt` — this powers the `[seo_hub]` shortcode display text.

**CSS class injection** — `publish_html_content()` automatically injects CSS classes into all headings and paragraphs before sending to WordPress. Class map: `h1→hdr-xl`, `h2→hdr-l`, `h3→hdr-m`, `h4→hdr-s`, `h5→hdr-xs`, `p→txt-m`, `small→txt-s`. Elements with an existing `class` attribute are left untouched (preserves intentional overrides). FAQ `<h2>` outputs `class="hdr-m"` from the agent so it is kept as `hdr-m`, not overridden to `hdr-l`. To backfill classes on already-published posts:
```bash
python3 src/publishing/update_post_classes.py --abbr sdy --type service
python3 src/publishing/update_post_classes.py --abbr gtm --type all
python3 src/publishing/update_post_classes.py --abbr sdy --type all --dry-run
python3 src/publishing/inject_elementor_template.py --template-id 22698          # inject into all GTB posts (default)
python3 src/publishing/inject_elementor_template.py --template-id 22698 --dry-run
python3 src/publishing/inject_elementor_template.py --template-id 22698 --post-id 12345  # single post test
python3 src/publishing/inject_elementor_template.py --template-id 22698 --abbr gtm       # different client
```

**Re-publishing existing HTML files** (without regenerating content):
```bash
python3 src/content/republish_existing.py                # republish all gtm location files
python3 src/content/republish_existing.py --type service # service pages
python3 src/content/republish_existing.py --abbr gtm --type blog
python3 src/content/regen_images.py --abbr sdy --folders "hair-oiling-treatment-2026-04-06,thai-facial-massage-2026-03-28" --type service  # regenerate images for specific pages
```
Use this when posts need to be re-created in WordPress (e.g. after enabling Elementor CPT support).

**Custom post types** — content is published to the correct CPT based on content type. Mapping is in `clients/[abbr]/config.json` under `wordpress.content_type_map`. CPTs: `seo_service`, `seo_location`, `seo_pillar`, `seo_topical`, `seo_comp_alt`, `seo_problem`. **`blog` content type maps to the standard WordPress `post` type** (not a CPT) so posts appear in normal blog loops, RSS feeds, and category archives. `seo_blog` CPT retained in plugin for backward compatibility only. All CPTs grouped under "SEO Content" in wp-admin. SEO meta fields (`seo_meta` REST field) work without Yoast — keys are Yoast-compatible so they display in Yoast UI if installed.

**SEO Machine admin panel** — "SEO Machine" metabox registered on all 7 CPTs and standard `post` type. Currently shows Target Keyword field, saved to `_seo_machine_focus_keyword` meta key (no third-party plugin references). Plain WP styling for now; brand styling planned before public/commercial release.

**WordPress category support** — `publish_scheduled.py` reads `wp_category` from each queue entry and passes it through to the publisher. `publish_html_content()` accepts a `category` param; auto-creates the WordPress category if it doesn't exist and assigns it on publish. Works on both Elementor and non-Elementor paths. The built-in `category` taxonomy is registered for the `post` type natively; no extra registration needed.

**Elementor template publishing** (used when `clients/[abbr]/elementor-template.json` exists):
1. Run `python3 src/publishing/fetch_elementor_template.py [abbr]` once to capture the saved template (reads `wordpress.elementor_template_id` from config). Skips SSL verification automatically for `.local` domains. Saves a `clients/[abbr]/elementor-template-meta.json` sidecar with the WP `modified` date.
2. Before every publish, the batch runner checks whether the template has been updated in WordPress (compares `modified` date via REST API) and auto-re-fetches if stale. Prints `→ Template: up to date` or `→ Template updated in WordPress — re-fetching...`. Checked once per client per run.
2. On `--publish`, article HTML is injected into the template's HTML widget(s); first `<h2>` stripped (template has H1 title widget); schema `<script>` appended directly; list spacing fixed via inline styles
3. Post created as the correct CPT (e.g. `seo_location`) with `_elementor_data` + `_elementor_edit_mode: builder` meta

**Two-section injection mode** (SDY template): if the template contains HTML widgets with `<!-- S1 CONTENT -->` and `<!-- S2 CONTENT -->` markers, the injector splits automatically — Section 1 body → S1 widget, FAQ accordion → S2 widget (with schema appended). The Button section between them is left untouched. Falls back to single-widget mode (GTM) if markers are absent.

**GTM config:** `clients/gtm/config.json` — `wordpress.elementor_template_id: 16508`, `wordpress.content_type_map` maps all 5 types to CPT slugs

**SDY config:** `clients/sdy/config.json` — `wordpress` block points to live (`serendipitymassage.co.uk`); `wordpress_local` preserves local credentials; `wordpress_live` is a legacy block (same as `wordpress` now). `ssh` block includes `wp_path` — triggers WP-CLI publish path automatically.

**SiteGround cache auto-purge** — `_purge_sg_cache()` in `WordPressPublisher` runs `sg_cachepress_purge_everything()` via WP-CLI SSH at the end of every successful `publish_html_content()` call. Requires `wp_path` in the client's `ssh` block. Currently active for GTM, SDY, and TMG. Silent no-op for clients without `ssh_config` or `wp_path`. Console output: `→ Cache: purged`. This ensures cross-site hub shortcodes on secondary blog sites (GTB, TMB) see fresh content immediately after publish — SiteGround otherwise serves cached empty REST responses to server-to-server PHP requests.

**WP-CLI SSH publish path** — `WordPressPublisher` detects `ssh_config.wp_path` and routes all publishing through WP-CLI commands over SSH instead of the REST API. Required for SiteGround-hosted sites: SiteGround's CDN returns 202 bot-challenge pages for unauthenticated REST requests from non-browser IPs, and also disables SSH port forwarding (`AllowTcpForwarding no`), making direct API tunneling impossible. The WP-CLI path: creates the WP draft via `wp post create`, transfers images via SCP + `wp media import`, applies Elementor JSON via `wp eval file_get_contents()`. Add `"wp_path": "/home/[user]/www/[domain]/public_html"` to the `ssh` block in `config.json` to activate. `from_config(wp_config, ssh_config=ssh_config)` is the call signature — `ssh_config` is propagated from `business_config.get('ssh')` in both `publish_scheduled.py` and `geo_batch_runner.py`.

**Elementor CPT auto-enable** — `seomachine.php` filters `option_elementor_cpt_support` and `default_option_elementor_cpt_support` to auto-enable all 5 CPTs in Elementor without manual checkbox step. No Elementor → Settings action required on new installs.

**Hub page shortcode** — `[seo_hub type="location"]` registered in `seomachine.php`. Place in an Elementor Shortcode widget (not HTML widget). Renders a `<ul class="seo-hub-links">` of all published posts of that type, sorted A–Z, each wrapped in `<li><h3><a>`. Display text = post excerpt if set, otherwise post title. Supported types: `location`, `service`, `pillar`, `topical`, `blog`, `comp_alt`, `problem`. `[seo_hub type="problem"]` renders a 3-column CSS grid with bordered cards, disc bullets, inherited link colours, mobile-responsive (stacks to 1 column) via `seo_hub_problem_grid()`. Must be deployed to `wp-content/mu-plugins/seomachine.php` (not inside `plugins/`).

**Cross-site hub (blog subdomains)** — on blog subdomains (GTB, TMB), set `wp option update seo_hub_source "https://main-site-url.com"`. The shortcode fetches posts from the main site's REST API (no auth needed — public CPTs) and caches results for 12 hours. The `blog` type always queries locally. Override per-shortcode: `[seo_hub type="location" source="https://..."]`. Cache bust: `wp transient delete seo_hub_cache_location`. **Lite mode (v3.2.0):** setting `seo_hub_source` also automatically suppresses all 6 CPTs and the "SEO Content" admin menu on secondary blog sites — no manual step needed. A blue info notice in Settings → General confirms lite mode is active.

**Schema handling (non-Elementor)**: `_wrap_schema_block()` moves the `<!-- SCHEMA --><script>` block into a Gutenberg `<!-- wp:html -->` block. The `[DATE]` placeholder is replaced with today's ISO date by the batch runner before saving.

**Sitewide LocalBusiness JSON-LD** (v3.4.0) — `seomachine.php` outputs a `LocalBusiness` schema block in `<head>` on the front page and all singular pages, populated from WP options. Opt-in per install: only outputs if `seo_machine_biz_name` option is set. Set via WP-CLI: `seo_machine_biz_name`, `seo_machine_biz_phone`, `seo_machine_biz_street`, `seo_machine_biz_locality`, `seo_machine_biz_postcode`, `seo_machine_biz_country`, `seo_machine_biz_schema_type`, `seo_machine_opening_hours` (JSON array of `OpeningHoursSpecification` objects). Currently configured on SDY staging2.

**Sitemap redirect** (v3.4.0) — `seomachine.php` 301-redirects `/sitemap.xml` → `/wp-sitemap.xml` (WordPress core's full sitemap including all public CPTs) and adds a `Sitemap:` directive to `robots.txt`. Ensures Google discovers all CPT pages without requiring Yoast/Rank Math.

## Project Structure

All Python executables live in `src/` under module subfolders. Test scripts live in `tests/`. Modules (imported by scripts) stay in `data_sources/modules/`. GCP service account keys go in `config/`.

```
src/
  content/      ← geo_batch_runner.py, republish_existing.py, publish_scheduled.py, regen_images.py
  research/     ← research_competitors.py, research_quick_wins.py, research_serp_analysis.py, etc.
  publishing/   ← fetch_elementor_template.py, update_post_classes.py, inject_elementor_template.py
  snippets/     ← generate_directions_snippet.py
  social/       ← repurpose_content.py, video_producer.py, social_post_generator.py
  audit/        ← run_audit.py, collectors.py, scoring.py, report.py, pdf_gen.py, queue_gen.py
  citations/    ← run_citations.py (CLI entry point)
  competitors/  ← competitor alternative page generators (future)
tests/          ← test scripts (delete before production)
data_sources/   ← importable modules (google_sheets, wordpress_publisher, elevenlabs_tts, ghl_publisher, etc.)
config/         ← service account keys (gitignored)
clients/        ← per-client context and config
```

Scripts in `src/` subfolders resolve the project root as `Path(__file__).parent.parent.parent`, so all paths (`content/`, `clients/`, `.env`) still resolve correctly when run from the project root.

## Python Analysis Pipeline

Located in `data_sources/modules/`. Scripts in `src/`:

```bash
python3 src/research/research_quick_wins.py
python3 src/research/research_competitor_gaps.py
python3 src/research/research_serp_analysis.py "keyword"
python3 src/research/research_topic_clusters.py
python3 src/research/research_trending.py
python3 src/research/research_competitors.py --abbr gtm   # full competitor research (map pack + organic + profiles)
python3 src/research/research_blog_topics.py --abbr gtb   # blog topic ideas (niche cache, 30-day TTL)
python3 src/research/research_blog_topics.py --abbr gtb --sheet   # also push to Sheet (status: pause)
python3 src/research/research_blog_topics.py --abbr gtb --refresh  # force cache refresh
python3 src/research/research_blog_topics.py --abbr gtb --queue    # write topic-queue.json for scheduled publishing
python3 src/research/research_blog_topics.py --abbr gtb --queue --cadence 14  # fortnightly cadence
python3 src/content/publish_scheduled.py --abbr gtb          # publish next topic from queue
python3 src/content/publish_scheduled.py --abbr gtb --status # show queue status table
python3 src/content/publish_scheduled.py --abbr gtb --dry-run  # generate + quality-check, skip WP publish
python3 src/content/publish_scheduled.py --abbr gtm --queue comp-alt-queue.json          # comp-alt queue
python3 src/content/publish_scheduled.py --abbr gtm --queue comp-alt-queue.json --status # comp-alt status
python3 tests/test_dataforseo.py    # test API connectivity
python3 src/reporting/daily_digest.py                    # send today's digest email
python3 src/reporting/daily_digest.py --date 2026-04-07  # specific date
python3 src/reporting/daily_digest.py --dry-run          # print without sending
python3 src/audit/run_audit.py --abbr gtm                # full SEO audit (existing client)
python3 src/audit/run_audit.py --abbr gtm --no-pdf       # audit, skip PDF generation
python3 src/audit/run_audit.py --url https://... --name "Business" --no-email  # prospect audit
python3 src/citations/run_citations.py --abbr gtm                  # full: audit + create missing
python3 src/citations/run_citations.py --abbr gtm --mode audit     # check only, no submissions
python3 src/citations/run_citations.py --abbr gtm --mode create    # create missing only
python3 src/citations/run_citations.py --abbr gtm --status         # citation status table
python3 src/citations/run_citations.py --abbr gtm --dry-run        # audit without submitting
python3 src/citations/run_citations.py --abbr gtm --force          # re-check all sites
```

**`run_citations.py`** — tiered citation audit and creation across 23 UK directory sites. Four tiers: Tier 1 (direct API: Yelp, Foursquare, GBP), Tier 2 (DataForSEO: TrustPilot, TripAdvisor, Facebook, etc.), Tier 3 (Playwright scrape + form fill: Yell, Thomson Local, Scoot, etc.), Tier 4 (manual HTML pack). State stored at `clients/[abbr]/citations/state.json` with 30-day staleness cadence. Manual pack at `clients/[abbr]/citations/manual-pack.html` for Tier 4 + Tier 3 fallbacks. Citation score (0–15 pts) replaces the old NAP-only section in `/audit` output — full audit runs `collect_citations()` automatically when `abbreviation` is in config.json. Modules: `citation_sites.py` (master site list), `citation_checker.py` (presence checks), `citation_submitter.py` (form fills), `citation_manual_pack.py` (HTML pack generator), `citation_manager.py` (orchestrator), `citation_state.py` (state load/save), `nap_utils.py` (shared NAP normalisation).

**Shareable citation pack** — `generate_shareable_pack()` in `citation_manual_pack.py` generates `clients/[abbr]/citations/manual-pack-shareable.md` alongside the HTML pack on every run. Plain-text format optimised for copy-paste into WhatsApp or email: numbered lists with bare URLs (auto-linked by messaging apps), ASCII separators, four sections (general directories / associations / niche directories / competitor gaps), each with a plain-English instruction paragraph, NAP block at the bottom. Returns `(path, content)` tuple — content is directly usable by a future API endpoint without reading the file. Auto-generated whenever `generate_manual_pack()` runs.

**Competitor citation gap analysis** — `src/research/research_citation_gaps.py` reverse-engineers where top GBP competitors are cited and identifies directories where they appear but you don't. Runs automatically on the first citation audit per client (stored in `state.json` as `competitor_gaps_run`); re-run on demand via `python3 src/citations/run_citations.py --abbr sdy --competitor-gaps`. Results saved to `clients/[abbr]/citations/gap-results.json` and automatically rendered as a third section in `manual-pack.html`. Add `--discover` flag to also run DataForSEO backlinks analysis for net-new directory sites not in the standard list. Standalone: `python3 src/research/research_citation_gaps.py --abbr sdy [--top 10] [--discover] [--dry-run]`. Cost: ~$0.35/run (115 SERP queries for 5 competitors × 23 sites).

**Niche/industry directories** — `citation_sites.py` also contains `NICHE_CITATION_SITES: dict[str, list[CitationSite]]` keyed by `config.json["niche"]`. These are industry-specific associations and directories that supplement the generic 23-site list. Currently defined for `"massage-therapy"` (shared with `"thai-massage"`): SMTO, CNHC, FHT, CThA (associations requiring qualifications + PI insurance) + Therapy Directory, Heal Scotland, Natural Therapy Pages UK, Healthy Pages, Holistic Pages, Guru Directory (niche directories). The manual pack generator automatically renders a separate "Industry & Association Directories" section when `niche` is set in `config.json`. To add a new niche, add an entry to `NICHE_CITATION_SITES` in `citation_sites.py` — no other files need changing.

**`run_audit.py`** — full SEO audit script. Runs 6 scored checks (schema 20pts, content 20pts, GBP 20pts, reviews 15pts, NAP 15pts, technical 10pts) + competitor benchmark. Outputs: `audits/[abbr]/[date]/audit-internal.md` (raw data), `audit-prospect.html/pdf` (OMG-branded PAS report), `pending-queue.json` (content gaps as pending queue items). PDF emailed to `kmmsubs@gmail.com` on completion. **Note:** SiteGround's bot protection blocks unauthenticated web scraping — schema/technical collectors use WP app password auth to bypass this. Requires `playwright` + `playwright install chromium` for PDF generation (gracefully skips to HTML if not installed).

**`research_competitors.py`** — standalone competitor intelligence script. Reads `clients/[abbr]/config.json`, geocodes the `area` field via Nominatim (strips "City Centre" etc. before geocoding), queries DataForSEO for top 10 map pack results (`location_name` approach) + top 10 organic (UK, location code 2826), filters directory domains, scrapes each competitor site, extracts structured profiles via Claude Haiku, writes `clients/[abbr]/competitor-analysis.md`. Integrated into `/new-client` workflow as Step 5.

`dataforseo.get_maps_pack()` accepts both `location_name` (e.g. `"Glasgow,Scotland,United Kingdom"`) and `location_coordinate` (e.g. `"55.86,-4.25,10000"`).
