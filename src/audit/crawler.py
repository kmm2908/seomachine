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
