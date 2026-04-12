"""
Audit Report Builder

Produces two outputs from an AuditResult:
  1. Internal markdown report (raw data + full findings)
  2. Prospect HTML (OMG-branded, PAS framework, for PDF conversion)
"""

from __future__ import annotations

from typing import List
from scoring import AuditResult, NAPResult, CitationResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def _citation_section_md(nap) -> str:
    """Generate citation detail block for markdown report."""
    if not isinstance(nap, CitationResult) or not nap.site_results:
        return ''
    lines = [
        f'\n### Citations ({nap.found_count}/{nap.total_sites} found, score {nap.score}/15)\n'
    ]
    for r in sorted(nap.site_results, key=lambda x: x.site.priority, reverse=True)[:15]:
        icon = {'found': '✓', 'not_found': '✗', 'unknown': '·', 'duplicate': '⚠'}.get(r.status, '·')
        nap_note = ' — NAP issues: ' + ', '.join(r.issues) if r.issues else ''
        lines.append(f'- {icon} **{r.site.name}** ({r.status}){nap_note}')
    return '\n'.join(lines)


# ── Internal Markdown ─────────────────────────────────────────────────────────

def build_markdown(result: AuditResult) -> str:
    r = result
    lines: List[str] = []

    def h(level: int, text: str):
        lines.append(f'\n{"#" * level} {text}\n')

    def finding_block(findings: List[str], label: str = 'Findings'):
        if findings:
            lines.append(f'**{label}:**')
            for f in findings:
                lines.append(f'- {f}')
        else:
            lines.append(f'**{label}:** None — all checks passed.')

    h(1, f'SEO Audit: {r.site_name} ({r.abbr.upper()})')
    lines.append(f'*Date: {r.date}  |  URL: {r.site_url}*\n')
    lines.append(f'## Overall Score: {r.total_score}/100 (Grade {r.grade_letter})\n')

    lines.append('| Category | Score | Max |')
    lines.append('|----------|------:|----:|')
    lines.append(f'| Schema | {r.schema.score} | 20 |')
    lines.append(f'| Content | {r.content.score} | 20 |')
    lines.append(f'| GBP | {r.gbp.score} | 20 |')
    lines.append(f'| Reviews | {r.reviews.score} | 15 |')
    lines.append(f'| NAP + Citations | {r.nap.score} | 15 |')
    lines.append(f'| Technical | {r.technical.score} | 10 |')
    lines.append(f'| **Total** | **{r.total_score}** | **100** |')

    # ── Schema ────────────────────────────────────────────────────────────────
    h(2, f'Schema — {r.schema.score}/20')
    lines.append(f'- Pages checked: {r.schema.pages_checked}')
    lines.append(f'- LocalBusiness schema: {"✓" if r.schema.has_local_business else "✗"}')
    lines.append(f'- FAQPage schema: {"✓" if r.schema.has_faq else "✗"}')
    lines.append(f'- Article/BlogPosting schema: {"✓" if r.schema.has_article else "✗"}')
    lines.append(f'- Required fields (name/address/phone/url/hours): '
                 f'{sum([r.schema.name_present, r.schema.address_present, r.schema.phone_present, r.schema.url_present, r.schema.opening_hours_present])}/5 present')
    finding_block(r.schema.findings)

    # ── Content ───────────────────────────────────────────────────────────────
    h(2, f'Content — {r.content.score}/20')
    lines.append(f'- Service pages: {r.content.service_count}')
    lines.append(f'- Blog posts: {r.content.blog_count}')
    lines.append(f'- Location pages: {r.content.location_count}')
    lines.append(f'- Static pages: {r.content.page_count}')
    lines.append(f'- Sitemap: {"✓" if r.content.has_sitemap else "✗"} '
                 f'({r.content.sitemap_url_count} URLs)')
    finding_block(r.content.findings)

    # ── GBP ───────────────────────────────────────────────────────────────────
    h(2, f'Google Business Profile — {r.gbp.score}/20')
    if not r.gbp.available:
        lines.append('*GBP data not available — see findings.*')
    else:
        lines.append(f'- Description: {"✓" if r.gbp.has_description else "✗"}')
        lines.append(f'- Categories: {r.gbp.category_count}')
        lines.append(f'- Hours set: {"✓" if r.gbp.has_hours else "✗"}')
        lines.append(f'- Photos: {r.gbp.photo_count}')
        lines.append(f'- Services listed: {r.gbp.services_count}')
    finding_block(r.gbp.findings)

    # ── Reviews ───────────────────────────────────────────────────────────────
    h(2, f'Reviews — {r.reviews.score}/15')
    if not r.reviews.available:
        lines.append('*Review data not available — see findings.*')
    else:
        lines.append(f'- Total reviews: {r.reviews.count}')
        lines.append(f'- Average rating: {r.reviews.average_rating:.1f}')
        lines.append(f'- Response rate: {int(r.reviews.response_rate * 100)}%')
    finding_block(r.reviews.findings)

    # ── NAP / Citations ───────────────────────────────────────────────────────
    h(2, f'NAP + Citations — {r.nap.score}/15')
    _icons = {'match': '✓', 'mismatch': '✗', 'unknown': '?'}
    if isinstance(r.nap, CitationResult):
        lines.append(f'- Schema name: {_icons.get(r.nap.schema_name_match, "?")}')
        lines.append(f'- Schema address: {_icons.get(r.nap.schema_address_match, "?")}')
        lines.append(f'- Schema phone: {_icons.get(r.nap.schema_phone_match, "?")}')
        lines.append(f'- Citations found: {r.nap.found_count}/{r.nap.total_sites}')
        if r.nap.nap_issue_count:
            lines.append(f'- NAP issues across citations: {r.nap.nap_issue_count}')
        if r.nap.duplicate_count:
            lines.append(f'- Duplicate listings: {r.nap.duplicate_count}')
        if r.nap.critical_missing:
            lines.append(f'- Critical sites missing: {", ".join(r.nap.critical_missing)}')
    else:
        lines.append(f'- Name: {_icons[r.nap.name_match]}  '
                     f'Config="{r.nap.config_name}"  |  Schema="{r.nap.schema_name}"')
        lines.append(f'- Address: {_icons[r.nap.address_match]}  '
                     f'Config="{r.nap.config_address}"  |  Schema="{r.nap.schema_address}"')
        lines.append(f'- Phone: {_icons[r.nap.phone_match]}  '
                     f'Config="{r.nap.config_phone}"  |  Schema="{r.nap.schema_phone}"')
    finding_block(r.nap.findings)
    lines.append(_citation_section_md(r.nap))

    # ── Technical ─────────────────────────────────────────────────────────────
    h(2, f'Technical — {r.technical.score}/10')
    lines.append(f'- HTTPS: {"✓" if r.technical.has_ssl else "✗"}')
    lines.append(f'- Meta title: {"✓" if r.technical.has_meta_title else "✗"}')
    lines.append(f'- Meta description: {"✓" if r.technical.has_meta_description else "✗"}')
    lines.append(f'- H1 tag: {"✓" if r.technical.has_h1 else "✗"}')
    lines.append(f'- robots.txt: {"✓" if r.technical.has_robots else "✗"}')
    lines.append(f'- Sitemap: {"✓" if r.technical.has_sitemap else "✗"}')
    lines.append(f'- Response time: {r.technical.response_time_ms}ms')
    finding_block(r.technical.findings)

    # ── Competitor Benchmark ──────────────────────────────────────────────────
    h(2, 'Competitor Benchmark (unscored)')
    if not r.competitor.available:
        lines.append('*Run `research_competitors.py` to generate competitor data.*')
    else:
        lines.append(f'- Map pack position: {r.competitor.client_map_position}')
        lines.append(f'- Top competitors: {", ".join(r.competitor.top_competitors[:3])}')
    if r.competitor.notes:
        for note in r.competitor.notes:
            lines.append(f'- {note}')

    return '\n'.join(lines)


