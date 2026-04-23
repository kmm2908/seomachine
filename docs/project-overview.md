# SEO Machine — Project Overview

*Last updated: 2026-04-14*

A Claude Code workspace for creating, publishing, and distributing SEO-optimised content at scale for local service business clients.

---

## Product Areas

The project has grown across **8 distinct product areas**. Each is summarised below with its current status.

---

### 1. Content Generation Pipeline
**Status: Live and active**

The core product. Generates on-brand, quality-gated content for client websites.

| Component | Location | Purpose |
|-----------|----------|---------|
| Scheduled publisher | `src/content/publish_scheduled.py` | Cron-driven; one topic per run from JSON queue file |
| Quality gate | `data_sources/modules/quality_gate.py` | Flesch + engagement checks; rewrites up to 2× before flagging |
| 7 content writers | `.claude/agents/` | blog, service, location, pillar, topical, comp-alt, problem |
| Image generator | `data_sources/modules/image_generator.py` | Gemini banner + section images; GPT fallback |
| Image regenerator | `src/content/regen_images.py` | Reruns image pipeline on existing articles |
| Republisher | `src/content/republish_existing.py` | Republishes saved HTML without regenerating content |

**Active cron jobs:** GTB (5 queues × weekly), GTM comp-alt (Wednesday), SDY comp-alt (Thursday)

---

### 2. WordPress Integration
**Status: Live and active — nearing commercial release quality**

All content is published to WordPress. The MU-plugin and publisher handle CPTs, Elementor injection, schema, SEO meta, and hub shortcodes.

| Component | Location | Purpose |
|-----------|----------|---------|
| MU-plugin | `wordpress/seomachine.php` (v3.2.0) | CPTs, hub shortcode, SEO meta, CSS classes, lite mode |
| Publisher | `data_sources/modules/wordpress_publisher.py` | REST API + WP-CLI SSH path; Elementor injection; class injection |
| Elementor fetcher | `src/publishing/fetch_elementor_template.py` | Captures Elementor template for injection |
| Class backfiller | `src/publishing/update_post_classes.py` | Injects hdr-*/txt-* classes on existing published posts |
| Auto-deploy | `.github/workflows/deploy-plugin.yml` | Deploys plugin to all 5 sites on push to main |

**Plugin targets:** GTM, GTB, SDY, TMG, TMB (all via GitHub Actions)

---

### 3. Client Management
**Status: Live — 5 active clients**

Standardised per-client config and context system. Onboarding via `/new-client`.

| Client | Site | Niche | Status |
|--------|------|-------|--------|
| GTM | glasgowthaimassage.co.uk | thai-massage | Live, active publishing |
| GTB | blog.glasgowthaimassage.co.uk | thai-massage | Live, 5 weekly cron queues |
| SDY | serendipitymassage.co.uk (staging2) | massage-therapy | Staging — pre-launch review |
| TMG | thaimassagegreenock.co.uk | thai-massage | Set up, minimal publishing |
| TMB | blog.thaimassagegreenock.co.uk | thai-massage | Set up, minimal publishing |

Each client: `config.json`, brand voice, SEO guidelines, competitor analysis, internal links map, target keywords, writing examples.

---

### 4. SEO Research & Analysis
**Status: Live — used interactively via slash commands**

A suite of Python research scripts and slash commands for keyword research, competitor intelligence, and opportunity identification.

| Script | Purpose |
|--------|---------|
| `research_blog_topics.py` | Blog topics from keyword research; niche cache (30-day TTL); pushes to Sheet or queue |
| `research_competitors.py` | Map pack + organic competitor profiles via DataForSEO + Claude Haiku |
| `research_serp_analysis.py` | SERP feature analysis and entity extraction |
| `research_competitor_gaps.py` | Content gap analysis vs top competitors |
| `research_topic_clusters.py` | Keyword clustering for topical authority |
| `research_quick_wins.py` | Quick-win opportunities from GSC data |
| `research_trending.py` | Trending queries from GSC |
| `research_priorities_comprehensive.py` | Multi-factor opportunity scoring |
| `research_performance_matrix.py` | GA4 + GSC combined performance view |

Slash command equivalents: `/research`, `/research-serp`, `/research-gaps`, `/research-topics`, `/research-trending`, `/research-performance`, `/priorities`, `/cluster`

---

### 5. Audit & Reporting
**Status: Live — audit complete; reporting basic**

Full 6-category SEO audit with branded PDF output. Daily digest email for monitoring published content.

| Component | Location | Purpose |
|-----------|----------|---------|
| Audit runner | `src/audit/run_audit.py` | Full audit: schema, content, GBP, reviews, NAP, technical |
| Collectors | `src/audit/collectors.py` | Data collection per category |
| Scoring | `src/audit/scoring.py` | Point-based scoring per category |
| Report | `src/audit/report.py` | Markdown internal report + OMG-branded HTML/PDF |
| Queue gen | `src/audit/queue_gen.py` | Creates pending content queue from audit findings |
| PDF gen | `src/audit/pdf_gen.py` | Prospect-ready PDF via Playwright |
| Daily digest | `src/reporting/daily_digest.py` | Summary email: what published, cost, quality status |

---

### 6. Citation Management
**Status: Live — 23 UK sites across 4 tiers**

Automated citation audit and creation across major UK directories.

