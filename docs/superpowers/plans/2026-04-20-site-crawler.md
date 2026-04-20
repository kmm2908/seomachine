# Site Crawler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an async site spider that crawls all pages on a client WordPress site, detects 13 categories of technical SEO issues, saves structured output, and feeds findings into the existing audit pipeline.

**Architecture:** `src/audit/crawler.py` contains all crawl logic (data models, HTML parsers, async HTTP helpers, issue detector, output writers, and the top-level `crawl()` coroutine). `src/audit/run_crawl.py` is a thin CLI wrapper. `src/audit/collectors.py` gains an optional `crawl_report` parameter on `collect_technical()` so the audit pipeline can consume crawl findings without re-crawling.

**Tech Stack:** Python 3.11+, `aiohttp>=3.9` (async HTTP), `BeautifulSoup4` (HTML parsing, already in requirements), `pytest` + `pytest-asyncio` + `aioresponses` (testing)

---

### Task 1: Add dependencies

**Files:**
- Modify: `data_sources/requirements.txt`

- [ ] **Step 1: Add aiohttp and test dependencies**

Open `data_sources/requirements.txt` and add these lines (preserve existing content):

```
aiohttp>=3.9
aioresponses>=0.7
pytest-asyncio>=0.23
```

- [ ] **Step 2: Install**

```bash
pip install -r data_sources/requirements.txt
```

Expected: installs without errors.

- [ ] **Step 3: Verify**

```bash
python3 -c "import aiohttp; print(aiohttp.__version__)"
```

Expected: prints a version string like `3.9.x`.

- [ ] **Step 4: Commit**

```bash
git add data_sources/requirements.txt
git commit -m "feat(crawler): add aiohttp and test dependencies"
```

---

### Task 2: Data models

**Files:**
- Create: `src/audit/crawler.py`
- Create: `tests/audit/test_crawler.py`

- [ ] **Step 1: Write the failing test**

Create `tests/audit/test_crawler.py`:

```python
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.audit.crawler import CrawlIssues, CrawlResult, CrawlStats, PageData


def make_page(**kwargs) -> PageData:
    defaults = dict(
        url="https://example.com/",
        http_code=200,
        final_url="https://example.com/",
        redirect_chain=[],
        title="Home",
        meta_description="A description.",
        h1s=["Welcome"],
        canonical="https://example.com/",
        resources={"css": [], "js": [], "images": []},
        inlinks=[],
        is_in_sitemap=True,
    )
    return PageData(**{**defaults, **kwargs})


def make_result() -> CrawlResult:
    return CrawlResult(
        site_url="https://example.com",
        crawled_at="2026-04-20T10:00:00+00:00",
        pages=[make_page()],
        issues=CrawlIssues(),
        stats=CrawlStats(total_pages=1, pages_200=1),
    )


def test_crawl_result_json_serializable():
    result = make_result()
    data = asdict(result)
    serialised = json.dumps(data)  # must not raise
    parsed = json.loads(serialised)
    assert parsed["site_url"] == "https://example.com"
    assert parsed["pages"][0]["url"] == "https://example.com/"


def test_page_data_fields():
    page = make_page(http_code=404, title="")
    assert page.http_code == 404
    assert page.title == ""
    assert page.resources == {"css": [], "js": [], "images": []}


def test_crawl_issues_defaults_empty():
    issues = CrawlIssues()
    assert issues.pages_4xx == []
    assert issues.duplicate_titles == {}
    assert issues.orphan_pages == []
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine"
python3 -m pytest tests/audit/test_crawler.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'src.audit.crawler'`

- [ ] **Step 3: Create `src/audit/crawler.py` with data models**

```python
from __future__ import annotations

import asyncio
import json
import re
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup


@dataclass
class PageData:
    url: str
    http_code: int
    final_url: str
    redirect_chain: list[str]
    title: str
    meta_description: str
    h1s: list[str]
    canonical: str
    resources: dict[str, list[str]]
    inlinks: list[str]
    is_in_sitemap: bool


@dataclass
class CrawlIssues:
    pages_4xx: list[dict] = field(default_factory=list)
    redirect_chains: list[dict] = field(default_factory=list)
    https_issues: list[dict] = field(default_factory=list)
    broken_resources: list[dict] = field(default_factory=list)
    orphan_pages: list[str] = field(default_factory=list)
    missing_title: list[str] = field(default_factory=list)
    duplicate_titles: dict[str, list[str]] = field(default_factory=dict)
    title_too_long: list[dict] = field(default_factory=list)
    missing_meta: list[str] = field(default_factory=list)
    duplicate_meta: dict[str, list[str]] = field(default_factory=dict)
    meta_too_long: list[dict] = field(default_factory=list)
    missing_h1: list[str] = field(default_factory=list)
    multiple_h1: list[dict] = field(default_factory=list)


@dataclass
class CrawlStats:
    total_pages: int = 0
    pages_200: int = 0
    pages_3xx: int = 0
    pages_4xx: int = 0
    pages_5xx: int = 0
    total_resources_checked: int = 0
    broken_resources_count: int = 0
    crawl_duration_seconds: float = 0.0
    avg_response_ms: float = 0.0


@dataclass
class CrawlResult:
    site_url: str
    crawled_at: str
    pages: list[PageData]
    issues: CrawlIssues
    stats: CrawlStats
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/audit/test_crawler.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/audit/crawler.py tests/audit/test_crawler.py
git commit -m "feat(crawler): add data models and serialization tests"
```

