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
