# data_sources/modules/citation_manual_pack.py
"""Generates a pre-filled manual citation submission pack (HTML)."""

from __future__ import annotations
from datetime import date
from pathlib import Path

import json
from citation_sites import CitationSite, CitationCheckResult, CITATION_SITES, get_niche_sites


def _load_gap_results(abbr: str, root: Path) -> dict | None:
    path = root / 'clients' / abbr / 'citations' / 'gap-results.json'
    if path.exists():
        return json.loads(path.read_text())
    return None


def generate_shareable_pack(
    abbr: str,
    config: dict,
    site_results: list[CitationCheckResult],
    root: Path,
    niche: str = '',
) -> tuple[Path, str]:
    """
    Generate a plain-text shareable pack (WhatsApp / email friendly).
    Returns (path, content) so the content can also be served directly by a future API.
    """
    manual_sites = [
        r for r in site_results
        if r.site.tier == 4 or r.submit_status == 'manual_required'
    ]
    checked_ids = {r.site.id for r in site_results}
    unchecked_tier4 = [
        CitationCheckResult(site=s)
        for s in CITATION_SITES
        if s.tier == 4 and s.id not in checked_ids
    ]
    all_manual = manual_sites + unchecked_tier4
    niche_results = [CitationCheckResult(site=s) for s in get_niche_sites(niche)]
    assoc_sites = [r for r in niche_results if r.site.id in _ASSOCIATION_IDS]
    dir_sites = [r for r in niche_results if r.site.id not in _ASSOCIATION_IDS]
    gap_results = _load_gap_results(abbr, root)

    content = _render_shareable(config, all_manual, assoc_sites, dir_sites, gap_results)
    out_dir = root / 'clients' / abbr / 'citations'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'manual-pack-shareable.md'
    out_path.write_text(content)
    return out_path, content


def generate_manual_pack(
    abbr: str,
    config: dict,
    site_results: list[CitationCheckResult],
    root: Path,
    niche: str = '',
) -> Path:
    """
    Generate manual-pack.html for sites that need manual submission.
    Includes Tier 4 sites + any Tier 3 sites where submit_status == 'manual_required'.
    When niche is provided, also renders a separate section for industry/association sites.
    Returns the path to the generated file.
    """
    manual_sites = [
        r for r in site_results
        if r.site.tier == 4 or r.submit_status == 'manual_required'
    ]
    # Also include Tier 4 sites not yet checked
    checked_ids = {r.site.id for r in site_results}
    unchecked_tier4 = [
        CitationCheckResult(site=s)
        for s in CITATION_SITES
        if s.tier == 4 and s.id not in checked_ids
    ]
    all_manual = manual_sites + unchecked_tier4
    niche_sites = [CitationCheckResult(site=s) for s in get_niche_sites(niche)]
    gap_results = _load_gap_results(abbr, root)

    out_dir = root / 'clients' / abbr / 'citations'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'manual-pack.html'
    out_path.write_text(_render_pack(config, all_manual, niche_sites, gap_results))
    generate_shareable_pack(abbr, config, site_results, root, niche)
    return out_path


_ASSOCIATION_IDS = {'smto', 'cnhc', 'fht', 'ctha'}


