"""
Wikipedia Research Module
=========================
Fetches Wikipedia summaries and related entities for a location or topic.
Uses the free Wikipedia REST API and MediaWiki API — no auth required.
All errors return {'found': False} so they never block content generation.
"""

import json
import re
import urllib.parse
import urllib.request
from typing import Optional


class WikipediaResearcher:
    SEARCH_URL = 'https://en.wikipedia.org/w/api.php'
    SUMMARY_URL = 'https://en.wikipedia.org/api/rest_v1/page/summary/{title}'
    LINKS_URL = 'https://en.wikipedia.org/w/api.php'

    # Link titles to skip when building related entities list
    _SKIP_PREFIXES = ('List of', 'Index of', 'Category:', 'Wikipedia:', 'Template:', 'File:')
    _SKIP_EXACT = {'disambiguation', 'Disambiguation'}

    def _get(self, url: str, params: Optional[dict] = None) -> dict:
        if params:
            url = url + '?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'User-Agent': 'SEOMachine/1.0 (content-research-bot)'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode('utf-8'))

    # Street-type words that don't help Wikipedia searches
    _STREET_WORDS = {
        'st', 'street', 'rd', 'road', 'ave', 'avenue', 'ln', 'lane',
        'blvd', 'boulevard', 'dr', 'drive', 'pl', 'place', 'cres',
        'crescent', 'junction', 'jct', 'of', 'the', 'and', 'at', 'near',
    }

    def _clean_query(self, query: str) -> str:
        """Strip postcodes and reduce to a clean search term."""
        # Remove Scottish/UK postcodes (e.g. G1, G12, EH1, FK3 2AB)
        query = re.sub(r'\b[A-Z]{1,2}\d{1,2}(?:\s*\d[A-Z]{2})?\b', '', query)
        # Remove "Glasgow" if the remaining query has a more specific name
        parts = query.strip().split()
        if len(parts) > 2 and 'Glasgow' in parts:
            parts = [p for p in parts if p != 'Glasgow']
        return ' '.join(parts).strip()

    def _extract_neighbourhood(self, query: str) -> Optional[str]:
        """Extract a neighbourhood/area name from a street-level address.

        For addresses like "Corunna St & St Vincent Crescent, Finnieston, Glasgow G3",
        returns "Finnieston, Glasgow" — the comma-separated segment that isn't a street
        name or "Glasgow" itself.
        """
        # Strip postcode
        query = re.sub(r'\b[A-Z]{1,2}\d{1,2}(?:\s*\d[A-Z]{2})?\b', '', query).strip()
        parts = [p.strip() for p in query.split(',') if p.strip()]

        # A meaningful part: not "Glasgow", no digits, no & connector
        def is_neighbourhood(p: str) -> bool:
            return (
                p.lower() not in ('glasgow', '')
                and not re.search(r'\d|&', p)
                and not all(w.lower() in self._STREET_WORDS for w in p.split())
            )

        candidates = [p for p in parts if is_neighbourhood(p)]
        if candidates:
            return f"{candidates[-1]}, Glasgow"
        return None

    def _search_title(self, query: str) -> Optional[str]:
        """Search Wikipedia for the best matching article title."""
        data = self._get(self.SEARCH_URL, {
            'action': 'query',
            'list': 'search',
            'srsearch': query,
            'srlimit': 3,
            'format': 'json',
        })
        results = data.get('query', {}).get('search', [])
        if not results:
            return None
        return results[0]['title']

    def _get_summary(self, title: str) -> Optional[dict]:
        """Fetch summary extract and canonical URL for a page title."""
        url = self.SUMMARY_URL.format(title=urllib.parse.quote(title, safe=''))
        data = self._get(url)
        if data.get('type') == 'disambiguation':
            return None
        extract = data.get('extract', '').strip()
        if not extract:
            return None
        return {
            'title': data.get('title', title),
            'url': data.get('content_urls', {}).get('desktop', {}).get('page', f'https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}'),
            'summary': extract[:800],  # cap at 800 chars to keep prompt lean
        }

    def _get_related_entities(self, title: str) -> list[str]:
        """Return a filtered list of linked topics from the lead section (section 0) only."""
        # Fetch HTML of section 0 to avoid navbox/category noise
        data = self._get(self.LINKS_URL, {
            'action': 'parse',
            'page': title,
            'prop': 'text',
            'section': '0',
            'format': 'json',
        })
        html = data.get('parse', {}).get('text', {}).get('*', '')
        # Strip tables (infoboxes, navboxes) to avoid picking up their links
        html = re.sub(r'<table[\s\S]*?</table>', '', html, flags=re.IGNORECASE)
        # Extract link titles from <a href="/wiki/..." title="..."> tags
        titles = re.findall(r'<a [^>]*title="([^"]+)"', html)
        seen = set()
        entities = []
        for name in titles:
            if name in seen:
                continue
            seen.add(name)
            if not name or len(name) < 4:
                continue
            if any(name.startswith(p) for p in self._SKIP_PREFIXES):
                continue
            if name in self._SKIP_EXACT:
                continue
            if '(disambiguation)' in name:
                continue
            # Skip edit-section links and citation labels
            if name.startswith('Edit') or re.match(r'^\[\d+\]$', name):
                continue
            entities.append(name)
            if len(entities) >= 12:
                break
        return entities

    def research(self, query: str) -> dict:
        """
        Fetch Wikipedia data for a location or topic query.

        Returns a dict with:
            found (bool)
            title (str)
            url (str)
            summary (str)
            related_entities (list[str])

        Always returns {'found': False} on any error.
        """
        try:
            clean = self._clean_query(query)
            if not clean:
                return {'found': False}

            title = self._search_title(clean)
            if not title:
                area = self._extract_neighbourhood(query)
                if area:
                    title = self._search_title(area)
            if not title:
                return {'found': False}

            summary_data = self._get_summary(title)
            if not summary_data:
                return {'found': False}

            related = self._get_related_entities(summary_data['title'])

            return {
                'found': True,
                'title': summary_data['title'],
                'url': summary_data['url'],
                'summary': summary_data['summary'],
                'related_entities': related,
            }
        except Exception:
            return {'found': False}
