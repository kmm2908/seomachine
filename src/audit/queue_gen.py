"""
Pending Content Queue Generator

Analyses the AuditResult and produces a list of pending queue entries
in the standard SEO Machine format. All items start as `status: pending`
and nothing runs until the user approves and moves them to the
appropriate queue file.
"""

from __future__ import annotations

from typing import List, Dict
from scoring import AuditResult


def build_pending_queue(result: AuditResult) -> List[Dict]:
    """
    Return a list of queue entry dicts based on content gaps found in the audit.

    Each entry is in the standard SEO Machine queue format:
      {"topic": "...", "content_type": "...", "status": "pending", "wp_category": "..."}
    """
    entries: List[Dict] = []
    r = result
    name = r.site_name
    city = _extract_city(r.site_url, getattr(r.nap, 'config_address', ''))

    # ── Service pages ─────────────────────────────────────────────────────────
    if r.content.service_count < 3:
        entries.append({
            'topic': f'{name} — Core Services Overview',
            'content_type': 'service',
            'status': 'pending',
            'notes': f'Audit gap: only {r.content.service_count} service page(s) found',
        })

    # ── Location pages ────────────────────────────────────────────────────────
    if r.content.location_count == 0 and city:
        entries.append({
            'topic': f'{city} City Centre',
            'content_type': 'location',
            'status': 'pending',
            'notes': 'Audit gap: no location pages found',
        })
        entries.append({
            'topic': f'{city}',
            'content_type': 'pillar',
            'status': 'pending',
            'notes': 'Audit gap: pillar page for primary service area',
        })

    # ── Blog posts ────────────────────────────────────────────────────────────
    if r.content.blog_count < 4:
        shortage = 4 - r.content.blog_count
        blog_topics = _default_blog_topics(name, city)
        for topic in blog_topics[:shortage]:
            entries.append({
                'topic': topic,
                'content_type': 'blog',
                'status': 'pending',
                'notes': 'Audit gap: low blog content',
            })

    # ── Schema fix reminder (not a content item, but a task) ─────────────────
    if r.schema.score < 12:
        entries.append({
            'topic': f'Schema Audit Fix — {name}',
            'content_type': 'topical',
            'status': 'pending',
            'notes': (
                'Audit gap: schema score ' + str(r.schema.score) + '/20. '
                'Consider a dedicated schema fix pass via SEO Machine.'
            ),
        })

    return entries


def _extract_city(site_url: str, address: str) -> str:
    """Best-effort city extraction from address string."""
    if not address:
        return ''
    # Address format: "Street, City Postcode" or similar
    parts = [p.strip() for p in address.split(',')]
    for part in parts[1:]:
        # Skip postcodes (contain digits)
        if not any(c.isdigit() for c in part) and len(part) > 3:
            return part.strip()
    return parts[0].strip() if parts else ''


def _default_blog_topics(business_name: str, city: str) -> List[str]:
    """Generic blog topic starters — agent will refine based on client brief."""
    city_str = f' {city}' if city else ''
    return [
        f'Benefits of Regular Massage Therapy for{city_str} Professionals',
        f'How to Choose the Right Massage for Your Needs',
        f'What to Expect at Your First Massage Session',
        f'Massage Therapy and Stress Relief: What the Research Shows',
        f'Top Tips for Getting the Most Out of Your Massage',
        f'How Often Should You Get a Massage?',
    ]
