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
