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
