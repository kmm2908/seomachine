"""
Audit Scoring — data model and score computation.

Each category returns a dataclass with a `score` field (int) and
`findings` list (human-readable issues). Weights sum to 100.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


# ── Category weights ──────────────────────────────────────────────────────────
WEIGHTS = {
    'schema':    20,
    'content':   20,
    'gbp':       20,
    'reviews':   15,
    'nap':       15,
    'technical': 10,
}

GRADE_THRESHOLDS = [
    (85, 'A'),
    (70, 'B'),
    (55, 'C'),
    (40, 'D'),
    (0,  'F'),
]


def grade(score: int) -> str:
    for threshold, letter in GRADE_THRESHOLDS:
        if score >= threshold:
            return letter
    return 'F'


# ── Result dataclasses ────────────────────────────────────────────────────────

@dataclass
class SchemaResult:
    """JSON-LD schema completeness (max 20 pts)."""
    has_local_business: bool = False
    has_faq: bool = False
    has_article: bool = False
    name_present: bool = False
    address_present: bool = False
    phone_present: bool = False
    url_present: bool = False
    opening_hours_present: bool = False
    pages_checked: int = 0
    score: int = 0
    findings: List[str] = field(default_factory=list)

    def compute_score(self) -> int:
        pts = 0
        if self.has_local_business: pts += 8
        if self.name_present:       pts += 2
        if self.address_present:    pts += 2
        if self.phone_present:      pts += 2
        if self.url_present:        pts += 2
        if self.has_faq:            pts += 2
        if self.has_article:        pts += 2
        self.score = min(pts, 20)
        return self.score


@dataclass
class ContentResult:
    """Published content coverage (max 20 pts)."""
    service_count: int = 0
    blog_count: int = 0
    location_count: int = 0
    page_count: int = 0
    has_sitemap: bool = False
    sitemap_url_count: int = 0
    # Duplicate content: list of (id1, title1, id2, title2, reason) tuples
    duplicate_pairs: list = field(default_factory=list)
    score: int = 0
    findings: List[str] = field(default_factory=list)

    def compute_score(self) -> int:
        pts = 0
        # Service content
        if self.service_count >= 4:   pts += 7
        elif self.service_count >= 2: pts += 5
        elif self.service_count >= 1: pts += 3
        # Blog/news content
        if self.blog_count >= 6:   pts += 7
        elif self.blog_count >= 3: pts += 5
        elif self.blog_count >= 1: pts += 3
        # Location/area pages
        if self.location_count >= 4:   pts += 3
        elif self.location_count >= 1: pts += 2
        # Sitemap (bonus for discoverability)
        if self.has_sitemap: pts += 3
        # Deduct for duplicate content (2 pts per pair, min 0)
        pts = max(0, pts - len(self.duplicate_pairs) * 2)
        self.score = min(pts, 20)
        return self.score


@dataclass
class GBPResult:
    """Google Business Profile completeness (max 20 pts)."""
    available: bool = False          # False = GBP module not configured
    has_description: bool = False
    category_count: int = 0
    has_hours: bool = False
    photo_count: Optional[int] = None  # None = unknown (v4 media API not yet called)
    services_count: int = 0
    score: int = 0
    findings: List[str] = field(default_factory=list)

    def compute_score(self) -> int:
        if not self.available:
            self.score = 0
            return 0
        pts = 0
        if self.has_description:   pts += 5
        if self.category_count >= 2: pts += 5
        elif self.category_count == 1: pts += 3
        if self.has_hours:         pts += 5
        if self.photo_count is not None:
            if self.photo_count >= 10: pts += 5
            elif self.photo_count >= 3: pts += 3
            elif self.photo_count >= 1: pts += 1
        self.score = min(pts, 20)
        return self.score


@dataclass
class ReviewResult:
    """Review count, rating, and response rate (max 15 pts)."""
    count: int = 0
    average_rating: float = 0.0
    response_rate: float = 0.0    # 0.0–1.0
    available: bool = False
    score: int = 0
    findings: List[str] = field(default_factory=list)

    def compute_score(self) -> int:
        if not self.available:
            self.score = 0
            return 0
        pts = 0
        # Count (5 pts)
        if self.count >= 50:   pts += 5
        elif self.count >= 20: pts += 4
        elif self.count >= 10: pts += 3
        elif self.count >= 5:  pts += 2
        # Rating (5 pts)
        if self.average_rating >= 4.8:   pts += 5
        elif self.average_rating >= 4.5: pts += 4
        elif self.average_rating >= 4.0: pts += 3
        elif self.average_rating >= 3.5: pts += 1
        # Response rate (5 pts)
        if self.response_rate >= 0.75:   pts += 5
        elif self.response_rate >= 0.50: pts += 3
        elif self.response_rate >= 0.25: pts += 2
        self.score = min(pts, 15)
        return self.score


@dataclass
class NAPResult:
    """Name/Address/Phone consistency (max 15 pts)."""
    name_match: str = 'unknown'    # 'match', 'mismatch', 'unknown'
    address_match: str = 'unknown'
    phone_match: str = 'unknown'
    config_name: str = ''
    config_address: str = ''
    config_phone: str = ''
    schema_name: str = ''
    schema_address: str = ''
    schema_phone: str = ''
    score: int = 0
    findings: List[str] = field(default_factory=list)

    def compute_score(self) -> int:
        pts = 0
        if self.name_match == 'match':    pts += 5
        if self.address_match == 'match': pts += 5
        if self.phone_match == 'match':   pts += 5
        self.score = min(pts, 15)
        return self.score


@dataclass
class CitationResult:
    """Citation presence and NAP consistency across directories (max 15 pts).
    Replaces the schema-only NAPResult as the 'nap' scoring category.
    """
    # Schema NAP (carried over from original NAPResult checks)
    schema_name_match: str = 'unknown'
    schema_address_match: str = 'unknown'
    schema_phone_match: str = 'unknown'
    # Citation coverage
    total_sites: int = 0
    found_count: int = 0
    nap_issue_count: int = 0
    duplicate_count: int = 0
    critical_missing: list = field(default_factory=list)  # GBP/Bing/Yelp
    # Per-site results (CitationCheckResult objects)
    site_results: list = field(default_factory=list)
    score: int = 0
    findings: List[str] = field(default_factory=list)

    def compute_score(self) -> int:
        pts = 0

        # Schema NAP (kept for backward compat when citation check not run)
        if not self.site_results:
            if self.schema_name_match == 'match':    pts += 3
            if self.schema_address_match == 'match': pts += 3
            if self.schema_phone_match == 'match':   pts += 3
            self.score = min(pts, 15)
            return self.score

        # Citation coverage: 80%+ of priority sites = 6 pts
        if self.total_sites > 0:
            pct = self.found_count / self.total_sites
            if pct >= 0.8:
                pts += 6
            elif pct >= 0.6:
                pts += 4
            elif pct >= 0.4:
                pts += 2

        # NAP consistency: 5 pts (deduct 1 per issue, min 0)
        nap_pts = max(0, 5 - self.nap_issue_count)
        pts += nap_pts

        # No duplicates: 2 pts
        if self.duplicate_count == 0:
            pts += 2

        # No critical sites missing: 2 pts
        if not self.critical_missing:
            pts += 2

        self.score = min(pts, 15)
        return self.score


@dataclass
class TechnicalResult:
    """Basic technical health (max 10 pts)."""
    has_ssl: bool = False
    has_meta_title: bool = False
    has_meta_description: bool = False
    has_h1: bool = False
    has_robots: bool = False
    has_sitemap: bool = False
    response_time_ms: int = 0
    score: int = 0
    findings: List[str] = field(default_factory=list)

    def compute_score(self) -> int:
        pts = 0
        if self.has_ssl:              pts += 2
        if self.has_meta_title:       pts += 2
        if self.has_meta_description: pts += 2
        if self.has_h1:               pts += 1
        if self.has_robots:           pts += 1
        if self.has_sitemap:          pts += 1
        if 0 < self.response_time_ms < 3000: pts += 1
        self.score = min(pts, 10)
        return self.score


@dataclass
class CompetitorResult:
    """Competitor benchmark (unscored — context only)."""
    top_competitors: List[str] = field(default_factory=list)
    client_map_position: str = 'unknown'
    notes: List[str] = field(default_factory=list)
    available: bool = False


@dataclass
class AuditResult:
    abbr: str
    site_name: str
    site_url: str
    date: str
    schema: SchemaResult
    content: ContentResult
    gbp: GBPResult
    reviews: ReviewResult
    nap: 'NAPResult | CitationResult'
    technical: TechnicalResult
    competitor: CompetitorResult
    total_score: int = 0
    grade_letter: str = 'F'

    def compute_totals(self) -> None:
        self.schema.compute_score()
        self.content.compute_score()
        self.gbp.compute_score()
        self.reviews.compute_score()
        self.nap.compute_score()
        self.technical.compute_score()
        self.total_score = (
            self.schema.score
            + self.content.score
            + self.gbp.score
            + self.reviews.score
            + self.nap.score
            + self.technical.score
        )
        self.grade_letter = grade(self.total_score)