# ── Prospect HTML ─────────────────────────────────────────────────────────────

_GRADE_COLOURS = {
    'A': ('#00875a', 'Excellent'),
    'B': ('#0052cc', 'Good'),
    'C': ('#ff991f', 'Fair'),
    'D': ('#de350b', 'Weak'),
    'F': ('#6554c0', 'Critical'),
}

_CATEGORY_LABELS = {
    'schema':    ('Schema Markup',        'Tells Google exactly what your business offers'),
    'content':   ('Website Content',      'Service pages, blog posts, and local landing pages'),
    'gbp':       ('Google Business Profile', 'Your profile in Google Maps and local search'),
    'reviews':   ('Reviews & Reputation', 'Review count, rating, and response rate'),
    'nap':       ('NAP + Citations',       'Name/address/phone consistency and directory presence'),
    'technical': ('Technical Health',     'SSL, page speed, meta tags, and sitemaps'),
}


def _score_bar(score: int, max_score: int) -> str:
    pct = int((score / max_score) * 100) if max_score else 0
    if pct >= 75:
        colour = '#00875a'
    elif pct >= 50:
        colour = '#ff991f'
    else:
        colour = '#de350b'
    return f'''
      <div class="bar-wrap">
        <div class="bar-fill" style="width:{pct}%;background:{colour};"></div>
      </div>
      <span class="bar-label">{score}/{max_score}</span>'''