def _render_pack(config: dict, results: list[CitationCheckResult], niche_results: list[CitationCheckResult] = None, gap_results: dict = None) -> str:
    name = config.get('name', '')
    address = config.get('address', '')
    phone = config.get('phone', '')
    website = config.get('website', '')
    description = config.get('description', f'{name} — professional massage therapy in {config.get("city", "")}.')

    rows = '\n'.join(_render_site_row(r, config) for r in results)
    niche_results = niche_results or []
    assoc_results = [r for r in niche_results if r.site.id in _ASSOCIATION_IDS]
    dir_results = [r for r in niche_results if r.site.id not in _ASSOCIATION_IDS]

    niche_section = ''
    if niche_results:
        assoc_rows = '\n'.join(_render_site_row(r, config) for r in assoc_results)
        dir_rows = '\n'.join(_render_site_row(r, config) for r in dir_results)
        niche_section = f"""
<hr style="margin:2rem 0">
<h2>Industry &amp; Association Directories</h2>
<p style="color:#555;font-size:0.9rem">Separate submission track — associations require proof of qualifications and professional indemnity insurance. Directories are self-registration.</p>

<h3 style="margin-top:1.5rem">Associations</h3>
{assoc_rows}

<h3 style="margin-top:1.5rem">Niche Directories</h3>
{dir_rows}
"""

    gap_section = ''
    if gap_results:
        action_gaps = [g for g in gap_results.get('gaps', []) if g.get('our_status') == 'not_found']
        competitors = gap_results.get('competitors', [])
        generated = gap_results.get('generated', '')
        if action_gaps:
            gap_rows = '\n'.join(_render_gap_row(g) for g in action_gaps)
            comp_list = ', '.join(c['name'] for c in competitors[:5])
            gap_section = f"""
<hr style="margin:2rem 0">
<h2>Competitor Citation Gaps</h2>
<p style="color:#555;font-size:0.9rem">Sites where your top GBP competitors appear but you don't. Analysed {len(competitors)} competitors ({comp_list}) on {generated}. Run <code>python3 src/research/research_citation_gaps.py --abbr {{}}</code> to refresh.</p>
{gap_rows}
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Citation Manual Pack — {name}</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #222; }}
  h1 {{ font-size: 1.4rem; border-bottom: 2px solid #333; padding-bottom: 8px; }}
  h2 {{ font-size: 1.1rem; margin-top: 2rem; }}
  h3 {{ font-size: 1rem; margin-top: 1.5rem; }}
  .nap-block {{ background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; padding: 16px; margin: 16px 0; font-family: monospace; white-space: pre-wrap; }}
  .site {{ border: 1px solid #ddd; border-radius: 6px; padding: 16px; margin: 16px 0; }}
  .site h3 {{ margin: 0 0 8px; }}
  .site a.btn {{ display: inline-block; background: #2563eb; color: #fff; text-decoration: none; padding: 8px 16px; border-radius: 4px; margin: 8px 0; }}
  .fields {{ background: #f9f9f9; padding: 12px; border-radius: 4px; font-size: 0.9rem; }}
  .fields dt {{ font-weight: bold; margin-top: 6px; }}
  .fields dd {{ margin: 0 0 4px 16px; font-family: monospace; }}
  input[type=checkbox] {{ margin-right: 6px; }}
  .done {{ opacity: 0.5; text-decoration: line-through; }}
  .generated {{ color: #666; font-size: 0.85rem; }}
</style>
</head>
<body>
<h1>Citation Manual Submission Pack — {name}</h1>
<p class="generated">Generated {date.today().isoformat()}</p>

<h2>Standard NAP Block (copy-paste)</h2>
<div class="nap-block">Business Name: {name}
Address: {address}
Phone: {phone}
Website: {website}

Short Description (50 words):
{description[:280]}

Categories: Massage, Thai Massage, Health &amp; Beauty, Wellness</div>

<h2>Sites to Submit ({len(results)} total)</h2>
{rows}
{niche_section}
{gap_section}
<script>
document.querySelectorAll('input[type=checkbox]').forEach(cb => {{
  cb.addEventListener('change', () => {{
    cb.closest('.site').classList.toggle('done', cb.checked);
  }});
}});
</script>
</body>
</html>"""