---

### Task 3: HTML parsers

**Files:**
- Modify: `src/audit/crawler.py` (add two functions)
- Modify: `tests/audit/test_crawler.py` (add tests)

- [ ] **Step 1: Write failing tests**

Append to `tests/audit/test_crawler.py`:

```python
from src.audit.crawler import extract_links, extract_metadata


def test_extract_metadata_full():
    html = """
    <html><head>
      <title>My Page Title</title>
      <meta name="description" content="Great description here.">
      <link rel="canonical" href="https://example.com/page/">
    </head><body>
      <h1>Main Heading</h1>
      <h1>Second H1</h1>
    </body></html>
    """
    meta = extract_metadata(html)
    assert meta["title"] == "My Page Title"
    assert meta["meta_description"] == "Great description here."
    assert meta["canonical"] == "https://example.com/page/"
    assert meta["h1s"] == ["Main Heading", "Second H1"]


def test_extract_metadata_missing_fields():
    html = "<html><body><p>No title, no meta.</p></body></html>"
    meta = extract_metadata(html)
    assert meta["title"] == ""
    assert meta["meta_description"] == ""
    assert meta["canonical"] == ""
    assert meta["h1s"] == []


def test_extract_links_internal_vs_external():
    html = """
    <html><body>
      <a href="/about/">About</a>
      <a href="https://example.com/contact/">Contact</a>
      <a href="https://other.com/page/">Other site</a>
      <a href="mailto:hi@example.com">Email</a>
      <a href="#section">Fragment</a>
    </body></html>
    """
    internal, external, resources = extract_links(html, "https://example.com/")
    assert "https://example.com/about/" in internal
    assert "https://example.com/contact/" in internal
    assert "https://other.com/page/" in external
    assert all("mailto:" not in u for u in internal | external)
    assert all("#section" not in u for u in internal | external)


def test_extract_links_resources():
    html = """
    <html><head>
      <link rel="stylesheet" href="/style.css">
      <script src="/app.js"></script>
    </head><body>
      <img src="/logo.png">
    </body></html>
    """
    _, _, resources = extract_links(html, "https://example.com/")
    assert "https://example.com/style.css" in resources["css"]
    assert "https://example.com/app.js" in resources["js"]
    assert "https://example.com/logo.png" in resources["images"]
```

- [ ] **Step 2: Run to verify they fail**

```bash
python3 -m pytest tests/audit/test_crawler.py::test_extract_metadata_full -v
```

Expected: `ImportError: cannot import name 'extract_metadata'`

- [ ] **Step 3: Add `extract_metadata` and `extract_links` to `crawler.py`**

Add after the dataclass definitions:

```python
def extract_metadata(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    meta_desc = meta_desc_tag.get("content", "").strip() if meta_desc_tag else ""

    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]

    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    canonical = canonical_tag.get("href", "").strip() if canonical_tag else ""

    return {"title": title, "meta_description": meta_desc, "h1s": h1s, "canonical": canonical}


def extract_links(
    html: str, base_url: str
) -> tuple[set[str], set[str], dict[str, list[str]]]:
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc
    internal: set[str] = set()
    external: set[str] = set()
    resources: dict[str, list[str]] = {"css": [], "js": [], "images": []}

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        abs_url = urljoin(base_url, href).split("#")[0]
        parsed = urlparse(abs_url)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc == base_domain:
            internal.add(abs_url)
        else:
            external.add(abs_url)

    for tag in soup.find_all("link", href=True):
        if "stylesheet" in tag.get("rel", []):
            resources["css"].append(urljoin(base_url, tag["href"]))

    for tag in soup.find_all("script", src=True):
        resources["js"].append(urljoin(base_url, tag["src"]))

    for tag in soup.find_all("img", src=True):
        resources["images"].append(urljoin(base_url, tag["src"]))

    return internal, external, resources
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/audit/test_crawler.py -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/audit/crawler.py tests/audit/test_crawler.py
git commit -m "feat(crawler): add HTML metadata and link extractors"
```

---

### Task 4: Async HTTP helpers

**Files:**
- Modify: `src/audit/crawler.py` (add three async functions)
- Modify: `tests/audit/test_crawler.py` (add async tests)

- [ ] **Step 1: Write failing tests**

Append to `tests/audit/test_crawler.py`:

```python
import pytest
from aioresponses import aioresponses as mock_aiohttp

from src.audit.crawler import fetch_page, fetch_sitemap, head_check


@pytest.mark.asyncio
async def test_fetch_page_200():
    with mock_aiohttp() as m:
        m.get("https://example.com/", status=200, body="<html><head><title>T</title></head></html>",
              content_type="text/html")
        http_code, final_url, chain, html = await fetch_page("https://example.com/")
    assert http_code == 200
    assert "title" in html.lower()
    assert chain == []


@pytest.mark.asyncio
async def test_fetch_page_404():
    with mock_aiohttp() as m:
        m.get("https://example.com/gone/", status=404, body="Not found", content_type="text/html")
        http_code, final_url, chain, html = await fetch_page("https://example.com/gone/")
    assert http_code == 404


@pytest.mark.asyncio
async def test_head_check_200():
    with mock_aiohttp() as m:
        m.head("https://example.com/style.css", status=200)
        code = await head_check("https://example.com/style.css")
    assert code == 200


@pytest.mark.asyncio
async def test_head_check_404():
    with mock_aiohttp() as m:
        m.head("https://example.com/missing.css", status=404)
        code = await head_check("https://example.com/missing.css")
    assert code == 404


@pytest.mark.asyncio
async def test_fetch_sitemap_returns_urls():
    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://example.com/</loc></url>
      <url><loc>https://example.com/about/</loc></url>
    </urlset>"""
    with mock_aiohttp() as m:
        m.get("https://example.com/wp-sitemap.xml", status=200, body=sitemap_xml)
        urls = await fetch_sitemap("https://example.com")
    assert "https://example.com/" in urls
    assert "https://example.com/about/" in urls


@pytest.mark.asyncio
async def test_fetch_sitemap_missing_returns_empty():
    with mock_aiohttp() as m:
        m.get("https://example.com/wp-sitemap.xml", status=404)
        m.get("https://example.com/sitemap.xml", status=404)
        m.get("https://example.com/sitemap_index.xml", status=404)
        urls = await fetch_sitemap("https://example.com")
    assert urls == set()
```

