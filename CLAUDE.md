# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session Start

At the start of every new session, automatically invoke `/start` before responding to anything else.

## Agent Usage

Offload research, writing, file operations, and batch tasks to sub-agents wherever possible to keep the main conversation context clean. Prefer `run_in_background: true` for any task that doesn't need its result before the next step.

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
  sdy/                  ← Serendipity Massage Therapy & Wellness (live, batch publishing active)
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

Global context (not client-specific) stays in `context/`:
- `context/style-guide.md` — universal grammar, formatting, writing rules (including no-hyphens rule)
- `context/cro-best-practices.md` — conversion optimisation principles

## Content Pipeline

```
Google Sheet queue → src/content/geo_batch_runner.py → content/[abbr]/[type]/
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
| `comp-alt` | `competitor-alt-writer.md` | 500–700 | Competitor alternative / comparison pages |

Default: `blog` if Column E is empty.

## Batch Runner

```bash
python3 src/content/geo_batch_runner.py             # process all "Write Now" rows
python3 src/content/geo_batch_runner.py A2:E5       # specific range only
python3 src/content/geo_batch_runner.py --publish   # generate + publish to WordPress as draft
```

Google Sheet columns: A=Topic/Location, B=Status (`Write Now`/`DONE`/`pause`/`Images o/s`/`Review`/`Publish`), C=Cost (auto), D=Business abbreviation, E=Content type, F=File path (auto-set on `Images o/s`/`Review`, cleared on DONE), G=Notes (quality failures on `Review`, cleared on DONE), H=Review count (increments each time a row is flagged `Review`).

Output: `content/[abbr]/[type]/[slug]-[date]/[slug]-[date].html` (one folder per article; images saved alongside HTML)

**Directions snippet** — `src/snippets/generate_directions_snippet.py` generates a self-contained HTML+JS Google Maps directions widget per client. Saved to `clients/[abbr]/snippets/[abbr]-directions.html`. The batch runner calls `_ensure_directions_snippet()` automatically on the first publish run per client — no manual step needed. The snippet is injected into `comp-alt` page prompts automatically.

**Quality gate** runs after every article is written. Checks Flesch Reading Ease ≥ 55 (readability) and engagement (hook + CTAs mandatory; mini-stories, rhythm, paragraphs — 2/3 optional). If it fails, Claude rewrites with targeted instructions, up to 2 rewrites. Console output:
```
→ Quality: Flesch 55 ✓ | hook ✓ | ctas ✓ | stories ✗ | rhythm ✓ | paras ✓ — passed
```
On final failure: best rewrite saved to disk, row marked `Review` in Sheet, failures written to Column G, publish skipped.

**Review workflow:** manually edit the HTML file (path in Column F, failures in Column G), then set Column B to `Publish`. Next batch run publishes the file without regenerating content, marks DONE, clears G and F.

Quality failures logged to `logs/quality-log.csv` (append-only, gitignored).

Set `IMAGE_API_PROVIDER=gemini` in `.env` to generate images automatically. Requires `GOOGLE_AI_API_KEY` and `OPENAI_API_KEY`. Leave blank to skip image generation (content-only mode). Cost: ~$0.27/post (Gemini) or ~$0.16/post (DALL-E 3 fallback).

**Image failure handling:** if image generation fails after 3 Gemini retries (30s/60s/120s backoff), the runner automatically falls back to DALL-E 3. If both fail and `--publish` is set, the row is marked `Images o/s` and the file path written to Column F — content is saved locally but not published. Next batch run retries images only (no content regeneration) and publishes on success.

**Image naming:** `{base-slug}-banner.jpg`, `{heading-slug}.jpg` (section 1), `{base-slug}-faq.jpg` (FAQ section). All names are keyword-rich — no generic `section-1.jpg` filenames.

**Image placement and alignment:**
- Banner (1200×500): `class="aligncenter"`, injected after the first sentence of section 1
- Section image (400×300): `class="alignright"`, after the 3rd paragraph of section 1
- FAQ image (400×300): `class="alignleft"`, 3 paragraphs before the end of section 1
- Section 2 (FAQ accordion): no image injected — both body images appear before FAQ starts

**Banner subject by content type:**
- `location`: banner shows the local area/street scene; section image shows spa treatment
- All other types: banner shows spa/treatment scene

## Commands (Slash)

All commands are in `.claude/commands/`. Key commands:

**Research:**
- `/research [topic]` — social research (Reddit/YouTube) → entity mapping → keyword research → section plan; generates brief in `research/`
- `/research-serp "keyword"` — SERP analysis with entity extraction
- `/research-gaps` — competitor keyword gap analysis
- `/research-topics` — topical authority cluster analysis
- `/research-trending` — trending queries from GSC
- `/research-performance` — analytics-driven priorities

**Writing:**
- `/write [topic]` — full article in `drafts/`, auto-triggers SEO agents
- `/article [topic]` — simplified article creation
- `/rewrite [topic]` — update existing content
- `/geo-batch` — batch content from Google Sheet (runs `src/content/geo_batch_runner.py`)

**Publishing & Optimisation:**
- `/publish-draft [file]` — publish to WordPress via REST API
- `/optimize [file]` — final SEO polish pass
- `/analyze-existing [URL or file]` — content health audit
- `/cluster [topic]` — topic cluster strategy

**Landing Pages:**
- `/landing-write`, `/landing-audit`, `/landing-research`, `/landing-publish`, `/landing-competitor`

## Agents

Located in `.claude/agents/`. Content writers:
- `service-page-writer.md`, `location-page-writer.md`, `pillar-page-writer.md`
- `topical-writer.md`, `blog-post-writer.md`

All 5 content writers output **three HTML blocks**:
1. `<!-- SECTION 1 -->` — main body
2. `<!-- SECTION 2 FAQ -->` — collapsible accordion using `<details>`/`<summary>` (no JS/CSS)
3. `<!-- SCHEMA -->` — JSON-LD with `@graph` containing the primary type (`Article`/`BlogPosting`/`Service`/`WebPage`), `FAQPage`, and `LocalBusiness` on every page

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

`WordPressPublisher.from_config(wp_config)` accepts credentials directly from the client JSON.

**Batch runner publishing** uses `publish_html_content()` — extracts title from `<h2>`, uploads all local images to WP media library (rewriting relative `src` to absolute URLs), sets first image as featured image. The original topic/address from the Sheet is passed as `excerpt` — this powers the `[seo_hub]` shortcode display text.

**Re-publishing existing HTML files** (without regenerating content):
```bash
python3 src/content/republish_existing.py                # republish all gtm location files
python3 src/content/republish_existing.py --type service # service pages
python3 src/content/republish_existing.py --abbr gtm --type blog
```
Use this when posts need to be re-created in WordPress (e.g. after enabling Elementor CPT support).

**Custom post types** — content is published to the correct CPT based on content type. Mapping is in `clients/[abbr]/config.json` under `wordpress.content_type_map`. CPTs: `seo_service`, `seo_location`, `seo_pillar`, `seo_topical`, `seo_blog`, `seo_comp_alt`. All grouped under "SEO Content" in wp-admin. SEO meta fields (`seo_meta` REST field) work without Yoast — keys are Yoast-compatible so they display in Yoast UI if installed.

**Elementor template publishing** (used when `clients/[abbr]/elementor-template.json` exists):
1. Run `python3 src/publishing/fetch_elementor_template.py [abbr]` once to capture the saved template (reads `wordpress.elementor_template_id` from config). Skips SSL verification automatically for `.local` domains. Saves a `clients/[abbr]/elementor-template-meta.json` sidecar with the WP `modified` date.
2. Before every publish, the batch runner checks whether the template has been updated in WordPress (compares `modified` date via REST API) and auto-re-fetches if stale. Prints `→ Template: up to date` or `→ Template updated in WordPress — re-fetching...`. Checked once per client per run.
2. On `--publish`, article HTML is injected into the template's HTML widget(s); first `<h2>` stripped (template has H1 title widget); schema `<script>` appended directly; list spacing fixed via inline styles
3. Post created as the correct CPT (e.g. `seo_location`) with `_elementor_data` + `_elementor_edit_mode: builder` meta

**Two-section injection mode** (SDY template): if the template contains HTML widgets with `<!-- S1 CONTENT -->` and `<!-- S2 CONTENT -->` markers, the injector splits automatically — Section 1 body → S1 widget, FAQ accordion → S2 widget (with schema appended). The Button section between them is left untouched. Falls back to single-widget mode (GTM) if markers are absent.

**GTM config:** `clients/gtm/config.json` — `wordpress.elementor_template_id: 16508`, `wordpress.content_type_map` maps all 5 types to CPT slugs

**SDY config:** `clients/sdy/config.json` — `wordpress` block points to live (`serendipitymassage.co.uk`); `elementor_template_id: 564`; `wordpress_local` block preserves local credentials for reference

**Elementor CPT auto-enable** — `seomachine.php` filters `option_elementor_cpt_support` and `default_option_elementor_cpt_support` to auto-enable all 5 CPTs in Elementor without manual checkbox step. No Elementor → Settings action required on new installs.

**Hub page shortcode** — `[seo_hub type="location"]` registered in `seomachine.php`. Place in an Elementor Shortcode widget (not HTML widget). Renders a `<ul class="seo-hub-links">` of all published posts of that type, sorted A–Z, each wrapped in `<li><h3><a>`. Display text = post excerpt if set, otherwise post title. Supported types: `location`, `service`, `pillar`, `topical`, `blog`. Must be deployed to `wp-content/mu-plugins/seomachine.php` (not inside `plugins/`).

**Schema handling (non-Elementor)**: `_wrap_schema_block()` moves the `<!-- SCHEMA --><script>` block into a Gutenberg `<!-- wp:html -->` block. The `[DATE]` placeholder is replaced with today's ISO date by the batch runner before saving.

## Project Structure

All Python executables live in `src/` under module subfolders. Test scripts live in `tests/`. Modules (imported by scripts) stay in `data_sources/modules/`. GCP service account keys go in `config/`.

```
src/
  content/      ← geo_batch_runner.py, republish_existing.py
  research/     ← research_competitors.py, research_quick_wins.py, research_serp_analysis.py, etc.
  publishing/   ← fetch_elementor_template.py
  snippets/     ← generate_directions_snippet.py
  competitors/  ← competitor alternative page generators (future)
tests/          ← test scripts (delete before production)
data_sources/   ← importable modules (google_sheets, wordpress_publisher, etc.)
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
python3 tests/test_dataforseo.py    # test API connectivity
```

**`research_competitors.py`** — standalone competitor intelligence script. Reads `clients/[abbr]/config.json`, geocodes the `area` field via Nominatim (strips "City Centre" etc. before geocoding), queries DataForSEO for top 10 map pack results (`location_name` approach) + top 10 organic (UK, location code 2826), filters directory domains, scrapes each competitor site, extracts structured profiles via Claude Haiku, writes `clients/[abbr]/competitor-analysis.md`. Integrated into `/new-client` workflow as Step 5.

`dataforseo.get_maps_pack()` accepts both `location_name` (e.g. `"Glasgow,Scotland,United Kingdom"`) and `location_coordinate` (e.g. `"55.86,-4.25,10000"`).