def _render_shareable(
    config: dict,
    generic_sites: list[CitationCheckResult],
    assoc_sites: list[CitationCheckResult],
    dir_sites: list[CitationCheckResult],
    gap_results: dict | None,
) -> str:
    name = config.get('name', '')
    address = config.get('address', '')
    phone = config.get('phone', '')
    website = config.get('website', '')
    sep = '━' * 40

    # Sites covered by competitor gaps — exclude from Part 1 to avoid duplication
    gap_site_ids = {g['site_id'] for g in (gap_results or {}).get('gaps', []) if g.get('our_status') == 'not_found'}
    generic_only = [r for r in generic_sites if r.site.id not in gap_site_ids]

    lines = [
        f'CITATION SUBMISSION PACK — {name.upper()}',
        f'Generated: {date.today().isoformat()}',
        '',
    ]

    if generic_only:
        lines += [
            sep,
            f'PART 1 — GENERAL DIRECTORIES ({len(generic_only)} sites)',
            sep,
            '',
            'Please register the business on each directory below.',
            'For each site: open the link, create a free account, then paste',
            'the business details from the bottom of this message.',
            'Most take 5–10 minutes. Some send a verification email before',
            'the listing goes live — check your inbox after submitting.',
            '',
        ]
        for i, r in enumerate(generic_only, 1):
            lines.append(f'{i}. {r.site.name}')
            lines.append(f'   {r.site.submission_url}')
            lines.append('')

    if assoc_sites:
        lines += [
            sep,
            f'PART 2 — PROFESSIONAL ASSOCIATIONS ({len(assoc_sites)} organisations)',
            sep,
            '',
            'These are membership bodies that include a public therapist directory.',
            'Membership requires proof of qualifications and current professional',
            'indemnity insurance. Contact each organisation to start an application.',
            'Being listed here is a strong trust signal — worth the annual fee.',
            '',
        ]
        for i, r in enumerate(assoc_sites, 1):
            lines.append(f'{i}. {r.site.name}')
            lines.append(f'   {r.site.submission_url}')
            lines.append('')

    if dir_sites:
        lines += [
            sep,
            f'PART 3 — INDUSTRY DIRECTORIES ({len(dir_sites)} sites)',
            sep,
            '',
            'Health and wellness-specific directories. Most allow free',
            'self-registration — open the link and create a practitioner profile.',
            '',
        ]
        for i, r in enumerate(dir_sites, 1):
            lines.append(f'{i}. {r.site.name}')
            lines.append(f'   {r.site.submission_url}')
            lines.append('')

    if gap_results:
        action_gaps = [g for g in gap_results.get('gaps', []) if g.get('our_status') == 'not_found']
        if action_gaps:
            n_comp = gap_results.get('competitors', [])
            lines += [
                sep,
                f'PART 4 — COMPETITOR GAPS ({len(action_gaps)} sites)',
                sep,
                '',
                f'Your top {len(n_comp)} GBP competitors appear on these sites but we don\'t.',
                'These are priority targets — submit here first.',
                '',
            ]
            for i, g in enumerate(action_gaps, 1):
                lines.append(f'{i}. {g["site_name"]} ({g["competitor_count"]}/{len(n_comp)} competitors listed)')
                lines.append(f'   {g["submission_url"]}')
                lines.append('')

    lines += [
        sep,
        'BUSINESS DETAILS (copy-paste into every form)',
        sep,
        '',
        f'Name:     {name}',
        f'Address:  {address}',
        f'Phone:    {phone}',
        f'Website:  {website}',
        'Category: Massage Therapist / Health & Beauty',
        '',
        'Short description (50 words):',
        f'{name} — professional massage therapy in {config.get("city", "Glasgow")}.',
        'Expert Thai massage, deep tissue, aromatherapy and wellness treatments.',
        'Fully qualified therapists. Book online or call us to arrange your appointment.',
        '',
    ]

    return '\n'.join(lines)


def _render_gap_row(gap: dict) -> str:
    total = gap['total_competitors']
    count = gap['competitor_count']
    filled = round((count / total) * 8) if total else 0
    bar = '█' * filled + '░' * (8 - filled)
    return f"""<div class="site">
  <h3><input type="checkbox"> {gap['site_name']} — <span style="color:#d97706">&#x26a0; {count}/{total} competitors listed here</span> {bar}</h3>
  <a class="btn" href="{gap['submission_url']}" target="_blank">Open Submission Page</a>
</div>"""


def _render_site_row(result: CitationCheckResult, config: dict) -> str:
    site = result.site
    if result.status == 'not_found':
        status_note = '<span style="color:#dc2626">&#x2717; Not listed</span>'
    elif result.submit_status == 'manual_required':
        status_note = '<span style="color:#d97706">&#x26a0; Automated submission failed</span>'
    else:
        status_note = '<span style="color:#6b7280">Not yet checked</span>'

    return f"""<div class="site">
  <h3><input type="checkbox"> {site.name} — {status_note}</h3>
  <a class="btn" href="{site.submission_url}" target="_blank">Open Submission Page</a>
  <div class="fields">
    <dl>
      <dt>Business Name</dt><dd>{config.get('name', '')}</dd>
      <dt>Address</dt><dd>{config.get('address', '')}</dd>
      <dt>Phone</dt><dd>{config.get('phone', '')}</dd>
      <dt>Website</dt><dd>{config.get('website', '')}</dd>
      <dt>Category</dt><dd>Massage Therapist / Health &amp; Beauty</dd>
    </dl>
  </div>
</div>"""