Also add `asyncio_mode = "auto"` config. Create `pytest.ini` if it doesn't exist:

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 2: Run to verify they fail**

```bash
python3 -m pytest tests/audit/test_crawler.py::test_fetch_page_200 -v
```

Expected: `ImportError: cannot import name 'fetch_page'`

- [ ] **Step 3: Add async HTTP helpers to `crawler.py`**

Add after `extract_links`:

```python
async def fetch_page(
    url: str,
    session: aiohttp.ClientSession | None = None,
    timeout: int = 10,
) -> tuple[int, str, list[str], str]:
    """Returns (http_code, final_url, redirect_chain, html)."""
    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession(
            headers={"User-Agent": "SEOMachine/1.0"},
            connector=aiohttp.TCPConnector(ssl=False),
        )
    try:
        async with session.get(
            url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            chain = [str(r.url) for r in resp.history]
            final_url = str(resp.url)
            http_code = resp.status
            content_type = resp.content_type or ""
            html = await resp.text(errors="replace") if "html" in content_type else ""
            return http_code, final_url, chain, html
    except asyncio.TimeoutError:
        return 408, url, [], ""
    except Exception:
        return 0, url, [], ""
    finally:
        if own_session:
            await session.close()


async def head_check(
    url: str,
    session: aiohttp.ClientSession | None = None,
    timeout: int = 10,
) -> int:
    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession(
            headers={"User-Agent": "SEOMachine/1.0"},
            connector=aiohttp.TCPConnector(ssl=False),
        )
    try:
        async with session.head(
            url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            return resp.status
    except Exception:
        return 0
    finally:
        if own_session:
            await session.close()


async def fetch_sitemap(
    site_url: str,
    session: aiohttp.ClientSession | None = None,
) -> set[str]:
    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession(
            headers={"User-Agent": "SEOMachine/1.0"},
            connector=aiohttp.TCPConnector(ssl=False),
        )
    urls: set[str] = set()
    try:
        for path in ("/wp-sitemap.xml", "/sitemap.xml", "/sitemap_index.xml"):
            try:
                async with session.get(
                    site_url.rstrip("/") + path,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        continue
                    text = await resp.text()
                    found = re.findall(r"<loc>(https?://[^<]+)</loc>", text)
                    urls.update(found)
                    if "<sitemapindex" in text:
                        sub_xml_urls = re.findall(
                            r"<loc>(https?://[^<]+\.xml[^<]*)</loc>", text
                        )
                        for sub in sub_xml_urls:
                            try:
                                async with session.get(
                                    sub, timeout=aiohttp.ClientTimeout(total=10)
                                ) as sr:
                                    if sr.status == 200:
                                        urls.update(
                                            re.findall(
                                                r"<loc>(https?://[^<]+)</loc>",
                                                await sr.text(),
                                            )
                                        )
                            except Exception:
                                pass
                    break
            except Exception:
                continue
    finally:
        if own_session:
            await session.close()
    return urls
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/audit/test_crawler.py -v
```

Expected: 13 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/audit/crawler.py tests/audit/test_crawler.py pytest.ini
git commit -m "feat(crawler): add async HTTP helpers with tests"
```

---

### Task 5: Issue detector

**Files:**
- Modify: `src/audit/crawler.py` (add `detect_issues`)
- Modify: `tests/audit/test_crawler.py` (add tests)

- [ ] **Step 1: Write failing tests**

Append to `tests/audit/test_crawler.py`:

```python
from src.audit.crawler import detect_issues


def test_detect_4xx():
    pages = [
        make_page(url="https://example.com/gone/", http_code=404,
                  inlinks=["https://example.com/"]),
    ]
    issues = detect_issues(pages, sitemap_urls=set())
    assert len(issues.pages_4xx) == 1
    assert issues.pages_4xx[0]["url"] == "https://example.com/gone/"
    assert issues.pages_4xx[0]["http_code"] == 404


def test_detect_redirect_chains():
    pages = [
        make_page(
            url="https://example.com/old/",
            redirect_chain=["https://example.com/mid/", "https://example.com/mid2/"],
            final_url="https://example.com/new/",
        ),
    ]
    issues = detect_issues(pages, sitemap_urls=set())
    assert len(issues.redirect_chains) == 1
    assert issues.redirect_chains[0]["hop_count"] == 3


def test_detect_no_redirect_chain_for_single_hop():
    pages = [
        make_page(
            url="https://example.com/old/",
            redirect_chain=["https://example.com/new/"],
            final_url="https://example.com/new/",
        ),
    ]
    issues = detect_issues(pages, sitemap_urls=set())
    assert issues.redirect_chains == []


