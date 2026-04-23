# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session Start

At the start of every new session, automatically invoke `/start` before responding to anything else.

## Agent Usage

Offload research, writing, file operations, and batch tasks to sub-agents wherever possible to keep the main conversation context clean. Prefer `run_in_background: true` for any task that doesn't need its result before the next step. Use a lower model (Haiku/Sonnet) for sub-agents running simple tasks.

**Long-running publish runs must always use a background agent.** Any task that chains multiple `publish_scheduled.py` runs will trip the Claude Code UI timeout if run directly. Pattern:

```
Agent prompt: "Run in sequence in /path/to/seomachine, 300000ms timeout each:
  python3 src/content/publish_scheduled.py --abbr [abbr] --queue [queue]  (×N)
Report back: client, topic, status, post ID, cost per run."
run_in_background: true
```

## Project Overview

SEO Machine is a Claude Code workspace for creating SEO-optimised content at scale. It combines custom commands, specialised agents, a Python batch runner, and Google Sheets integration to research, write, optimise, and publish articles for multiple business clients.

## Setup

```bash
pip install -r data_sources/requirements.txt
```

API credentials go in `.env` at the project root. WordPress credentials are configured per client in `clients/[abbr]/config.json`.

## Client Structure

Each client lives in `clients/[abbr]/`. To add a new client, run `/new-client`. For full config schema and field documentation, see `clients/README.md`.

```
clients/
  [abbr]/
    config.json          ← WP creds, schema tokens, image settings, GBP Place ID (`gbp_place_id`), ai_visibility
    brand-voice.md       ← tone and messaging rules
    seo-guidelines.md    ← keyword and entity strategy
    internal-links-map.md
    features.md
    competitor-analysis.md
    target-keywords.md
    writing-examples.md
  README.md              ← full schema docs + onboarding guide
```

Global context (not client-specific): `context/style-guide.md`, `context/cro-best-practices.md`, `context/ai-brand-visibility.md`.

## Content Pipeline

```
Topic queue file  → src/content/publish_scheduled.py → content/[abbr]/[type]/  (cron-driven)
```

Slash command pipeline: `topics/` → `research/` → `drafts/` → `review-required/` → `published/`

For all CLI commands and flags, see `docs/commands.md`.

## Content Types

| Type | Agent | Word Count | Use for |
|------|-------|------------|---------|
| `service` | `service-page-writer.md` | 400–600 | Individual treatment/service pages |
| `location` | `location-page-writer.md` | 450+ | District, neighbourhood, or postcode pages |
| `pillar` | `pillar-page-writer.md` | 700–1000 | GBP category landing pages |
| `topical` | `topical-writer.md` | 600–1000 | Informational/question-based articles |
| `blog` | `blog-post-writer.md` | 600–1200 | Conversational blog posts |
| `news` | `blog-post-writer.md` | 600–1200 | News-angle posts; hook is optional in quality gate |
| `comp-alt` | `competitor-alt-writer.md` | 500–700 | Competitor alternative / comparison pages |
| `problem` | `problem-page-writer.md` | 600–800 | Condition/symptom pages with authority outbound links |

## Batch Runner

```bash
python3 src/content/publish_scheduled.py --abbr gtb --status   # queue status
python3 src/content/publish_scheduled.py --abbr gtb            # publish next pending topic
```

Quality gate runs after every article — see `data_sources/modules/quality_gate.py` for thresholds.
Failed quality gate: article published as draft with `★★★★★` in title — fix in wp-admin, remove stars, publish.

## Content Repurposing

`src/social/repurpose_content.py` — blog → video script + social posts → ElevenLabs TTS → FFmpeg video → GoHighLevel scheduling. Runs ~2hrs after blog publish via cron. See `docs/superpowers/specs/2026-03-26-content-repurposing-pipeline-design.md` for full design.

## Commands (Slash)

All commands in `.claude/commands/`. Key groups:
- **Research:** `/research`, `/research-serp`, `/research-gaps`, `/research-topics`, `/research-trending`, `/research-performance`, `/research-blog-topics`
- **Writing:** `/write`, `/article`, `/rewrite`
- **Publishing:** `/publish-draft`, `/optimize`, `/analyze-existing`, `/audit`, `/cluster`
- **Landing pages:** `/landing-write`, `/landing-audit`, `/landing-research`, `/landing-publish`, `/landing-competitor`

