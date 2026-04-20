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
