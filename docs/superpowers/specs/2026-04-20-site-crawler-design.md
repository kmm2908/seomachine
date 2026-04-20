# Site Crawler Design

**Date:** 2026-04-20
**Status:** Approved

## Overview

An async site crawler that spiders all pages on a client site, detects technical SEO issues, and feeds findings into the existing audit pipeline. Replaces Ahrefs Site Audit for crawl-based issue detection across GTM, GTB, SDY, TMG, TMB.

## Goals

- Detect the highest-impact technical SEO issues surfaced by a real crawl (not point-in-time checks)
- Save structured crawl data for future UI consumption
- Integrate with the existing `/audit` pipeline via `collect_technical()`
- Run on-demand via CLI; scheduled crawls deferred to UI phase

## Architecture

### New files

**`src/audit/crawler.py`** — async spider

- Entry point: `async def crawl(site_url, config) -> CrawlResult`
- Uses `aiohttp` for HTTP requests, `BeautifulSoup` for HTML parsing
- `asyncio.Semaphore(10)` — max 10 concurrent requests (configurable)
- 0.1s delay between fetches, 10s per-request timeout
- User-Agent: `SEOMachine/1.0`

**`src/audit/run_crawl.py`** — CLI entry point

```bash
python3 src/audit/run_crawl.py --abbr gtm
python3 src/audit/run_crawl.py --abbr gtm --max-pages 500 --concurrency 10
python3 src/audit/run_audit.py --abbr gtm --crawl   # audit + crawl together
```

### Updated file

**`src/audit/collectors.py`** — `collect_technical()` gains optional `crawl_report` path param. When present, reads `CrawlResult` JSON and maps findings into `TechnicalResult`. Falls back to current shallow checks when no crawl report exists.

## Crawl Algorithm

1. Fetch homepage + `/wp-sitemap.xml`, build sitemap URL set
2. Parse `<a href>` (internal — follow), `<link href>` CSS, `<script src>`, `<img src>`
3. Follow internal links recursively; HEAD-check external links for status only
4. Record per-page data (see Data Models)
5. Stop when max pages reached (default: 500) or no unvisited URLs remain
6. Run detector pass over all collected `PageData` → populate `CrawlIssues`

## Data Models

```python
@dataclass
class PageData:
    url: str
    http_code: int
    final_url: str                    # after redirects
    redirect_chain: list[str]
    title: str
    meta_description: str
    h1s: list[str]
    canonical: str
    resources: dict[str, list[str]]   # {css: [...], js: [...], images: [...]}
    inlinks: list[str]
    is_in_sitemap: bool

@dataclass
class CrawlIssues:
    pages_4xx: list[dict]             # {url, http_code, inlinks}
    redirect_chains: list[dict]       # {url, chain, hop_count}
    https_issues: list[dict]          # {url, issue_type}
    broken_resources: list[dict]      # {page_url, resource_url, resource_type, http_code}
    orphan_pages: list[str]
    missing_title: list[str]
    duplicate_titles: dict[str, list[str]]   # {title: [urls]}
    title_too_long: list[dict]        # {url, title, length}
    missing_meta: list[str]
    duplicate_meta: dict[str, list[str]]
    meta_too_long: list[dict]         # {url, meta, length}
    missing_h1: list[str]
    multiple_h1: list[dict]           # {url, h1s}

@dataclass
class CrawlStats:
    total_pages: int
    pages_200: int
    pages_3xx: int
    pages_4xx: int
    pages_5xx: int
    total_resources_checked: int
    broken_resources_count: int
    crawl_duration_seconds: float
    avg_response_ms: float

@dataclass
class CrawlResult:
    site_url: str
    crawled_at: str                   # ISO datetime
    pages: list[PageData]
    issues: CrawlIssues
    stats: CrawlStats
```

## Issue Detection

| Issue | Severity | Detection logic |
|-------|----------|----------------|
| 4xx pages | Critical | `http_code >= 400` — records URL, code, all inlinks |
| Redirect chains | Critical | Redirect hops ≥ 3 — records full chain and hop count |
| Broken resources | Critical | CSS/JS/image returning 4xx — records referencing page |
| HTTPS / mixed content | Warning | HTTPS page with `http://` resource URLs, or page over HTTP |
| Orphan pages | Warning | No inlinks (except homepage) AND not in sitemap |
| Missing H1 | Warning | No `<h1>` found |
| Multiple H1s | Info | More than one `<h1>` on page |
| Missing title | Info | `<title>` absent or empty |
| Duplicate titles | Info | Same title on 2+ pages |
| Title too long | Info | Title > 60 characters |
| Missing meta description | Info | `<meta name="description">` absent or empty |
| Duplicate meta descriptions | Info | Same description on 2+ pages |
| Meta too long | Info | Description > 160 characters |

## Output

Saved to `audits/[abbr]/[date]/`:

- `crawl-report.json` — full `CrawlResult` (machine-readable; feeds audit + future UI)
- `crawl-summary.md` — human-readable issues grouped by severity (Critical / Warning / Info), with counts and affected URLs

Console output mirrors the existing audit style:
```
→ Crawling serendipitymassage.co.uk...
→ Pages: 143 crawled | 200: 138 · 3xx: 3 · 4xx: 2
→ Issues: 2 critical · 5 warnings · 12 info
→ Saved: audits/sdy/2026-04-20/crawl-report.json
```

## Audit Integration

`collect_technical()` in `collectors.py`:
- If `crawl_report` path is passed and file exists → reads JSON, maps crawl findings into `TechnicalResult`
- Otherwise → existing shallow checks run unchanged (backward compatible)

`run_audit.py` gains `--crawl` flag:
- Runs crawler first → saves `crawl-report.json` → passes path to `collect_technical()`
- Without flag → existing audit behaviour unchanged

## CLI Reference

```bash
# Crawl only
python3 src/audit/run_crawl.py --abbr gtm

# Crawl with options
python3 src/audit/run_crawl.py --abbr gtm --max-pages 500 --concurrency 10 --delay 0.2

# Full audit with crawl
python3 src/audit/run_audit.py --abbr gtm --crawl
```

## Dependencies

Add to `data_sources/requirements.txt`:
- `aiohttp>=3.9`

`BeautifulSoup4` and `requests` are already present.

## Deferred

- Scheduled crawls (weekly / twice-weekly / monthly) — UI phase
- Page speed measurement
- Duplicate content detection
- Per-page structured data validation