def _finding_list(findings: List[str], max_items: int = 3) -> str:
    if not findings:
        return '<p class="finding-ok">✓ No critical issues found in this area.</p>'
    html = '<ul class="findings">'
    for f in findings[:max_items]:
        html += f'<li>{f}</li>'
    if len(findings) > max_items:
        html += f'<li class="more">…and {len(findings) - max_items} more issues</li>'
    html += '</ul>'
    return html


def build_prospect_html(result: AuditResult) -> str:
    r = result
    grade_colour, grade_label = _GRADE_COLOURS.get(r.grade_letter, ('#666', 'Unknown'))

    # Summary sentence for the PAS hero section
    total_findings = sum([
        len(r.schema.findings), len(r.content.findings),
        len(r.gbp.findings), len(r.reviews.findings),
        len(r.nap.findings), len(r.technical.findings),
    ])
    score_pct = r.total_score
    if score_pct >= 85:
        problem_headline = 'Your online presence is strong — let\'s make it unbeatable.'
        problem_body = (
            f'{r.site_name} scored {r.total_score}/100 in our audit. '
            'There are still opportunities to pull further ahead of your competitors.'
        )
    elif score_pct >= 55:
        problem_headline = f'Your website has {total_findings} gaps your competitors are exploiting.'
        problem_body = (
            f'{r.site_name} scored {r.total_score}/100 in our audit. '
            'These gaps are reducing your visibility in Google and costing you bookings every week.'
        )
    else:
        problem_headline = f'Critical: {total_findings} issues are actively blocking your growth.'
        problem_body = (
            f'{r.site_name} scored {r.total_score}/100 in our audit. '
            'Without fixing these, Google is unlikely to show your business to local customers — '
            'regardless of how good your service actually is.'
        )

    # Agitate — what the cost really is
    agitate_points = []
    if r.schema.score < 12:
        agitate_points.append(
            'Google cannot properly verify your business details — your competitors with correct '
            'schema markup are getting rich results (stars, FAQs, opening times) that you\'re not.'
        )
    if r.content.blog_count < 3:
        agitate_points.append(
            'With fewer than 3 blog posts, your website has almost no chance of ranking for '
            'informational searches — the queries your future customers type before they book.'
        )
    if r.reviews.score < 8 and r.reviews.available:
        agitate_points.append(
            f'Your {r.reviews.count} reviews and {r.reviews.average_rating:.1f}★ average '
            'puts you behind competitors with 50+ reviews. Most customers won\'t even click on '
            'a business with fewer than 20 reviews.'
        )
    if r.gbp.score < 12 and r.gbp.available:
        agitate_points.append(
            'An incomplete Google Business Profile means you\'re invisible in the local 3-pack — '
            'the map results that get 40% of all local search clicks.'
        )
    if not agitate_points:
        agitate_points.append(
            'Every week these gaps remain open, your competitors are capturing the customers '
            'who should be booking with you.'
        )

    agitate_html = ''.join(f'<li>{pt}</li>' for pt in agitate_points[:3])

    # Build category rows
    cat_rows = ''
    cat_data = [
        ('schema',    r.schema.score,    20, r.schema.findings),
        ('content',   r.content.score,   20, r.content.findings),
        ('gbp',       r.gbp.score,       20, r.gbp.findings),
        ('reviews',   r.reviews.score,   15, r.reviews.findings),
        ('nap',       r.nap.score,       15, r.nap.findings),
        ('technical', r.technical.score, 10, r.technical.findings),
    ]
    for key, score, max_s, findings in cat_data:
        label, desc = _CATEGORY_LABELS[key]
        cat_rows += f'''
        <div class="cat-row">
          <div class="cat-info">
            <span class="cat-name">{label}</span>
            <span class="cat-desc">{desc}</span>
          </div>
          <div class="cat-score-wrap">
            {_score_bar(score, max_s)}
          </div>
          <div class="cat-findings">
            {_finding_list(findings, max_items=2)}
          </div>
        </div>'''

    # Competitor section
    comp_html = ''
    if r.competitor.available and r.competitor.top_competitors:
        names = ', '.join(r.competitor.top_competitors[:3])
        pos_text = (
            f' Your current map pack position: <strong>{r.competitor.client_map_position}</strong>.'
            if r.competitor.client_map_position != 'unknown' else ''
        )
        comp_html = f'''
        <div class="comp-section">
          <h3>Your Competitive Landscape</h3>
          <p>We identified your top local competitors: <strong>{names}</strong>.{pos_text}
          Our content strategy is designed specifically to outrank these businesses for
          the keywords your customers are searching.</p>
        </div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SEO Audit Report — {r.site_name}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            font-size: 14px; color: #172b4d; background: #fff; line-height: 1.5; }}

    /* ── OMG Header ─────────────────────────────────────────────────── */
    .header {{
      background: linear-gradient(135deg, #1a2744 0%, #0d1b36 100%);
      color: #fff;
      padding: 32px 48px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}
    .header-brand {{ }}
    .agency-name {{ font-size: 22px; font-weight: 700; letter-spacing: -0.5px; color: #fff; }}
    .agency-tag  {{ font-size: 11px; color: #8fa4cc; margin-top: 2px; letter-spacing: 0.5px;
                   text-transform: uppercase; }}
    .header-meta {{ text-align: right; }}
    .report-title {{ font-size: 13px; color: #8fa4cc; text-transform: uppercase;
                    letter-spacing: 1px; margin-bottom: 4px; }}
    .report-client {{ font-size: 18px; font-weight: 600; color: #fff; }}
    .report-date   {{ font-size: 11px; color: #8fa4cc; margin-top: 4px; }}

    /* ── Grade Hero ─────────────────────────────────────────────────── */
    .grade-hero {{
      background: #f4f5f7;
      padding: 32px 48px;
      display: flex;
      align-items: center;
      gap: 40px;
      border-bottom: 3px solid {grade_colour};
    }}
    .grade-circle {{
      width: 90px; height: 90px; border-radius: 50%;
      background: {grade_colour};
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      flex-shrink: 0;
    }}
    .grade-letter {{ font-size: 36px; font-weight: 800; color: #fff; line-height: 1; }}
    .grade-pts    {{ font-size: 12px; color: rgba(255,255,255,0.85); margin-top: 2px; }}
    .grade-summary {{ flex: 1; }}
    .grade-label  {{ font-size: 13px; font-weight: 600; color: {grade_colour};
                    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }}
    .grade-headline {{ font-size: 20px; font-weight: 700; color: #172b4d; line-height: 1.3; }}
    .grade-body     {{ font-size: 13px; color: #5e6c84; margin-top: 8px; }}

    /* ── Sections ───────────────────────────────────────────────────── */
    .section {{ padding: 32px 48px; border-bottom: 1px solid #ebecf0; }}
    .section-title {{ font-size: 18px; font-weight: 700; color: #172b4d;
                     margin-bottom: 6px; display: flex; align-items: center; gap: 10px; }}
    .section-tag   {{ font-size: 11px; font-weight: 600; text-transform: uppercase;
                     letter-spacing: 1px; padding: 2px 8px; border-radius: 3px; }}
    .tag-problem   {{ background: #ffebe6; color: #de350b; }}
    .tag-agitate   {{ background: #fffae6; color: #974f0c; }}
    .tag-solution  {{ background: #e3fcef; color: #006644; }}

    /* ── Agitate list ───────────────────────────────────────────────── */
    .agitate-list {{ margin-top: 16px; }}
    .agitate-list li {{ padding: 12px 16px; margin-bottom: 8px; border-left: 3px solid #de350b;
                        background: #fff4f0; border-radius: 0 4px 4px 0; }}

    /* ── Score breakdown ────────────────────────────────────────────── */
    .cat-row {{ margin-bottom: 20px; padding: 16px; background: #f9fafb;
               border-radius: 6px; border: 1px solid #ebecf0; }}
    .cat-info {{ display: flex; align-items: baseline; gap: 12px; margin-bottom: 10px; }}
    .cat-name {{ font-weight: 600; font-size: 14px; color: #172b4d; }}
    .cat-desc {{ font-size: 12px; color: #5e6c84; }}
    .cat-score-wrap {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
    .bar-wrap {{ flex: 1; height: 10px; background: #ebecf0; border-radius: 5px; overflow: hidden; }}
    .bar-fill {{ height: 100%; border-radius: 5px; transition: width 0.3s; }}
    .bar-label {{ font-size: 12px; font-weight: 600; color: #5e6c84; white-space: nowrap; }}
    .findings {{ margin: 0; padding-left: 18px; }}
    .findings li {{ font-size: 12px; color: #5e6c84; margin-bottom: 4px; }}
    .findings li.more {{ color: #8993a4; font-style: italic; }}
    .finding-ok {{ font-size: 12px; color: #006644; }}

    /* ── Solution section ───────────────────────────────────────────── */
    .solution-grid {{ display: grid; grid-template-columns: repeat(3, 1fr);
                     gap: 16px; margin-top: 20px; }}
    .solution-card {{ background: #f4f5f7; border-radius: 8px; padding: 20px;
                     border-top: 3px solid #1a2744; }}
    .sol-num  {{ font-size: 24px; font-weight: 800; color: #1a2744; line-height: 1; }}
    .sol-title {{ font-size: 13px; font-weight: 700; color: #172b4d; margin: 6px 0 4px; }}
    .sol-desc  {{ font-size: 12px; color: #5e6c84; line-height: 1.5; }}

    /* ── Competitor section ─────────────────────────────────────────── */
    .comp-section {{ margin-top: 20px; padding: 16px; background: #e6f0ff;
                    border-radius: 6px; border-left: 3px solid #0052cc; }}
    .comp-section h3 {{ font-size: 14px; font-weight: 600; color: #0052cc; margin-bottom: 6px; }}
    .comp-section p {{ font-size: 13px; color: #172b4d; }}

    /* ── CTA ────────────────────────────────────────────────────────── */
    .cta-section {{
      background: linear-gradient(135deg, #1a2744 0%, #0d1b36 100%);
      padding: 40px 48px;
      text-align: center;
      color: #fff;
    }}
    .cta-title {{ font-size: 24px; font-weight: 700; margin-bottom: 10px; }}
    .cta-body  {{ font-size: 14px; color: #8fa4cc; margin-bottom: 24px; max-width: 480px;
                 margin-left: auto; margin-right: auto; }}
    .cta-btn   {{
      display: inline-block; padding: 14px 32px;
      background: #f0a500; color: #1a2744;
      font-weight: 700; font-size: 15px; border-radius: 6px;
      text-decoration: none; letter-spacing: 0.3px;
    }}
    .cta-url   {{ font-size: 11px; color: #4a6394; margin-top: 12px; }}

    /* ── Footer ─────────────────────────────────────────────────────── */
    .footer {{
      padding: 16px 48px;
      background: #f4f5f7;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      color: #8993a4;
    }}
    .footer-brand {{ font-weight: 600; }}
  </style>
</head>
<body>

  <!-- OMG Header -->
  <div class="header">
    <div class="header-brand">
      <div class="agency-name">Online Marketing Group</div>
      <div class="agency-tag">Guaranteed Growth for Your Local Small Business</div>
    </div>
    <div class="header-meta">
      <div class="report-title">SEO Audit Report</div>
      <div class="report-client">{r.site_name}</div>
      <div class="report-date">{r.date}</div>
    </div>
  </div>

  <!-- Grade Hero — Problem -->
  <div class="grade-hero">
    <div class="grade-circle">
      <span class="grade-letter">{r.grade_letter}</span>
      <span class="grade-pts">{r.total_score}/100</span>
    </div>
    <div class="grade-summary">
      <div class="grade-label">{grade_label}</div>
      <div class="grade-headline">{problem_headline}</div>
      <div class="grade-body">{problem_body}</div>
    </div>
  </div>

  <!-- Agitate -->
  <div class="section">
    <div class="section-title">
      What These Gaps Are Costing You
      <span class="section-tag tag-agitate">The Impact</span>
    </div>
    <ul class="agitate-list">
      {agitate_html}
    </ul>
  </div>

  <!-- Score Breakdown -->
  <div class="section">
    <div class="section-title">
      Your Score Breakdown
      <span class="section-tag tag-problem">Where You Stand</span>
    </div>
    {cat_rows}
    {comp_html}
  </div>

  <!-- Solution -->
  <div class="section">
    <div class="section-title">
      Our Plan to Fix This
      <span class="section-tag tag-solution">The Solution</span>
    </div>
    <p style="color:#5e6c84; margin-bottom:4px;">
      Online Marketing Group uses a proven system to turn every one of these gaps
      into a competitive advantage. Here's what we do, in order:
    </p>
    <div class="solution-grid">
      <div class="solution-card">
        <div class="sol-num">01</div>
        <div class="sol-title">Technical Foundation</div>
        <div class="sol-desc">Fix schema markup, meta tags, sitemap, and NAP consistency so Google
          can fully understand and trust your business.</div>
      </div>
      <div class="solution-card">
        <div class="sol-num">02</div>
        <div class="sol-title">Content at Scale</div>
        <div class="sol-desc">Service pages, location pages, and regular blog content — written
          to rank, structured to convert, published on a consistent schedule.</div>
      </div>
      <div class="solution-card">
        <div class="sol-num">03</div>
        <div class="sol-title">GBP & Reviews</div>
        <div class="sol-desc">Optimise your Google Business Profile, build a review strategy,
          and get you into the local 3-pack where 40% of local clicks go.</div>
      </div>
    </div>
  </div>

  <!-- CTA -->
  <div class="cta-section">
    <div class="cta-title">Ready to Fix This?</div>
    <div class="cta-body">
      We only take on clients we\'re confident we can grow. Tell us about your business
      and we\'ll let you know if we\'re a fit.
    </div>
    <a class="cta-btn" href="https://omgmarketinguk.com/">Apply for a Free Strategy Call</a>
    <div class="cta-url">omgmarketinguk.com</div>
  </div>

  <!-- Footer -->
  <div class="footer">
    <span class="footer-brand">Online Marketing Group</span>
    <span>omgmarketinguk.com · Greenock, Scotland</span>
    <span>© 2000-2026 omgmarketinguk.com</span>
  </div>

</body>
</html>'''
