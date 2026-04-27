"""
Content Pipeline
================
Shared functions for generating, writing, and managing SEO content.
Used by publish_scheduled.py and any other content publishing scripts.
"""

import json
import os
import re
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv

# ── Project root and .env ────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.parent.resolve()
load_dotenv(ROOT / '.env')

sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))
from wikipedia import WikipediaResearcher
from quality_gate import QualityGate

# ── Paths ────────────────────────────────────────────────────────────────────
CONTENT_DIR = ROOT / 'content'
CONTEXT_DIR = ROOT / 'context'
AGENTS_DIR = ROOT / '.claude' / 'agents'
CLIENTS_DIR = ROOT / 'clients'

# ── Content type → agent file mapping ────────────────────────────────────────
CONTENT_TYPE_AGENTS = {
    'service':    'service-page-writer.md',
    'location':   'location-page-writer.md',
    'topical':    'topical-writer.md',
    'blog':       'blog-post-writer.md',
    'news':       'blog-post-writer.md',  # news-angle posts; hook threshold relaxed in quality gate
    'pillar':     'pillar-page-writer.md',
    'comp-alt':   'competitor-alt-writer.md',
    'problem':    'problem-page-writer.md',
    'yoga-video': 'yoga-video-writer.md',  # embed-led posts; iframe + credit injected post-generation
}


def extract_youtube_id(url: str) -> Optional[str]:
    """Extract the 11-char video ID from a youtube.com/watch?v= or youtu.be/ URL."""
    if not url:
        return None
    m = re.search(r'(?:v=|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})', url)
    return m.group(1) if m else None

# ── Claude model and pricing ─────────────────────────────────────────────────
MODEL = 'claude-sonnet-4-6'
INPUT_COST_PER_M = 3.00
OUTPUT_COST_PER_M = 15.00


def load_file(path: Path) -> str:
    """Read a file, return empty string if missing."""
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ''