def test_detect_https_mixed_content():
    pages = [
        make_page(
            url="https://example.com/",
            final_url="https://example.com/",
            resources={"css": ["http://example.com/style.css"], "js": [], "images": []},
        ),
    ]
    issues = detect_issues(pages, sitemap_urls=set())
    assert len(issues.https_issues) == 1
    assert issues.https_issues[0]["issue_type"] == "mixed_content"


def test_detect_orphan_pages():
    pages = [
        make_page(url="https://example.com/orphan/", inlinks=[], is_in_sitemap=False),
    ]
    issues = detect_issues(pages, sitemap_urls=set())
    assert "https://example.com/orphan/" in issues.orphan_pages


def test_detect_no_orphan_if_has_inlinks():
    pages = [
        make_page(
            url="https://example.com/page/",
            inlinks=["https://example.com/"],
            is_in_sitemap=False,
        ),
    ]
    issues = detect_issues(pages, sitemap_urls=set())
    assert issues.orphan_pages == []


def test_detect_missing_title():
    pages = [make_page(title="")]
    issues = detect_issues(pages, sitemap_urls=set())
    assert "https://example.com/" in issues.missing_title


def test_detect_title_too_long():
    long_title = "A" * 61
    pages = [make_page(title=long_title)]
    issues = detect_issues(pages, sitemap_urls=set())
    assert issues.title_too_long[0]["length"] == 61


def test_detect_duplicate_titles():
    pages = [
        make_page(url="https://example.com/a/", title="Same Title"),
        make_page(url="https://example.com/b/", title="Same Title"),
    ]
    issues = detect_issues(pages, sitemap_urls=set())
    assert "Same Title" in issues.duplicate_titles
    assert len(issues.duplicate_titles["Same Title"]) == 2


def test_detect_missing_h1():
    pages = [make_page(h1s=[])]
    issues = detect_issues(pages, sitemap_urls=set())
    assert "https://example.com/" in issues.missing_h1


def test_detect_multiple_h1():
    pages = [make_page(h1s=["First", "Second"])]
    issues = detect_issues(pages, sitemap_urls=set())
    assert issues.multiple_h1[0]["url"] == "https://example.com/"
    assert issues.multiple_h1[0]["h1s"] == ["First", "Second"]


def test_detect_missing_meta():
    pages = [make_page(meta_description="")]
    issues = detect_issues(pages, sitemap_urls=set())
    assert "https://example.com/" in issues.missing_meta


def test_detect_meta_too_long():
    long_meta = "B" * 161
    pages = [make_page(meta_description=long_meta)]
    issues = detect_issues(pages, sitemap_urls=set())
    assert issues.meta_too_long[0]["length"] == 161


def test_on_page_checks_skip_non_200():
    pages = [make_page(http_code=404, title="", h1s=[], meta_description="")]
    issues = detect_issues(pages, sitemap_urls=set())
    assert issues.missing_title == []
    assert issues.missing_h1 == []
    assert issues.missing_meta == []
```

- [ ] **Step 2: Run to verify they fail**

```bash
python3 -m pytest tests/audit/test_crawler.py::test_detect_4xx -v
```

Expected: `ImportError: cannot import name 'detect_issues'`

- [ ] **Step 3: Add `detect_issues` to `crawler.py`**

Add after `fetch_sitemap`:

```python
def detect_issues(pages: list[PageData], sitemap_urls: set[str]) -> CrawlIssues:
    issues = CrawlIssues()
    title_map: dict[str, list[str]] = {}
    meta_map: dict[str, list[str]] = {}

    for page in pages:
        # 4xx
        if page.http_code >= 400:
            issues.pages_4xx.append(
                {"url": page.url, "http_code": page.http_code, "inlinks": page.inlinks}
            )

        # Redirect chains: 3+ total hops means redirect_chain has 2+ intermediate URLs
        if len(page.redirect_chain) >= 2:
            full_chain = page.redirect_chain + [page.final_url]
            issues.redirect_chains.append(
                {"url": page.url, "chain": full_chain, "hop_count": len(full_chain)}
            )

        # HTTPS / mixed content
        if page.final_url.startswith("https://"):
            for res_list in page.resources.values():
                for res_url in res_list:
                    if res_url.startswith("http://"):
                        issues.https_issues.append(
                            {"url": page.url, "issue_type": "mixed_content",
                             "resource": res_url}
                        )
                        break
        elif page.final_url.startswith("http://"):
            issues.https_issues.append({"url": page.url, "issue_type": "not_https"})

        # Orphan: no internal inlinks and not in sitemap
        if not page.inlinks and not page.is_in_sitemap:
            issues.orphan_pages.append(page.url)

        # On-page checks only for 200 pages
        if page.http_code != 200:
            continue

        if not page.title:
            issues.missing_title.append(page.url)
        else:
            title_map.setdefault(page.title, []).append(page.url)
            if len(page.title) > 60:
                issues.title_too_long.append(
                    {"url": page.url, "title": page.title, "length": len(page.title)}
                )

        if not page.meta_description:
            issues.missing_meta.append(page.url)
        else:
            meta_map.setdefault(page.meta_description, []).append(page.url)
            if len(page.meta_description) > 160:
                issues.meta_too_long.append(
                    {"url": page.url, "meta": page.meta_description,
                     "length": len(page.meta_description)}
                )

        if not page.h1s:
            issues.missing_h1.append(page.url)
        elif len(page.h1s) > 1:
            issues.multiple_h1.append({"url": page.url, "h1s": page.h1s})

    issues.duplicate_titles = {t: urls for t, urls in title_map.items() if len(urls) > 1}
    issues.duplicate_meta = {m: urls for m, urls in meta_map.items() if len(urls) > 1}
    return issues
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/audit/test_crawler.py -v
```

Expected: 27 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/audit/crawler.py tests/audit/test_crawler.py
git commit -m "feat(crawler): add issue detector with full test coverage"
```

