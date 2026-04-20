# CLI Command Reference

Full reference for all Python scripts. Run from the project root.

---

## Content Generation

```bash
# Batch runner — Google Sheet queue
python3 src/content/geo_batch_runner.py                    # all "Write Now" rows
python3 src/content/geo_batch_runner.py A2:E5              # specific range
python3 src/content/geo_batch_runner.py --publish          # generate + publish to WP as draft

# Scheduled publisher — JSON queue file
python3 src/content/publish_scheduled.py --abbr gtb                          # publish next pending topic
python3 src/content/publish_scheduled.py --abbr gtb --status                 # queue status table
python3 src/content/publish_scheduled.py --abbr gtb --dry-run                # generate only, skip WP
python3 src/content/publish_scheduled.py --abbr gtm --queue comp-alt-queue.json          # alt queue
python3 src/content/publish_scheduled.py --abbr gtm --queue comp-alt-queue.json --status

# Re-publish existing HTML (no content regeneration)
python3 src/content/republish_existing.py                  # all gtm location files
python3 src/content/republish_existing.py --type service
python3 src/content/republish_existing.py --abbr gtm --type blog
python3 src/content/republish_existing.py --file content/sdy/service/slug/slug.html

# Regenerate images for specific pages
python3 src/content/regen_images.py --abbr sdy --folders "slug-2026-04-06,slug-2026-03-28" --type service
```

---

## Research

```bash
python3 src/research/research_quick_wins.py
python3 src/research/research_competitor_gaps.py
python3 src/research/research_serp_analysis.py "keyword"
python3 src/research/research_topic_clusters.py
python3 src/research/research_trending.py
python3 src/research/research_competitors.py --abbr gtm    # map pack + organic + profiles → competitor-analysis.md

python3 src/research/research_blog_topics.py --abbr gtb                      # topic ideas (niche cache, 30-day TTL)
python3 src/research/research_blog_topics.py --abbr gtb --sheet              # push to Google Sheet (status: pause)
python3 src/research/research_blog_topics.py --abbr gtb --refresh            # force cache refresh
python3 src/research/research_blog_topics.py --abbr gtb --queue              # write topic-queue.json
python3 src/research/research_blog_topics.py --abbr gtb --queue --cadence 14 # fortnightly cadence
```

---

## Publishing Utilities

```bash
python3 src/publishing/fetch_elementor_template.py gtm     # fetch + save Elementor template JSON
python3 src/publishing/update_post_classes.py --abbr sdy --type service      # backfill CSS classes
python3 src/publishing/update_post_classes.py --abbr gtm --type all
python3 src/publishing/update_post_classes.py --abbr sdy --type all --dry-run
python3 src/publishing/inject_elementor_template.py --template-id 22698      # inject template into all GTB posts
python3 src/publishing/inject_elementor_template.py --template-id 22698 --dry-run
python3 src/publishing/inject_elementor_template.py --template-id 22698 --post-id 12345
python3 src/publishing/inject_elementor_template.py --template-id 22698 --abbr gtm
```

---

## Audit & Crawl

```bash
python3 src/audit/run_audit.py --abbr gtm                  # full SEO audit (existing client)
python3 src/audit/run_audit.py --abbr gtm --no-pdf         # skip PDF
python3 src/audit/run_audit.py --abbr gtm --crawl          # audit + site crawl
python3 src/audit/run_audit.py --url https://... --name "Business" --no-email  # prospect audit

python3 src/audit/run_crawl.py --abbr gtm                  # crawl only → crawl-report.json + crawl-summary.md
python3 src/audit/run_crawl.py --abbr gtm --max-pages 500 --concurrency 10 --delay 0.2
```

---

## Citations

```bash
python3 src/citations/run_citations.py --abbr gtm           # full: audit + create missing
python3 src/citations/run_citations.py --abbr gtm --mode audit     # check only
python3 src/citations/run_citations.py --abbr gtm --mode create    # create missing only
python3 src/citations/run_citations.py --abbr gtm --status         # status table
python3 src/citations/run_citations.py --abbr gtm --dry-run
python3 src/citations/run_citations.py --abbr gtm --force          # re-check all sites
python3 src/citations/run_citations.py --abbr sdy --competitor-gaps  # re-run gap analysis

python3 src/research/research_citation_gaps.py --abbr sdy [--top 10] [--discover] [--dry-run]
```

---

## Social / Repurposing

```bash
python3 src/social/repurpose_content.py --abbr gtm                     # process all unrepurposed articles
python3 src/social/repurpose_content.py --abbr gtm --dry-run           # generate, skip GHL publish
python3 src/social/repurpose_content.py --abbr gtm --status
python3 src/social/repurpose_content.py --abbr gtm --topic "Thai Massage Benefits"
```

---

## Reporting

```bash
python3 src/reporting/daily_digest.py                      # send today's digest email
python3 src/reporting/daily_digest.py --date 2026-04-07   # specific date
python3 src/reporting/daily_digest.py --dry-run            # print without sending
```

---

## Snippets

```bash
python3 src/snippets/generate_directions_snippet.py gtm    # generate directions widget
```

---

## Tests

```bash
python3 tests/test_dataforseo.py    # API connectivity check
pytest tests/                       # full test suite
pytest tests/audit/test_crawler.py  # crawler tests only
```
