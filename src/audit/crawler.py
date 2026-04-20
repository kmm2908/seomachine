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