---

### Task 6: Output writers

**Files:**
- Modify: `src/audit/crawler.py` (add two writer functions)
- Modify: `tests/audit/test_crawler.py` (add tests)

- [ ] **Step 1: Write failing tests**

Append to `tests/audit/test_crawler.py`:

```python
import json
from pathlib import Path

from src.audit.crawler import save_crawl_report, save_crawl_summary


def test_save_crawl_report_creates_json(tmp_path):
    result = make_result()
    path = save_crawl_report(result, tmp_path)
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["site_url"] == "https://example.com"
    assert len(data["pages"]) == 1


def test_save_crawl_summary_creates_markdown(tmp_path):
    result = make_result()
    # Add one critical issue so the summary has content
    result.issues.pages_4xx.append(
        {"url": "https://example.com/gone/", "http_code": 404, "inlinks": []}
    )
    path = save_crawl_summary(result, tmp_path)
    assert path.exists()
    content = path.read_text()
    assert "# Crawl Report" in content
    assert "4xx Pages" in content
    assert "https://example.com/gone/" in content
```

- [ ] **Step 2: Run to verify they fail**

```bash
python3 -m pytest tests/audit/test_crawler.py::test_save_crawl_report_creates_json -v
```

Expected: `ImportError: cannot import name 'save_crawl_report'`

- [ ] **Step 3: Add output writers to `crawler.py`**

Add after `detect_issues`:

```python
def save_crawl_report(result: CrawlResult, output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "crawl-report.json"
    path.write_text(json.dumps(asdict(result), indent=2))
    return path


def save_crawl_summary(result: CrawlResult, output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "crawl-summary.md"
    s = result.stats
    iss = result.issues

    lines: list[str] = [
        f"# Crawl Report — {result.site_url}",
        f"**Crawled:** {result.crawled_at}  ",
        f"**Pages:** {s.total_pages} | 200: {s.pages_200} · 3xx: {s.pages_3xx} "
        f"· 4xx: {s.pages_4xx} · 5xx: {s.pages_5xx}  ",
        f"**Resources:** {s.total_resources_checked} checked | "
        f"{s.broken_resources_count} broken  ",
        f"**Duration:** {s.crawl_duration_seconds}s | Avg: {s.avg_response_ms}ms",
        "",
        "---",
        "",
    ]

    def section(title: str, items: list, fmt) -> list[str]:
        if not items:
            return []
        out = [f"## {title} ({len(items)})", ""]
        out += [f"- {fmt(i)}" for i in items]
        out.append("")
        return out

    lines += ["## Critical", ""]
    lines += section(
        "4xx Pages", iss.pages_4xx,
        lambda i: f"`{i['url']}` → HTTP {i['http_code']} ({len(i['inlinks'])} inlinks)",
    )
    lines += section(
        "Redirect Chains", iss.redirect_chains,
        lambda i: f"`{i['url']}` → {i['hop_count']} hops: {' → '.join(i['chain'])}",
    )
    lines += section(
        "Broken Resources", iss.broken_resources,
        lambda i: (
            f"`{i['resource_url']}` ({i['resource_type']}, "
            f"HTTP {i['http_code']}) on `{i['page_url']}`"
        ),
    )

    lines += ["## Warnings", ""]
    lines += section(
        "HTTPS / Mixed Content", iss.https_issues,
        lambda i: f"`{i['url']}` — {i['issue_type']}",
    )
    lines += section("Orphan Pages", iss.orphan_pages, lambda u: f"`{u}`")
    lines += section("Missing H1", iss.missing_h1, lambda u: f"`{u}`")

    lines += ["## Info", ""]
    lines += section("Missing Title", iss.missing_title, lambda u: f"`{u}`")
    lines += section(
        "Title Too Long (>60 chars)", iss.title_too_long,
        lambda i: f"`{i['url']}` — {i['length']} chars",
    )
    dup_t = [{"title": t, "urls": us} for t, us in iss.duplicate_titles.items()]
    lines += section(
        "Duplicate Titles", dup_t,
        lambda i: (
            f"\"{i['title'][:50]}\" on {len(i['urls'])} pages: "
            + ", ".join(f"`{u}`" for u in i["urls"][:3])
        ),
    )
    lines += section("Missing Meta Description", iss.missing_meta, lambda u: f"`{u}`")
    lines += section(
        "Meta Too Long (>160 chars)", iss.meta_too_long,
        lambda i: f"`{i['url']}` — {i['length']} chars",
    )
    dup_m = [{"meta": m, "urls": us} for m, us in iss.duplicate_meta.items()]
    lines += section(
        "Duplicate Meta Descriptions", dup_m,
        lambda i: f"\"{i['meta'][:50]}\" on {len(i['urls'])} pages",
    )
    lines += section(
        "Multiple H1s", iss.multiple_h1,
        lambda i: (
            f"`{i['url']}` — {len(i['h1s'])} H1s: "
            + ", ".join(f'"{h}"' for h in i["h1s"][:2])
        ),
    )

    path.write_text("\n".join(lines))
    return path
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/audit/test_crawler.py -v
```