def slugify(text: str) -> str:
    """Convert a string to a URL-safe filename slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text.strip())
    text = re.sub(r'-+', '-', text)
    return text[:80].rstrip('-')


_template_checked: set = set()   # track which clients have been checked this run
_snippets_generated: set = set() # track which clients have had snippets checked this run


def _ensure_directions_snippet(abbr: str) -> None:
    """Generate the directions snippet for a client if it doesn't already exist.
    Runs once per client per batch run."""
    if abbr in _snippets_generated:
        return
    _snippets_generated.add(abbr)
    snippet_path = CLIENTS_DIR / abbr / "snippets" / f"{abbr}-directions.html"
    if snippet_path.exists():
        return
    try:
        sys.path.insert(0, str(ROOT / 'src' / 'snippets'))
        from generate_directions_snippet import generate
        snippet = generate(abbr)
        snippet_path.parent.mkdir(exist_ok=True)
        snippet_path.write_text(snippet, encoding='utf-8')
        print(f"    → Directions snippet: generated ({snippet_path.relative_to(ROOT)})")
    except Exception as e:
        print(f"    → Directions snippet error (skipped): {e}")


def _ensure_template_fresh(abbr: str, wp_config: dict) -> None:
    """Check once per client per run whether the Elementor template needs refreshing."""
    if abbr in _template_checked:
        return
    _template_checked.add(abbr)
    try:
        sys.path.insert(0, str(ROOT / 'src' / 'publishing'))
        from fetch_elementor_template import refresh_if_stale
        refreshed = refresh_if_stale(abbr, wp_config)
        if not refreshed:
            print(f"    → Template: up to date")
    except Exception as e:
        print(f"    → Template check error (skipped): {e}")


def _append_quality_log(root, client: str, content_type: str, topic: str, attempts: int, failures: list) -> None:
    """Append a row to logs/quality-log.csv each time an article is flagged Review."""
    import csv
    log_path = root / 'logs' / 'quality-log.csv'
    log_path.parent.mkdir(exist_ok=True)
    write_header = not log_path.exists()
    with open(log_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(['date', 'client', 'content_type', 'topic', 'attempts', 'failures'])
        writer.writerow([
            datetime.now().strftime('%Y-%m-%d'),
            client,
            content_type,
            topic,
            attempts,
            ' | '.join(failures),
        ])


def load_business_config(abbreviation: str) -> dict:
    """Load business config JSON from clients/[abbr]/config.json. Raises clear error if not found."""
    path = CLIENTS_DIR / abbreviation.lower() / 'config.json'
    if not path.exists():
        raise FileNotFoundError(
            f"No client config found for '{abbreviation}'. "
            f"Expected: {path}. Run /new-client to set one up."
        )
    return json.loads(path.read_text(encoding='utf-8'))


def build_system_prompt(abbreviation: str, content_type: str,
                        business_config: Optional[dict] = None) -> str:
    """Build the system prompt from the relevant agent + client context files."""
    agent_file = CONTENT_TYPE_AGENTS.get(content_type, 'blog-post-writer.md')
    agent = load_file(AGENTS_DIR / agent_file)

    client_dir = CLIENTS_DIR / abbreviation.lower()
    brand_voice = load_file(client_dir / 'brand-voice.md')
    seo_guidelines = load_file(client_dir / 'seo-guidelines.md')
    internal_links = load_file(client_dir / 'internal-links-map.md')
    style_guide = load_file(CONTEXT_DIR / 'style-guide.md')

    parts = [
        "You are running as a standalone automation script. Follow these instructions precisely.\n",
    ]

    if business_config:
        parts.append(f"\n\n## Business Context\n\n```json\n{json.dumps(business_config, indent=2)}\n```")

    parts.append(agent)

    if brand_voice:
        parts.append(f"\n\n## Brand Voice\n\n{brand_voice}")
    if style_guide:
        parts.append(f"\n\n## Style Guide\n\n{style_guide}")
    if seo_guidelines:
        parts.append(f"\n\n## SEO Guidelines\n\n{seo_guidelines}")
    if internal_links:
        parts.append(f"\n\n## Internal Links Map\n\n{internal_links}")

    if content_type == 'comp-alt':
        competitor_analysis = load_file(client_dir / 'competitor-analysis.md')
        if competitor_analysis:
            parts.append(f"\n\n## Competitor Analysis\n\n{competitor_analysis}")

    if content_type in ('blog', 'topical') and business_config:
        ai_vis = business_config.get('ai_visibility', {})
        if ai_vis and any(ai_vis.get(k) for k in ('canonical_description', 'brand_associations', 'positioning_note')):
            canonical = ai_vis.get('canonical_description', '')
            associations = ', '.join(ai_vis.get('brand_associations', []))
            note = ai_vis.get('positioning_note', '')
            section = "## AI Brand Positioning\n\n"
            if canonical:
                section += f"Use this description (verbatim or close to it) when introducing the business:\n> {canonical}\n\n"
            if associations:
                section += f"Weave these brand-problem associations naturally into the content: {associations}\n\n"
            if note:
                section += f"Positioning guidance: {note}"
            parts.append(f"\n\n{section.strip()}")

    parts.append(
        "\n\n## Output Instructions\n\n"
        "Your ENTIRE response must be the HTML content — nothing else. "
        "Start your response with `<!-- SECTION 1 -->` on its own line. "
        "Output all three sections: <!-- SECTION 1 -->, <!-- SECTION 2 FAQ -->, and <!-- SCHEMA -->. "
        "Do not include any frontmatter, markdown, explanation, preamble, or commentary. "
        "Do not wrap the output in a code block. "
        "The output is written directly to a file and pasted into a page template. "
        "Any text outside the HTML will corrupt the output."
    )

    return '\n'.join(parts)


def build_wiki_block(wiki_data: Optional[dict]) -> str:
    """Return a formatted Wikipedia research block to inject into prompts, or empty string."""
    if not wiki_data or not wiki_data.get('found'):
        return ''
    entities = ', '.join(wiki_data['related_entities'][:10])
    return (
        f"\n## Wikipedia Research: {wiki_data['title']}\n"
        f"Source: {wiki_data['url']}\n"
        f"Summary: {wiki_data['summary']}\n"
        f"Related entities from Wikipedia: {entities}\n\n"
        f"Use this as a factual basis for local detail. Include the Wikipedia URL as an outbound "
        f"authority link in the 'About This Area' section — place it naturally within a sentence.\n"
    )


def build_service_prompt(topic: str, business_config: Optional[dict] = None, brief: str = '') -> str:
    """User prompt for service page content."""
    today = date.today().isoformat()
    business_name = business_config.get('name', '') if business_config else ''
    services = business_config.get('services', []) if business_config else []
    brief_section = f"\n\nClient-supplied description to incorporate into the page (use this as source material, not verbatim copy):\n\"\"\"\n{brief.strip()}\n\"\"\"" if brief else ''
    return f"""Write a service page for the following:

Service/Topic: {topic}
Business: {business_name}
Services offered: {', '.join(services)}
Today's date: {today}{brief_section}

Steps you must follow:

1. Use the web_search tool to research this service:
   - "{topic} Glasgow benefits"
   - "{topic} what to expect"

2. Write a 550-700 word service page following the structure in your instructions:
   Section 1 (Hook → What Is It → Benefits → Who It's For → What to Expect → Trust Signals)
   Section 2 (FAQ — 4-6 questions about this service)

3. Output three HTML sections starting with <!-- SECTION 1 -->. No frontmatter, no markdown."""


def build_location_prompt(topic: str, business_config: Optional[dict] = None,
                          wiki_data: Optional[dict] = None) -> str:
    """User prompt for location/area page content."""
    today = date.today().isoformat()
    wiki_block = build_wiki_block(wiki_data)

    is_precise = bool(re.search(r'\b[Gg]\d+\s?\d*[A-Za-z]{0,2}\b', topic)) or len(topic.split()) > 4
    word_count = "minimum 450" if is_precise else "minimum 550"
    search_queries = (
        f'   - "{topic} transport subway bus routes"\n'
        f'   - "{topic} Glasgow landmarks businesses workers"\n'
        f'   - "{topic} Glasgow area facts"'
        if is_precise else
        f'   - "{topic} area Glasgow facts"\n'
        f'   - "{topic} Glasgow businesses residents"\n'
        f'   - "{topic} Glasgow transport links"'
    )

    return f"""Write a location page for the following:

Location: {topic}
Today's date: {today}
{wiki_block}
Steps you must follow:

1. Use the web_search tool to research this location:
{search_queries}

2. Write a {word_count} word location page following the structure in your instructions:
   Section 1 (Area Intro → Why This Business → Services → Getting Here → Trust Signals)
   Section 2 (FAQ — 4-5 questions for someone booking from this location)

3. Output three HTML sections starting with <!-- SECTION 1 -->. No frontmatter, no markdown."""


def build_topical_prompt(topic: str, business_config: Optional[dict] = None,
                         wiki_data: Optional[dict] = None) -> str:
    """User prompt for topical/informational content."""
    today = date.today().isoformat()
    wiki_block = build_wiki_block(wiki_data)
    if wiki_data and wiki_data.get('found'):
        wiki_block = wiki_block.replace(
            "Use this as a factual basis for local detail. Include the Wikipedia URL as an outbound "
            "authority link in the 'About This Area' section — place it naturally within a sentence.",
            "Use this as a reference source for background and related entities. Include the Wikipedia "
            "URL as an outbound authority citation — place it naturally within the article body."
        )
    return f"""Write an informational article on the following topic:

Topic: {topic}
Today's date: {today}
{wiki_block}
Steps you must follow:

1. Use the web_search tool to research this topic:
   - "{topic} benefits research"
   - "{topic} how it works"
   - "{topic} FAQ"

2. Write a 650-900 word informational article following the structure in your instructions.
   Base your content on research findings — cite specific facts where possible.
   Section 1 (Introduction → Main sections → Practical advice)
   Section 2 (FAQ — 4-6 follow-up questions)

3. Output three HTML sections starting with <!-- SECTION 1 -->. No frontmatter, no markdown."""


def build_blog_prompt(topic: str, business_config: Optional[dict] = None) -> str:
    """User prompt for blog post content."""
    today = date.today().isoformat()
    return f"""Write a blog post on the following topic:

Topic: {topic}
Today's date: {today}

Steps you must follow:

1. Use the web_search tool if helpful to find relevant facts or angles:
   - "{topic}"

2. Write a 900-1500 word blog post following the structure in your instructions.
   Keep the tone conversational and engaging.
   Section 1 (Hook intro → body sections with H3 subheadings → closing paragraph)
   Section 2 (FAQ — 4-5 questions related to the topic)

3. Output three HTML sections starting with <!-- SECTION 1 -->. No frontmatter, no markdown."""


def build_comp_alt_prompt(topic: str, business_config: Optional[dict] = None) -> str:
    """User prompt for competitor alternative pages. topic = competitor name."""
    abbr = (business_config.get('abbreviation', '') if business_config else '').lower()
    snippet_path = CLIENTS_DIR / abbr / 'snippets' / f'{abbr}-directions.html'
    directions_widget = load_file(snippet_path)

    return f"""Write a competitor alternative page for the following competitor:

Competitor: {topic}

Instructions:
1. Find the entry for "{topic}" in the Competitor Analysis provided in your system prompt.
   Use only the data in that entry — do not invent details.
2. Follow the page structure in your agent instructions exactly.
3. In the "Getting Here" section, include this directions widget exactly as written — do not modify it:

{directions_widget if directions_widget else '<!-- No directions widget found — omit this section -->'}

4. Output three HTML sections: <!-- SECTION 1 -->, <!-- SECTION 2 FAQ -->, <!-- SCHEMA -->.
   No markdown, no frontmatter, no commentary."""


def build_problem_prompt(topic: str, business_config: Optional[dict] = None) -> str:
    """User prompt for problem/condition page content."""
    today = date.today().isoformat()
    return f"""Write a problem/condition page for the following:

Condition: {topic}
Today's date: {today}

Steps you must follow:

1. Use the web_search tool to research this condition:
   - "{topic} massage therapy benefits"
   - "{topic} causes symptoms NHS"
   - "{topic} Wikipedia"
   Find authoritative sources (Wikipedia, NHS, PubMed, medical journals) to link to.

2. Write a 600-800 word problem page following the structure in your instructions.
   Include at least 2 outbound links to authoritative sources found via your research.
   Section 1 (Hook → What Is It → How Massage Helps → What to Expect → Who Benefits)
   Section 2 (FAQ — 4-6 condition-specific questions)

3. Output three HTML sections starting with <!-- SECTION 1 -->. No frontmatter, no markdown."""


def build_yoga_video_prompt(topic: str, business_config: Optional[dict] = None,
                            youtube_url: str = '', youtube_title: str = '') -> str:
    """User prompt for yoga/stretching video-led blog posts."""
    today = date.today().isoformat()
    title_line = youtube_title or topic
    return f"""Write an embed-led yoga/stretching blog post built around the following YouTube video:

Topic: {topic}
Source video title: {title_line}
Source video URL: {youtube_url}
Today's date: {today}

The video itself is the centrepiece. Your written copy is the wrapper.

Steps you must follow:

1. Output `<!-- SECTION 1 -->` and an `<h2>` containing the primary keyword.
2. Write an 80–120 word intro paragraph framing why someone should watch this specific video. Use a Pain Callout, Story, or Myth Bust hook.
3. Output the literal marker `<!-- YOUTUBE_EMBED -->` on its own line. The publisher replaces this with the iframe and source-credit line — do not output an iframe yourself.
4. Write 1–2 short `<h3>` sections (120–180 words combined) tying the video to a real Glasgow desk-worker / runner / sleeper problem.
5. Close with a 70–100 word CTA paragraph containing exactly one inline link to the booking_url from business config.
6. Output `<!-- SECTION 2 FAQ -->` with 4 `<details>`/`<summary>` questions and 2–3 sentence answers.
7. Output `<!-- SCHEMA -->` with a JSON-LD `@graph` containing BlogPosting, VideoObject, FAQPage, and LocalBusiness — use the literal tokens [YOUTUBE_ID], [YOUTUBE_URL], [YOUTUBE_TITLE], [DATE], [BUSINESS_PHONE], [BUSINESS_URL], [BUSINESS_STREET], [BUSINESS_POSTCODE], [BUSINESS_PRICE_RANGE], [BUSINESS_LOGO], [BANNER_IMAGE_URL] where applicable.

Total written word count: 380–500 words across Sections 1 and 2 combined. No frontmatter. No markdown. No code blocks."""


PROMPT_BUILDERS = {
    'service':    build_service_prompt,
    'location':   build_location_prompt,
    'topical':    build_topical_prompt,
    'blog':       build_blog_prompt,
    'comp-alt':   build_comp_alt_prompt,
    'problem':    build_problem_prompt,
    'yoga-video': build_yoga_video_prompt,
}


def build_user_prompt(topic: str, content_type: str,
                      business_config: Optional[dict] = None,
                      wiki_data: Optional[dict] = None,
                      brief: str = '',
                      youtube_url: str = '',
                      youtube_title: str = '') -> str:
    """Build the user prompt for the given content type."""
    builder = PROMPT_BUILDERS.get(content_type, build_blog_prompt)
    if content_type in ('location', 'topical'):
        return builder(topic, business_config, wiki_data)
    if content_type == 'service' and brief:
        return builder(topic, business_config, brief=brief)
    if content_type == 'yoga-video':
        return builder(topic, business_config, youtube_url=youtube_url, youtube_title=youtube_title)
    return builder(topic, business_config)


def write_content_file(topic: str, content: str, abbreviation: str,
                       content_type: str) -> Path:
    """Save content to content/[abbr]/[type]/[slug]-[date]/ and return the file path."""
    slug = slugify(topic)
    today = date.today().isoformat()
    article_dir = CONTENT_DIR / abbreviation.lower() / content_type / f"{slug}-{today}"
    article_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{slug}-{today}.html"
    filepath = article_dir / filename
    filepath.write_text(content, encoding='utf-8')
    return filepath


def extract_word_count(content: str) -> int:
    """Estimate word count from HTML content (strips tags and comments)."""
    text = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def calculate_cost(usage) -> float:
    """Calculate USD cost from an API usage object."""
    input_tokens = getattr(usage, 'input_tokens', 0) or 0
    output_tokens = getattr(usage, 'output_tokens', 0) or 0
    return (input_tokens / 1_000_000 * INPUT_COST_PER_M) + \
           (output_tokens / 1_000_000 * OUTPUT_COST_PER_M)


def generate_content(topic: str, abbreviation: str, content_type: str,
                     client: anthropic.Anthropic,
                     business_config: Optional[dict] = None,
                     brief: str = '',
                     youtube_url: str = '',
                     youtube_title: str = ''):
    """Call Claude API to research and write content.
    Returns (content: str, cost_usd: float).
    """
    system_prompt = build_system_prompt(abbreviation, content_type, business_config)

    wiki_data = None
    if content_type in ('location', 'topical'):
        wiki_data = WikipediaResearcher().research(topic)
        if wiki_data.get('found'):
            print(f"    Wikipedia: found '{wiki_data['title']}' — {wiki_data['url']}")
        else:
            print(f"    Wikipedia: no page found for '{topic}'")

    user_prompt = build_user_prompt(topic, content_type, business_config,
                                    wiki_data=wiki_data, brief=brief,
                                    youtube_url=youtube_url, youtube_title=youtube_title)

    for attempt in range(2):
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=4096,
                system=system_prompt,
                tools=[
                    {"type": "web_search_20260209", "name": "web_search"},
                ],
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
            ) as stream:
                final = stream.get_final_message()
            break
        except anthropic.RateLimitError:
            if attempt == 0:
                print("    Rate limited — waiting 70 seconds before retry...")
                time.sleep(70)
            else:
                raise

    cost_usd = calculate_cost(final.usage)

    text_blocks = [
        block.text.strip()
        for block in final.content
        if block.type == 'text' and block.text.strip()
    ]

    if not text_blocks:
        raise ValueError("No text content in response")

    cleaned = []
    for block in text_blocks:
        if block.startswith('```'):
            block = re.sub(r'^```\w*\n?', '', block)
            block = re.sub(r'\n?```$', '', block)
        cleaned.append(block.strip())
    text_blocks = cleaned

    for block in text_blocks:
        if block.startswith('<!-- SECTION 1 -->'):
            return block, cost_usd

    for block in text_blocks:
        if '<!-- SECTION 1 -->' in block:
            return block[block.index('<!-- SECTION 1 -->'):], cost_usd

    longest = max(text_blocks, key=len)
    if '<!-- SECTION 1 -->' in longest:
        return longest[longest.index('<!-- SECTION 1 -->'):], cost_usd
    return longest, cost_usd
