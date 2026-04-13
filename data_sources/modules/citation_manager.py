# data_sources/modules/citation_manager.py
"""
Citation Manager — orchestrates audit, creation, and full runs.

Usage:
    from citation_manager import CitationManager
    manager = CitationManager(abbr='gtm', config=config, root=ROOT)
    report = manager.run_full(dry_run=False)
"""

from __future__ import annotations
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))
sys.path.insert(0, str(ROOT / 'src' / 'audit'))

from citation_sites import CITATION_SITES, CitationCheckResult, CitationSite, SITE_BY_ID
from citation_checker import check_site
from citation_submitter import submit_site
from citation_state import CitationState
from citation_manual_pack import generate_manual_pack
from scoring import CitationResult

logger = logging.getLogger(__name__)

_CRITICAL_SITE_IDS = {'google_business_profile', 'bing_places', 'yelp'}


class CitationManager:
    def __init__(self, abbr: str, config: dict, root: Path):
        self.abbr = abbr
        self.config = config
        self.root = root
        self.state = CitationState(abbr, root)

    def run_audit(self, force: bool = False, dry_run: bool = False) -> CitationResult:
        """Check all due sites and return scored CitationResult."""
        sites = self.state.get_due_sites(CITATION_SITES, force=force)
        results = []
        for site in sites:
            logger.info('Checking %s (%s)...', site.name, site.id)
            r = check_site(site, self.config, dry_run=dry_run)
            self.state.update(r)
            results.append(r)

        self.state.save()
        # Always generate manual pack so users know what needs manual submission
        all_results = self._all_results_from_state()
        pack_path = generate_manual_pack(self.abbr, self.config, all_results, self.root)
        logger.info('Manual pack saved to %s', pack_path)
        # If no sites were due this run, score from the full state snapshot
        score_source = results if results else all_results
        return self._build_scored_result(score_source)

    def run_creation(self, dry_run: bool = False) -> list[CitationCheckResult]:
        """Attempt creation for all not_found sites. Returns submission results."""
        not_found_ids = self.state.get_not_found()
        sites_to_submit = [s for s in CITATION_SITES if s.id in not_found_ids]

        submitted = []
        for site in sites_to_submit:
            logger.info('Submitting to %s...', site.name)
            r = submit_site(site, self.config, dry_run=dry_run)
            self.state.update(r)
            submitted.append(r)

        # Generate manual pack for anything that needs it
        all_results = self._all_results_from_state()
        pack_path = generate_manual_pack(self.abbr, self.config, all_results, self.root)
        logger.info('Manual pack saved to %s', pack_path)
        self.state.save()
        return submitted

    def run_full(self, force: bool = False, dry_run: bool = False) -> CitationResult:
        """Audit all sites, then attempt creation for missing ones."""
        scored = self.run_audit(force=force, dry_run=dry_run)
        self.run_creation(dry_run=dry_run)
        return scored

    def _build_scored_result(self, results: list[CitationCheckResult]) -> CitationResult:
        total = len([r for r in results if r.status != 'unknown'])
        found = len([r for r in results if r.status == 'found'])
        nap_issues = sum(len(r.issues) for r in results if r.status == 'found')
        duplicates = len([r for r in results if r.status == 'duplicate'])
        critical_missing = [
            r.site.id for r in results
            if r.site.id in _CRITICAL_SITE_IDS and r.status == 'not_found'
        ]
        cr = CitationResult(
            total_sites=total,
            found_count=found,
            nap_issue_count=nap_issues,
            duplicate_count=duplicates,
            critical_missing=critical_missing,
            site_results=results,
        )
        cr.compute_score()
        cr.findings = self._build_findings(results, cr)
        return cr

    def _build_findings(self, results: list[CitationCheckResult], cr: CitationResult) -> list[str]:
        findings = []
        if cr.critical_missing:
            for sid in cr.critical_missing:
                name = next((s.name for s in CITATION_SITES if s.id == sid), sid)
                findings.append(f'Critical citation missing: {name}')
        for r in results:
            if 'phone_mismatch' in r.issues:
                findings.append(f'{r.site.name}: phone mismatch — update to {self.config.get("phone", "")}')
            if 'address_mismatch' in r.issues:
                findings.append(f'{r.site.name}: address mismatch')
            if r.status == 'duplicate':
                findings.append(f'{r.site.name}: duplicate listing found — remove one')
        if cr.total_sites > 0 and cr.found_count / cr.total_sites < 0.6:
            findings.append(f'Low citation coverage: {cr.found_count}/{cr.total_sites} sites')
        return findings

    def _all_results_from_state(self) -> list[CitationCheckResult]:
        """Reconstruct CitationCheckResult list from state for pack generation."""
        results = []
        for entry in self.state.all_results_snapshot():
            sid = entry['id']
            if sid not in SITE_BY_ID:
                continue
            r = CitationCheckResult(
                site=SITE_BY_ID[sid],
                status=entry.get('status', 'unknown'),
                submit_status=entry.get('submit_status'),
                issues=entry.get('issues', []),
                listing_url=entry.get('listing_url', ''),
                found_phone=entry.get('found_phone', ''),
                found_address=entry.get('found_address', ''),
            )
            results.append(r)
        return results

    def print_status(self) -> None:
        """Print a status table to stdout."""
        ICONS = {'found': '✓', 'not_found': '✗', 'unknown': '·', 'duplicate': '⚠'}
        SUBMIT_ICONS = {'submitted': '→', 'pending_verification': '⌛', 'manual_required': '✎', 'failed': '✗'}
        print(f'\n  {"Site":<28} {"Status":<12} {"NAP":<8} {"Submission":<16} Issues')
        print('  ' + '─' * 75)
        for entry in self.state.all_results_snapshot():
            sid = entry['id']
            site = SITE_BY_ID.get(sid)
            if not site:
                continue
            status_icon = ICONS.get(entry.get('status', 'unknown'), '·')
            nap = '✓' if entry.get('nap_match') else ('✗' if entry.get('nap_match') is False else '—')
            sub = SUBMIT_ICONS.get(entry.get('submit_status', ''), '')
            issues = ', '.join(entry.get('issues', []))
            print(f'  {site.name:<28} {status_icon} {entry.get("status", "unknown"):<10} {nap:<8} {sub:<16} {issues}')
        print()