Expected: 29 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/audit/crawler.py tests/audit/test_crawler.py
git commit -m "feat(crawler): add JSON and markdown output writers"
```

---

### Task 7: Core crawl loop

**Files:**
- Modify: `src/audit/crawler.py` (add `crawl()` coroutine)
- Modify: `tests/audit/test_crawler.py` (add integration test)

- [ ] **Step 1: Write failing test**

Append to `tests/audit/test_crawler.py`:

```python
from src.audit.crawler import crawl


@pytest.mark.asyncio
async def test_crawl_basic():
    homepage_html = """
    <html><head>
      <title>Home</title>
      <meta name="description" content="Welcome.">
      <link rel="stylesheet" href="/style.css">
    </head><body>
      <h1>Welcome</h1>
      <a href="/about/">About</a>
    </body></html>
    """
    about_html = """
    <html><head>
      <title>About</title>
      <meta name="description" content="About us.">
    </head><body><h1>About</h1></body></html>
    """
    with mock_aiohttp() as m:
        m.get("https://example.com/wp-sitemap.xml", status=404)
        m.get("https://example.com/sitemap.xml", status=404)
        m.get("https://example.com/sitemap_index.xml", status=404)
        m.get("https://example.com/", status=200, body=homepage_html,
              content_type="text/html")
        m.get("https://example.com/about/", status=200, body=about_html,
              content_type="text/html")
        m.head("https://example.com/style.css", status=200)
        result = await crawl("https://example.com", max_pages=10, concurrency=2, delay=0)

    assert result.stats.total_pages == 2
    assert result.stats.pages_200 == 2
    urls = {p.url for p in result.pages}
    assert "https://example.com/" in urls
    assert "https://example.com/about/" in urls
    # About page should have homepage as an inlink
    about_page = next(p for p in result.pages if p.url == "https://example.com/about/")
    assert "https://example.com/" in about_page.inlinks
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest tests/audit/test_crawler.py::test_crawl_basic -v
```

Expected: `ImportError: cannot import name 'crawl'`

- [ ] **Step 3: Add `crawl()` to `crawler.py`**

Add at the end of the file:

```python
async def crawl(
    site_url: str,
    max_pages: int = 500,
    concurrency: int = 10,
    delay: float = 0.1,
) -> CrawlResult:
    start_time = time.time()
    base_domain = urlparse(site_url).netloc
    start_url = site_url.rstrip("/") + "/"

    headers = {"User-Agent": "SEOMachine/1.0"}
    connector = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        sitemap_urls = await fetch_sitemap(site_url, session=session)

        queue: deque[str] = deque([start_url])
        visited: set[str] = set()
        pages: list[PageData] = []
        inlinks_map: dict[str, list[str]] = {}
        response_times: list[float] = []

        while queue and len(pages) < max_pages:
            batch: list[str] = []
            while queue and len(batch) < concurrency and len(pages) + len(batch) < max_pages:
                url = queue.popleft()
                if url not in visited:
                    visited.add(url)
                    batch.append(url)

            if not batch:
                break

            async def fetch_one(url: str):
                t0 = time.time()
                http_code, final_url, redirect_chain, html = await fetch_page(
                    url, session=session
                )
                elapsed = (time.time() - t0) * 1000
                meta = (
                    extract_metadata(html)
                    if html
                    else {"title": "", "meta_description": "", "h1s": [], "canonical": ""}
                )
                internal, _, resources = (
                    extract_links(html, url)
                    if html
                    else (set(), set(), {"css": [], "js": [], "images": []})
                )
                return url, http_code, final_url, redirect_chain, meta, resources, internal, elapsed

            batch_results = await asyncio.gather(*[fetch_one(u) for u in batch])

            for (url, http_code, final_url, redirect_chain,
                 meta, resources, internal_links, elapsed) in batch_results:
                response_times.append(elapsed)
                for link in internal_links:
                    normalized = link if urlparse(link).netloc == base_domain else link
                    inlinks_map.setdefault(normalized, []).append(url)
                    if normalized not in visited:
                        queue.append(normalized)
                pages.append(PageData(
                    url=url,
                    http_code=http_code,
                    final_url=final_url,
                    redirect_chain=redirect_chain,
                    title=meta["title"],
                    meta_description=meta["meta_description"],
                    h1s=meta["h1s"],
                    canonical=meta["canonical"],
                    resources=resources,
                    inlinks=[],
                    is_in_sitemap=url in sitemap_urls,
                ))

            await asyncio.sleep(delay)

        # Populate inlinks from map
        for page in pages:
            page.inlinks = inlinks_map.get(page.url, [])

        # Resource status checks (unique URLs only)
        all_res_urls = list({
            u for page in pages for res_list in page.resources.values() for u in res_list
        })
        resource_statuses: dict[str, int] = {}
        sem = asyncio.Semaphore(concurrency)

        async def check_one(res_url: str) -> None:
            async with sem:
                resource_statuses[res_url] = await head_check(res_url, session=session)

        await asyncio.gather(*[check_one(u) for u in all_res_urls])

        issues = detect_issues(pages, sitemap_urls)

        for page in pages:
            for res_type, res_urls in page.resources.items():
                for res_url in res_urls:
                    code = resource_statuses.get(res_url, 0)
                    if code >= 400:
                        issues.broken_resources.append({
                            "page_url": page.url,
                            "resource_url": res_url,
                            "resource_type": res_type,
                            "http_code": code,
                        })

        duration = time.time() - start_time
        stats = CrawlStats(
            total_pages=len(pages),
            pages_200=sum(1 for p in pages if p.http_code == 200),
            pages_3xx=sum(1 for p in pages if 300 <= p.http_code < 400),
            pages_4xx=sum(1 for p in pages if 400 <= p.http_code < 500),
            pages_5xx=sum(1 for p in pages if p.http_code >= 500),
            total_resources_checked=len(all_res_urls),
            broken_resources_count=len(issues.broken_resources),
            crawl_duration_seconds=round(duration, 2),
            avg_response_ms=round(
                sum(response_times) / len(response_times), 1
            ) if response_times else 0.0,
        )

        return CrawlResult(
            site_url=site_url,
            crawled_at=datetime.now(timezone.utc).isoformat(),
            pages=pages,
            issues=issues,
            stats=stats,
        )
