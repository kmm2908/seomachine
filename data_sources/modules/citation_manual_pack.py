# data_sources/modules/citation_manual_pack.py
"""Generates a pre-filled manual citation submission pack (HTML)."""

from __future__ import annotations
from datetime import date
from pathlib import Path

from citation_sites import CitationSite, CitationCheckResult, CITATION_SITES


def generate_manual_pack(
    abbr: str,
    config: dict,
    site_results: list[CitationCheckResult],
    root: Path,
) -> Path:
    """
    Generate manual-pack.html for sites that need manual submission.
    Includes Tier 4 sites + any Tier 3 sites where submit_status == 'manual_required'.
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

    out_dir = root / 'clients' / abbr / 'citations'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'manual-pack.html'
    out_path.write_text(_render_pack(config, all_manual))
    return out_path


def _render_pack(config: dict, results: list[CitationCheckResult]) -> str:
    name = config.get('name', '')
    address = config.get('address', '')
    phone = config.get('phone', '')
    website = config.get('website', '')
    description = config.get('description', f'{name} — professional massage therapy in {config.get("city", "")}.')

    rows = '\n'.join(_render_site_row(r, config) for r in results)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Citation Manual Pack — {name}</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #222; }}
  h1 {{ font-size: 1.4rem; border-bottom: 2px solid #333; padding-bottom: 8px; }}
  h2 {{ font-size: 1.1rem; margin-top: 2rem; }}
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

<script>
document.querySelectorAll('input[type=checkbox]').forEach(cb => {{
  cb.addEventListener('change', () => {{
    cb.closest('.site').classList.toggle('done', cb.checked);
  }});
}});
</script>
</body>
</html>"""


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