## Agents

Located in `.claude/agents/`. For agent properties and output format, read the agent file directly.

- **Content writers (7):** `service-page-writer.md`, `location-page-writer.md`, `pillar-page-writer.md`, `topical-writer.md`, `blog-post-writer.md`, `competitor-alt-writer.md`, `problem-page-writer.md`
- **SEO/optimisation:** `seo-optimizer.md`, `meta-creator.md`, `internal-linker.md`, `keyword-mapper.md`, `content-analyzer.md`, `editor.md`, `headline-generator.md`, `cro-analyst.md`, `performance.md`, `cluster-strategist.md`

## SEO Approach

Content is written entity-first, not keyword-first. Identify the primary entity and 3–5 secondary entities before writing. Entity co-occurrence and salience take priority over keyword density. See `clients/[abbr]/seo-guidelines.md`.

## WordPress Integration

Publishing uses the WordPress REST API or WP-CLI over SSH (see conventions below). The MU-plugin `wordpress/seomachine.php` registers CPTs and SEO meta fields — no Yoast dependency.

**Critical conventions** (full reasoning in `docs/conventions.md`):
1. Plugin must be in `wp-content/mu-plugins/` — not `mu-plugin/` (SiteGround display-only folder)
2. When `ssh.wp_path` is set in config → all publishing routes through WP-CLI over SSH, never direct REST
3. CSS cache-busting requires a filename rename — SG Optimizer strips `?ver=` query strings
4. GitHub Actions deploys `seomachine.php` + `seomachine-hub-v2.css` to all 5 sites on push to `main`
5. Elementor S1/S2 markers → two-section injection; single-widget fallback if absent
6. `[seo_hub]` shortcode must use Elementor **Shortcode widget**, not HTML widget

## Project Structure

```
src/
  content/      ← pipeline.py, publish_scheduled.py, republish_existing.py, regen_images.py
  research/     ← research_competitors.py, research_blog_topics.py, research_serp_analysis.py, etc.
  publishing/   ← fetch_elementor_template.py, update_post_classes.py, inject_elementor_template.py
  snippets/     ← generate_directions_snippet.py
  social/       ← repurpose_content.py, video_producer.py, social_post_generator.py
  audit/        ← run_audit.py, run_crawl.py, crawler.py, collectors.py, scoring.py, report.py
  citations/    ← run_citations.py
  api/          ← FastAPI client portal API (main.py, dependencies.py, routers/)
tests/          ← test scripts
data_sources/   ← importable modules (wordpress_publisher, image_generator, quality_gate, etc.)
config/         ← service account keys (gitignored)
clients/        ← per-client context and config (audit-latest.json written here after each audit run)
docs/           ← commands.md, conventions.md, verification.md, design specs
```

Scripts in `src/` resolve project root as `Path(__file__).parent.parent.parent`.

## Verification Protocol

Before handing back any completed task, run the relevant checks and include a `✓ Verified:` block in the response. If verification fails: fix → re-verify → hand back. If the failure revealed a new class of problem, add a rule to `docs/conventions.md` before handing back.

Full checklist: `docs/verification.md`

| Task type | Minimum check |
|---|---|
| WordPress publish | Post ID exists, correct CPT, page returns 200 |
| Script change | Run or `--dry-run`, show output, no errors |
| Config change | Valid JSON, dependent script imports cleanly |
| Plugin/CSS deploy | GitHub Actions job green, file present on server |
| HTML/content | Page returns 200, H1 present, schema `<script>` present |
| Queue change | Valid JSON, `--status` output clean |

## Continuous Improvement

When a task fails verification or a new class of problem is solved, add a rule to `docs/conventions.md` before handing back.

Rule format:
```
## [Short rule title]
**Why:** [what went wrong]
**How to apply:** [when this rule kicks in]
```

The `/wrap` command includes a conventions check — any session lesson not already in `docs/conventions.md` gets added as part of wrap-up.