```

- [ ] **Step 4: Run all tests**

```bash
python3 -m pytest tests/audit/test_crawler.py -v
```

Expected: 30 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/audit/crawler.py tests/audit/test_crawler.py
git commit -m "feat(crawler): add async crawl loop"
```

---

### Task 8: CLI entry point

**Files:**
- Create: `src/audit/run_crawl.py`

- [ ] **Step 1: Create `run_crawl.py`**

```python
#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.audit.crawler import crawl, save_crawl_report, save_crawl_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl a client site for SEO issues.")
    parser.add_argument("--abbr", required=True, help="Client abbreviation (e.g. gtm, sdy)")
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--delay", type=float, default=0.1,
                        help="Seconds between request batches")
    parser.add_argument("--output", help="Output directory (default: audits/[abbr]/[date])")
    args = parser.parse_args()

    config_path = ROOT / "clients" / args.abbr / "config.json"
    if not config_path.exists():
        print(f"Error: no config found at {config_path}", file=sys.stderr)
        sys.exit(1)

    config = json.loads(config_path.read_text())
    site_url = config["wordpress"]["site_url"]

    output_dir = (
        Path(args.output) if args.output
        else ROOT / "audits" / args.abbr / date.today().isoformat()
    )

    print(f"→ Crawling {site_url}...")
    result = asyncio.run(
        crawl(site_url, max_pages=args.max_pages,
              concurrency=args.concurrency, delay=args.delay)
    )

    s = result.stats
    iss = result.issues
    critical = len(iss.pages_4xx) + len(iss.redirect_chains) + len(iss.broken_resources)
    warnings = len(iss.https_issues) + len(iss.orphan_pages) + len(iss.missing_h1)
    info = (
        len(iss.missing_title) + len(iss.title_too_long) + len(iss.duplicate_titles)
        + len(iss.missing_meta) + len(iss.meta_too_long) + len(iss.duplicate_meta)
        + len(iss.multiple_h1)
    )

    print(
        f"→ Pages: {s.total_pages} crawled | "
        f"200: {s.pages_200} · 3xx: {s.pages_3xx} · 4xx: {s.pages_4xx} · 5xx: {s.pages_5xx}"
    )
    print(f"→ Issues: {critical} critical · {warnings} warnings · {info} info")

    json_path = save_crawl_report(result, output_dir)
    md_path = save_crawl_summary(result, output_dir)
    print(f"→ Saved: {json_path}")
    print(f"→ Saved: {md_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify `--help` works**

```bash
python3 src/audit/run_crawl.py --help
```

Expected: prints usage with `--abbr`, `--max-pages`, `--concurrency`, `--delay`, `--output`.

- [ ] **Step 3: Commit**

```bash
git add src/audit/run_crawl.py
git commit -m "feat(crawler): add CLI entry point run_crawl.py"
```

---

### Task 9: Audit integration

**Files:**
- Modify: `src/audit/collectors.py` (update `collect_technical`)
- Modify: `src/audit/run_audit.py` (add `--crawl` flag)

- [ ] **Step 1: Write failing test**

Append to `tests/audit/test_crawler.py`:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.audit.collectors import collect_technical


def test_collect_technical_accepts_crawl_report_without_error():
    crawl_report = {
        "issues": {
            "pages_4xx": [{"url": "https://example.com/gone/", "http_code": 404,
                           "inlinks": ["https://example.com/"]}],
            "redirect_chains": [],
            "broken_resources": [],
            "orphan_pages": [],
        },
        "stats": {"total_pages": 50, "crawl_duration_seconds": 12.3},
    }
    # Pass a fake site_url — we're testing the crawl_report integration only.
    # collect_technical will fail the homepage fetch and return early,
    # but it must not crash when crawl_report is passed.
    result = collect_technical("https://example.invalid", crawl_report=crawl_report)
    # crawl findings appended to findings list when available
    assert any("404" in f or "crawl" in f.lower() for f in result.findings)
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest tests/audit/test_crawler.py::test_collect_technical_accepts_crawl_report_without_error -v
```

Expected: `TypeError: collect_technical() got an unexpected keyword argument 'crawl_report'`

- [ ] **Step 3: Update `collect_technical` in `collectors.py`**

Find the function signature (line ~876):

```python
def collect_technical(site_url: str, wp_config: Optional[Dict] = None) -> TechnicalResult:
```

Change to:

```python
def collect_technical(
    site_url: str,
    wp_config: Optional[Dict] = None,
    crawl_report: Optional[Dict] = None,
) -> TechnicalResult:
```

