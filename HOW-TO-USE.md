# SEO Machine — How to Use

A Claude Code workspace for creating SEO-optimised content at scale. Uses custom slash commands, specialised AI agents, a Python batch runner, and Google Sheets integration to research, write, and publish content for multiple business clients.

---

## Table of Contents

1. [What This Tool Does](#what-this-tool-does)
2. [Initial Setup](#initial-setup)
3. [Adding a New Client](#adding-a-new-client)
4. [Client Information Checklist](#client-information-checklist)
5. [Slash Commands Reference](#slash-commands-reference)
6. [The Batch Runner](#the-batch-runner)
7. [Content Types](#content-types)
8. [What Gets Generated](#what-gets-generated)
9. [Publishing to WordPress](#publishing-to-wordpress)
10. [Typical Workflows](#typical-workflows)

---

## What This Tool Does

SEO Machine runs inside Claude Code (VS Code extension). You type slash commands in the chat and Claude writes, researches, and publishes content automatically.

The two main ways to generate content:

- **Interactive** — type a slash command, Claude generates one piece of content and hands it back for review
- **Batch** — fill a Google Sheet queue, run a Python script, Claude generates 10–50+ pieces unattended

---

## Initial Setup

### 1. Install Python dependencies

```bash
pip install -r data_sources/requirements.txt
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Then fill in the values. The `.env` file is never committed — it holds all secrets.

### Required credentials

| Variable | What it is | Where to get it |
|----------|------------|-----------------|
| `ANTHROPIC_API_KEY` | Claude API key | console.anthropic.com |
| `GEO_LOCATIONS_SHEET_ID` | Google Sheet ID for the content queue | From the Sheet URL |

### Optional credentials (enable extra features)

| Variable | Feature enabled |
|----------|----------------|
| `GA4_PROPERTY_ID` + `GA4_CREDENTIALS_PATH` | Analytics-based research commands |
| `GSC_SITE_URL` + `GSC_CREDENTIALS_PATH` | Search Console trending/performance data |
| `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` | SERP analysis and keyword research |
| `IMAGE_API_PROVIDER=gemini` + `GOOGLE_AI_API_KEY` | Auto-generate images in the batch runner |
| `GEO_EMAIL_SMTP_*` | Email summary after each batch run |

### Google Sheets setup

1. Create a new Google Sheet with columns: `A=Topic/Location`, `B=Status`, `C=Cost`, `D=Business`, `E=Content Type`
2. Share the Sheet with the service account email from your credentials JSON (give it **Editor** access)
3. Add the Sheet ID to `.env` as `GEO_LOCATIONS_SHEET_ID`

### Google service account setup (for GA4/GSC/Sheets)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → enable Google Analytics Data API, Search Console API, and Google Sheets API
3. Create a service account → download the JSON key
4. Save the JSON to `credentials/ga4-credentials.json`
5. Add the service account email as a Viewer in GA4 and Search Console, and as an Editor in your Google Sheet

---

## Adding a New Client

Run this command and answer the questions — it creates all files automatically:

```
/new-client
```

This creates `clients/[abbr]/` with a `config.json` and 7 stub context files ready to fill in.

To add a client manually:
1. Create `clients/[abbreviation-lowercase]/`
2. Add `config.json` (see schema in `clients/README.md`)
3. Copy the 7 context files from an existing client and update them
4. Add the abbreviation as a dropdown in Column D of the Google Sheet
5. Test with one row: `python3 geo_batch_runner.py A2:E3`

---

## Client Information Checklist

Before generating content for a new client, the following must be filled in. Files marked **Required** will cause poor-quality output if left blank. Files marked **Recommended** improve quality significantly.

### `config.json` — Required

The machine-readable config. Every field below is used by the batch runner.

| Field | Example | Notes |
|-------|---------|-------|
| `name` | `"Glasgow Thai Massage"` | Full trading name |
| `abbreviation` | `"GTM"` | Uppercase, 2–6 letters, must match Column D in the Sheet |
| `website` | `"https://glasgowthaimassage.co.uk"` | Full URL with https:// |
| `address` | `"Floor 3, 142 West Nile Street, Glasgow G1 2RQ"` | Full street address |
| `area` | `"Glasgow City Centre"` | Used in transport directions ("10 minutes from [area]") |
| `postcode` | `"G1 2RQ"` | Postcode only |
| `phone` | `"0141 123 4567"` | Leave as `""` if not public |
| `booking_url` | `"https://example.com/book"` | Leave as `""` if none |
| `keyword_prefix` | `"thai massage"` | The core search phrase, no location |
| `services` | `["Thai massage", "deep tissue", "hot stone"]` | Full list of services offered |
| `wordpress.url` | `"https://example.com"` | WP install URL |
| `wordpress.username` | `"seo-machine"` | WP application password username |
| `wordpress.app_password` | `"Wtg0 jK0T 3bak 7XRg"` | **Not** the login password — generate in WP Admin → Users → Application Passwords |

### `brand-voice.md` — Required

Defines how all content sounds. Without this, content will be generic.

Fill in:
- Brand positioning (what makes this business different, in one sentence)
- 3 voice pillars — what they mean and how they sound in writing
- Writing rules specific to this client (e.g. "never use the word luxury")
- No-go phrases
- How to refer to the business (full name, short form)

### `seo-guidelines.md` — Required

Defines the keyword and entity strategy. Without this, content targets the wrong terms.

Fill in:
- Primary entity (the main thing the business is known for)
- Entity cluster — treatments, conditions, outcomes, people, locations
- Keyword strategy — primary targets, long-tail variations, keywords to avoid
- Content architecture (hub-and-spoke page structure)

### `features.md` — Required

Used in service pages and body copy. Without this, services are described vaguely.

Fill in:
- Each service with description, duration, price (if public), and who it's for
- 3–5 key differentiators — specific, provable claims
- Practical info: parking, accessibility, opening hours, how to book

### `internal-links-map.md` — Recommended

Used by the internal linker agent. Without this, content links to nothing.

Fill in:
- Homepage URL and anchor text examples
- Each service page URL with anchor text
- Each location page URL as pages are created

### `competitor-analysis.md` — Recommended

Helps position content against competitors.

Fill in:
- 2–3 main competitors with website, strengths, weaknesses, and ranking keywords
- Content gaps (topics competitors don't cover well)
- Positioning paragraph

### `target-keywords.md` — Recommended

Informs research and writing priority. Without this, `/research` starts from scratch.

Fill in:
- Tier 1 primary keywords (highest priority)
- Tier 2 secondary keywords
- Tier 3 long-tail / geo targets
- Keywords to avoid

### `writing-examples.md` — Recommended

Teaches the agents the right tone for this client. 2–3 examples from the real website make a noticeable difference.

Fill in:
- 2–3 example passages of good writing (from the website, or written yourself)
- A note on what makes each example good (tone, structure, word choices)

---

## Slash Commands Reference

Type these in the Claude Code chat window. Most accept an argument — if omitted, Claude will ask.

### Session management

| Command | What it does |
|---------|-------------|
| `/start` | Reads `STATUS.md` and picks up from where the last session ended |
| `/wrap` | Closes out the session — updates `STATUS.md` with progress, notes, and next steps |

### Research

| Command | What it does |
|---------|-------------|
| `/research [topic]` | Full research flow — entity mapping, keyword analysis, SERP review. Saves a brief to `research/` |
| `/research-serp "keyword"` | SERP analysis for a specific keyword — entity extraction, top-10 content audit |
| `/research-gaps` | Competitor keyword gap analysis — finds terms competitors rank for that the client doesn't |
| `/research-topics` | Topical authority cluster analysis — surfaces topic clusters to build out |
| `/research-trending` | Trending queries from Google Search Console (requires GSC credentials) |
| `/research-performance` | Analytics-driven priorities — surfaces pages with traffic opportunity (requires GA4) |
| `/priorities` | Combines all research signals into a prioritised content hit list |

### Writing

| Command | What it does |
|---------|-------------|
| `/write [topic]` | Full article — research → write → SEO optimise → internal links → meta. Saves to `drafts/` |
| `/article [topic]` | Simplified single-step article (no full research phase) |
| `/rewrite [topic or file]` | Updates existing content — refreshes facts, improves entity coverage, re-optimises |
| `/geo-batch` | Triggers the batch runner from chat (see [The Batch Runner](#the-batch-runner)) |

### Publishing and optimisation

| Command | What it does |
|---------|-------------|
| `/publish-draft [file]` | Publishes a draft HTML file to WordPress as a draft post |
| `/optimize [file]` | Final SEO polish pass — entity density, headings, internal links, meta |
| `/analyze-existing [URL or file]` | Content health audit — identifies gaps and improvement opportunities |
| `/scrub [file]` | Clean-up pass — removes filler, improves clarity, checks against style guide |

### Strategy

| Command | What it does |
|---------|-------------|
| `/cluster [topic]` | Topic cluster strategy — maps out a hub page plus supporting content |
| `/content-calendar` | Builds a monthly publishing schedule from the keyword and cluster strategy |

### Landing pages

| Command | What it does |
|---------|-------------|
| `/landing-write [topic]` | Writes a conversion-focused landing page |
| `/landing-audit [URL or file]` | Audits a landing page for CRO and SEO issues |
| `/landing-research [topic]` | Researches a landing page angle — competitor pages, messaging hooks |
| `/landing-publish [file]` | Publishes a landing page HTML file to WordPress |
| `/landing-competitor [competitor URL]` | Analyses a competitor landing page |

### Setup

| Command | What it does |
|---------|-------------|
| `/new-client` | Interactive setup wizard — creates the full client folder structure |

---

## The Batch Runner

The batch runner reads a Google Sheet, generates content for every queued row, and optionally publishes to WordPress — all unattended.

### Google Sheet format

| Column A | Column B | Column C | Column D | Column E |
|----------|----------|----------|----------|----------|
| Topic / Location | Status | Cost (auto) | Business | Content Type |
| Byres Road Glasgow | `Write Now` | | GTM | location |
| Thai Massage Glasgow | `Write Now` | | GTM | service |
| 5 Benefits of Deep Tissue | `Write Now` | | GTM | blog |
| Merchant City G1 | `DONE` | $0.43 | GTM | location |
| Sauchiehall Street | `pause` | | GTM | location |

**Column B values:**
- `Write Now` — include in the next run
- `pause` — skip without removing
- `DONE` — done, skip permanently (set back to `Write Now` to regenerate)

**Column C** — written automatically by the script. Do not edit.

**Column D** — must match a folder name in `clients/` exactly (case-insensitive).

**Column E** — controls which agent is used. See [Content Types](#content-types). Defaults to `blog` if empty.

### Running the batch

```bash
# Generate content for all "Write Now" rows
python3 geo_batch_runner.py

# Generate content for a specific range only
python3 geo_batch_runner.py A2:E5

# Generate and publish to WordPress as drafts
python3 geo_batch_runner.py --publish

# Range + publish
python3 geo_batch_runner.py A2:E5 --publish
```

### What happens during a run

1. Reads every row where Column B = `Write Now`
2. For each row: researches the topic, generates content using the correct agent and client context
3. Saves content to `content/[abbr]/[type]/[slug]-[date]/[slug]-[date].html`
4. If `IMAGE_API_PROVIDER` is set: generates 3 images (banner, section, FAQ) and saves alongside the HTML
5. Updates Column B to `DONE` and Column C to the cost (e.g. `$0.43`)
6. If `--publish`: uploads images to WordPress media library, creates draft post in the correct CPT
7. Sends a summary email when done (if email is configured)

### Tips

- **Test first** — run a 2-row range before a full batch to check quality
- **Interruptions** — safe to re-run; rows already marked `DONE` are skipped
- **Rate limits** — the script waits 65 seconds between API calls. Run when Claude Code is idle to avoid conflicts on the same API key
- **Large batches** — for 20+ rows, consider running in segments of 10 to review quality between runs

---

## Content Types

| Type | Word Count | Use for | Agent used |
|------|------------|---------|------------|
| `service` | 400–600 | Individual treatment or service pages | `service-page-writer` |
| `location` | 450+ | District, neighbourhood, or postcode-level location pages | `location-page-writer` |
| `pillar` | 700–1000 | GBP category landing pages (hub pages) | `pillar-page-writer` |
| `topical` | 600–1000 | Informational / question-based articles | `topical-writer` |
| `blog` | 600–1200 | Conversational blog posts | `blog-post-writer` |

---

## What Gets Generated

Every piece of content is a single HTML file with three sections:

1. **Main body** (`<!-- SECTION 1 -->`) — the article or page content
2. **FAQ accordion** (`<!-- SECTION 2 FAQ -->`) — collapsible questions using `<details>`/`<summary>` (no JS or CSS needed)
3. **Schema markup** (`<!-- SCHEMA -->`) — JSON-LD `@graph` block containing the primary type (Article/Service/WebPage), FAQPage, and LocalBusiness

### Images (if enabled)

Three images are generated and saved in the same folder as the HTML:

| Image | Size | Filename | Placement |
|-------|------|----------|-----------|
| Banner | 1200×500 | `{slug}-banner.jpg` | After first sentence, centred |
| Section | 400×300 | `{heading-slug}.jpg` | After 3rd paragraph, right-aligned |
| FAQ | 400×300 | `{slug}-faq.jpg` | 3 paragraphs before FAQ, left-aligned |

For **location** content type: the banner shows the local area/street scene. For all other types: banner shows the service/treatment scene.

### Output folder structure

```
content/
  gtm/
    location/
      byres-road-glasgow-2026-03-18/
        byres-road-glasgow-2026-03-18.html
        byres-road-glasgow-banner.jpg
        byres-road-glasgow.jpg
        byres-road-glasgow-faq.jpg
    service/
      thai-massage-glasgow-2026-03-18/
        thai-massage-glasgow-2026-03-18.html
```

---

## Publishing to WordPress

### Prerequisites

WordPress credentials must be in `clients/[abbr]/config.json` under the `wordpress` key:

```json
"wordpress": {
  "url": "https://example.com",
  "username": "seo-machine",
  "app_password": "Wtg0 jK0T 3bak 7XRg Mg1P o7io",
  "default_post_type": "post",
  "default_status": "draft"
}
```

Generate the application password in **WP Admin → Users → Your Profile → Application Passwords**. This is NOT the login password.

### Custom Post Types

The MU plugin at `wordpress/seomachine.php` registers 5 custom post types. Upload this file to `wp-content/mu-plugins/` on the WordPress site before publishing.

| Content type | CPT slug | Where it appears in wp-admin |
|-------------|----------|------------------------------|
| `service` | `seo_service` | SEO Content → Services |
| `location` | `seo_location` | SEO Content → Locations |
| `pillar` | `seo_pillar` | SEO Content → Pillars |
| `topical` | `seo_topical` | SEO Content → Topical |
| `blog` | `seo_blog` | SEO Content → Blog |

### Enable CPTs in Elementor

After uploading the MU plugin, you must tell Elementor to allow editing on the new post types — otherwise the Elementor editor button will not appear on CPT posts.

**WP Admin → Elementor → Settings → Post Types**

Check all 5 boxes:

- [x] Services (`seo_service`)
- [x] Locations (`seo_location`)
- [x] Pillars (`seo_pillar`)
- [x] Topical (`seo_topical`)
- [x] Blog (`seo_blog`)

Save the settings. This only needs to be done once per WordPress site.

> **Note:** If you skip this step, batch-published posts will be created but the Elementor template data will not render — the post will appear blank in the front end.

### Elementor template support

If the client uses Elementor page builder, content can be injected into a saved template:

1. Build the page template in Elementor with an HTML widget. Inside the widget, type `Paste HTML Here` as a placeholder.
2. Save the template in Elementor Library. Note the template ID.
3. Add `"elementor_template_id": 12345` to the `wordpress` block in `config.json`
4. Run once to fetch and save the template: `python3 fetch_elementor_template.py [abbr]`
5. From then on, the batch runner automatically injects content into the template

### Publishing flow

- **Batch runner with `--publish`** — generates content and publishes in one step
- **`/publish-draft [file]`** — publishes a single pre-generated HTML file
- All posts are created as **drafts** — review and publish manually in wp-admin

---

## Typical Workflows

### Starting a new client

1. `/new-client` — fill in the setup wizard
2. Fill in the 7 context files in `clients/[abbr]/` (see [Client Information Checklist](#client-information-checklist))
3. Upload `wordpress/seomachine.php` to `wp-content/mu-plugins/` on the WordPress site
4. Add a test row to the Google Sheet and run `python3 geo_batch_runner.py A2:E3`
5. Review the output in `content/[abbr]/`, then run the full batch

### Researching a topic before writing

```
/research-serp "thai massage Glasgow"
/research thai massage glasgow
/write thai massage glasgow finnieston
```

### Batch content run (e.g. 20 location pages)

1. Add 20 rows to the Google Sheet (Column A = location, Column B = `Write Now`, Column D = client abbr, Column E = `location`)
2. `python3 geo_batch_runner.py` — generates all 20 pages
3. Review a sample of the output in `content/[abbr]/location/`
4. `python3 geo_batch_runner.py --publish` on the next run to push to WordPress

Or combine into one step:

```bash
python3 geo_batch_runner.py --publish
```

### Refreshing existing content

```
/research-performance          ← find pages that need updating
/rewrite [file or URL]         ← rewrite with fresh research
/optimize [file]               ← final SEO pass
/publish-draft [file]          ← push updated draft to WP
```

### Strategy planning

```
/cluster [core service]        ← map out the full topic cluster
/content-calendar              ← build a monthly publishing schedule
/priorities                    ← get a prioritised hit list of what to write next
```
