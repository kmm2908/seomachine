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
                    inlinks_map.setdefault(link, []).append(url)
                    if link not in visited:
                        queue.append(link)
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