Then find the end of the function (just before `return result`) and add:

```python
    # Enrich findings from crawl report when available
    if crawl_report:
        iss = crawl_report.get("issues", {})
        stats = crawl_report.get("stats", {})

        pages_4xx = iss.get("pages_4xx", [])
        chains = iss.get("redirect_chains", [])
        broken = iss.get("broken_resources", [])
        orphans = iss.get("orphan_pages", [])

        if pages_4xx:
            sample = ", ".join(f"`{i['url']}`" for i in pages_4xx[:3])
            extra = f" (+{len(pages_4xx) - 3} more)" if len(pages_4xx) > 3 else ""
            result.findings.append(
                f"{len(pages_4xx)} page(s) returning 404: {sample}{extra}"
            )
        if chains:
            result.findings.append(
                f"{len(chains)} redirect chain(s) with 3+ hops — wastes crawl budget."
            )
        if broken:
            result.findings.append(
                f"{len(broken)} broken CSS/JS/image resource(s) across site."
            )
        if orphans:
            result.findings.append(
                f"{len(orphans)} orphan page(s) — no internal links and not in sitemap."
            )

        total = stats.get("total_pages", 0)
        duration = stats.get("crawl_duration_seconds", 0)
        result.findings.append(f"Crawl: {total} pages in {duration}s.")

    return result
```

- [ ] **Step 4: Add `--crawl` flag to `run_audit.py`**

In `main()`, find the argparse block:

```python
    parser.add_argument('--no-email', action='store_true', help='Skip email delivery')
```

Add immediately after:

```python
    parser.add_argument('--crawl', action='store_true',
                        help='Run site crawler before audit and include findings in report')
```

Then find where `collect_technical` is called in `run_audit.py` and update it. First, add the crawl run before the collectors. Find the section that calls collectors (look for `collect_technical`) and insert above it:

```python
    crawl_report = None
    if args.crawl:
        from src.audit.crawler import crawl as run_crawl, save_crawl_report
        from dataclasses import asdict as dc_asdict
        print("→ Running site crawler...")
        crawl_result = asyncio.run(run_crawl(site_url))
        save_crawl_report(crawl_result, output_dir)
        crawl_report = dc_asdict(crawl_result)
```

Then update the `collect_technical` call (should look like):

```python
    technical = collect_technical(site_url, wp_config=wp_config)
```

Change to:

```python
    technical = collect_technical(site_url, wp_config=wp_config, crawl_report=crawl_report)
```

Also ensure `import asyncio` is at the top of `run_audit.py` (check first — it likely already is).

- [ ] **Step 5: Run all tests**

```bash
python3 -m pytest tests/audit/test_crawler.py -v
```

Expected: 31 tests pass.

- [ ] **Step 6: Verify `--crawl` flag appears in audit help**

```bash
python3 src/audit/run_audit.py --help
```

Expected: `--crawl` appears in the help output.

- [ ] **Step 7: Commit**

```bash
git add src/audit/collectors.py src/audit/run_audit.py tests/audit/test_crawler.py
git commit -m "feat(crawler): integrate crawl findings into audit collect_technical"
```

---

### Task 10: Smoke test against a real client

This task is not automated — it verifies the full pipeline works against a live site.

- [ ] **Step 1: Run crawler against GTM**

```bash
python3 src/audit/run_crawl.py --abbr gtm --max-pages 50 --concurrency 5
```

Expected output (numbers will vary):
```
→ Crawling https://glasgowthaimassage.co.uk...
→ Pages: 50 crawled | 200: 47 · 3xx: 1 · 4xx: 2 · 5xx: 0
→ Issues: X critical · Y warnings · Z info
→ Saved: audits/gtm/2026-04-20/crawl-report.json
→ Saved: audits/gtm/2026-04-20/crawl-summary.md
```

- [ ] **Step 2: Inspect crawl-summary.md**

```bash
cat audits/gtm/$(date +%F)/crawl-summary.md
```

Expected: readable markdown with Critical / Warnings / Info sections.

- [ ] **Step 3: Run full audit with crawl**

```bash
python3 src/audit/run_audit.py --abbr gtm --crawl --no-pdf --no-email
```

Expected: audit completes without error; crawl findings appear in the Technical section of `audit-internal.md`.

- [ ] **Step 4: Commit if any tweaks were needed**

```bash
git add -p
git commit -m "fix(crawler): tweaks from smoke test"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|----------------|------|
| Async spider (aiohttp) | Task 7 (crawl loop) |
| HTML parsing (BeautifulSoup) | Task 3 |
| `asyncio.Semaphore(10)`, 0.1s delay, 10s timeout | Task 7 |
| User-Agent: SEOMachine/1.0 | Task 7 |
| Sitemap fetch (/wp-sitemap.xml first) | Task 4 |
| All 13 issue types | Task 5 |
| crawl-report.json output | Task 6 |
| crawl-summary.md output | Task 6 |
| Severity grouping (Critical/Warning/Info) | Task 6 |
| collect_technical() integration | Task 9 |
| run_audit.py --crawl flag | Task 9 |
| CLI (run_crawl.py) | Task 8 |
| CrawlResult JSON-serialisable | Task 2 |
| UI readiness (pure crawl() function, clean JSON) | Tasks 2, 7 |
| `crawler` key in config.json reserved | Not needed at implementation time — no code reads it yet |

All spec requirements covered. No placeholders. Types consistent across tasks (PageData, CrawlIssues, CrawlResult used by name identically in Tasks 2–9).