| Component | Location | Purpose |
|-----------|----------|---------|
| Runner | `src/citations/run_citations.py` | Orchestrates audit/create/status modes |
| Site list | `data_sources/modules/citation_sites.py` | 23 UK directories with tier classification |
| Checker | `data_sources/modules/citation_checker.py` | Routes checks to correct method per tier |
| Submitter | `data_sources/modules/citation_submitter.py` | Form fills via API or Playwright |
| Manual pack | `data_sources/modules/citation_manual_pack.py` | Pre-filled HTML pack for Tier 3/4 |
| State | `data_sources/modules/citation_state.py` | Persistent state per client (30-day staleness cadence) |

---

### 7. Social & Video Repurposing
**Status: Built — partially active**

Two-stage pipeline: blog publishes first, then video + social content generated and scheduled via GoHighLevel ~2 hours later.

| Component | Location | Purpose |
|-----------|----------|---------|
| Repurposer | `src/social/repurpose_content.py` | Orchestrates full repurposing run per client |
| Social generator | `src/social/social_post_generator.py` | Claude-generated video script + social posts |
| Video producer | `src/social/video_producer.py` | ElevenLabs TTS + FFmpeg; long-form + 3-5 shorts |
| ElevenLabs | `data_sources/modules/elevenlabs_tts.py` | TTS voiceover with timestamp support |
| GHL publisher | `data_sources/modules/ghl_publisher.py` | GoHighLevel Social Planner API; schedules all platforms |

**Cost:** ~$2.95/article. **Platforms:** YouTube, LinkedIn, Facebook, GBP, X (thread/standalone alternation), Instagram.

---

### 8. RankFactory
**Status: Early/experimental — not yet active**

A separate product concept: fully automated niche site factory. Finds exact-match domains, scaffolds WordPress sites, and fills them with content automatically.

| Component | Location | Purpose |
|-----------|----------|---------|
| Orchestrator | `src/factory/orchestrator.py` | Full pipeline: EMD finder → content planner → publisher |
| EMD finder | `src/factory/emd_finder.py` | Finds exact-match domains for niche + city combos |
| Content planner | `src/factory/content_planner.py` | Generates full content queue from keyword research |
| Site scaffolder | `src/factory/site_scaffolder.py` | Provisions WordPress with CPTs and initial structure |
| Site monitor | `src/factory/site_monitor.py` | Tracks rankings and metrics post-launch |
| Lead tracker | `src/factory/lead_tracker.py` | Tracks conversions from factory sites |
| Brand image gen | `src/factory/brand_image_generator.py` | Generates branded images for factory sites |

**Note:** This area is architecturally distinct from the client services model. It needs a deliberate decision on priority before further development.

---

## Shared Data Infrastructure

Modules used across multiple product areas:

| Module | Used by |
|--------|---------|
| `dataforseo.py` | Research, Audit, Citations |
| `google_analytics.py` | Research, Audit, Reporting |
| `google_search_console.py` | Research, Audit, Reporting |
| `google_business_profile.py` | Audit, Content |
| `email_utils.py` | Content, Social (batch summary emails) |
| `wordpress_publisher.py` | Content, Publishing |
| `image_generator.py` | Content, Social |
| `quality_gate.py` | Content |
| `engagement_analyzer.py` | Content, Audit |
| `readability_scorer.py` | Content, Audit |

---

## Modules of Uncertain Status

These modules exist in `data_sources/modules/` but their active use is unclear. Worth reviewing to confirm whether they are live, partially used, or orphaned:

- `content_scrubber.py` — removes AI watermarks (unclear if used in pipeline)
- `license.py` — feature gate for premium add-ons (not yet active)
- `above_fold_analyzer.py`, `landing_page_scorer.py`, `cro_checker.py`, `trust_signal_analyzer.py` — used by landing page commands only
- `article_planner.py`, `section_writer.py` — used by `/article` command only
- `search_intent_analyzer.py`, `social_research_aggregator.py` — research pipeline helpers
- `content_length_comparator.py`, `seo_quality_rater.py` — may overlap with quality gate

---

## Scale Overview

| Area | Count |
|------|-------|
| Python scripts (`src/`) | 39 |
| Data/integration modules (`data_sources/modules/`) | ~40 |
| Slash commands (`.claude/commands/`) | 28 |
| Content writer agents (`.claude/agents/`) | 7 |
| Optimisation/strategy agents (`.claude/agents/`) | 11 |
| Active clients | 5 |
| WordPress post types | 6 CPTs + standard `post` |
| UK citation sites tracked | 23 |
| Active cron jobs | 7 |

---

## Questions Worth Answering

These are the bigger-picture decisions the project is circling:

1. **RankFactory vs Client Services** — are these two separate products, or does RankFactory serve the same clients? They share infrastructure but have different operating models.

2. **Social/video repurposing** — which clients is this actually running for? Is it generating ROI worth the $2.95/article cost?

3. **Plugin commercialisation** — `seomachine.php` is noted as a future commercial product. When does that become a priority, and what does it need before release?

4. **Unused modules** — the `data_sources/modules/` folder has grown to ~40 files. Some may be dead code. A cleanup pass would reduce cognitive overhead.

5. **TMG/TMB** — these clients exist but appear to have minimal active publishing. Are they being actively managed or effectively dormant?
