"""Manages persistent citation state per client in clients/[abbr]/citations/state.json."""

from __future__ import annotations
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from citation_sites import CitationCheckResult, CitationSite, CITATION_SITES


_DEFAULT_CADENCE_DAYS = 30


class CitationState:
    def __init__(self, abbr: str, root: Path):
        self.abbr = abbr
        self._dir = root / 'clients' / abbr / 'citations'
        self._path = self._dir / 'state.json'
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            return json.loads(self._path.read_text())
        return {'last_run': None, 'sites': {}, 'competitor_gaps_run': False}

    def save(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._data['last_run'] = date.today().isoformat()
        self._path.write_text(json.dumps(self._data, indent=2))

    def is_due(self, site_id: str, cadence_days: int = _DEFAULT_CADENCE_DAYS) -> bool:
        """Return True if site hasn't been checked within cadence_days."""
        entry = self._data['sites'].get(site_id, {})
        last_checked = entry.get('last_checked')
        if not last_checked:
            return True
        last = datetime.fromisoformat(last_checked).date()
        return (date.today() - last).days >= cadence_days

    def get_due_sites(self, sites: list[CitationSite], force: bool = False) -> list[CitationSite]:
        """Return sites that need checking."""
        if force:
            return sites
        return [s for s in sites if self.is_due(s.id)]

    def update(self, result: CitationCheckResult) -> None:
        """Record the outcome of a single site check."""
        self._data['sites'][result.site.id] = {
            'status': result.status,
            'listing_url': result.listing_url,
            'nap_match': result.nap_match,
            'found_name': result.found_name,
            'found_phone': result.found_phone,
            'found_address': result.found_address,
            'issues': result.issues,
            'submit_status': result.submit_status,
            'last_checked': date.today().isoformat(),
        }

    def competitor_gaps_have_run(self) -> bool:
        return bool(self._data.get('competitor_gaps_run', False))

    def mark_competitor_gaps_run(self) -> None:
        self._data['competitor_gaps_run'] = True

    def get_not_found(self) -> list[str]:
        """Return site IDs with status not_found and no pending submission."""
        return [
            sid for sid, data in self._data['sites'].items()
            if data.get('status') == 'not_found'
            and data.get('submit_status') is None
        ]

    def all_results_snapshot(self) -> list[dict]:
        """Return all known site states as a list, sorted by site priority desc."""
        site_priority = {s.id: s.priority for s in CITATION_SITES}
        return sorted(
            [{'id': sid, **data} for sid, data in self._data['sites'].items()],
            key=lambda x: site_priority.get(x['id'], 0),
            reverse=True,
        )
