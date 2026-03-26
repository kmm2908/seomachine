"""Social post and video script generator.

Uses Claude API to generate platform-specific social media posts
and a structured video narration script from a blog article.
"""
import sys
import os
import re
import json
from pathlib import Path
from html.parser import HTMLParser

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent.parent.resolve()
load_dotenv(ROOT / '.env')

MODEL = 'claude-sonnet-4-6'
INPUT_COST_PER_M = 3.00
OUTPUT_COST_PER_M = 15.00


class _HTMLTextExtractor(HTMLParser):
    """Strip HTML tags, extract text and structure."""

    def __init__(self):
        super().__init__()
        self._text_parts: list[str] = []
        self._headings: list[str] = []
        self._in_heading = False
        self._current_heading = ''
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self._skip = True
        if tag in ('h2', 'h3'):
            self._in_heading = True
            self._current_heading = ''

    def handle_endtag(self, tag):
        if tag == 'script':
            self._skip = False
        if tag in ('h2', 'h3') and self._in_heading:
            self._in_heading = False
            self._headings.append(self._current_heading.strip())

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_heading:
            self._current_heading += data
        self._text_parts.append(data)


def extract_content_from_html(html: str) -> dict:
    """Parse blog HTML into structured content for the generator."""
    section1 = ''
    section2 = ''
    if '<!-- SECTION 1 -->' in html:
        parts = html.split('<!-- SECTION 2 FAQ -->')
        section1 = parts[0].replace('<!-- SECTION 1 -->', '').strip()
        if len(parts) > 1:
            faq_and_schema = parts[1].split('<!-- SCHEMA -->')
            section2 = faq_and_schema[0].strip()

    title_match = re.search(r'<h2[^>]*>(.*?)</h2>', section1, re.DOTALL)
    title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else ''

    extractor = _HTMLTextExtractor()
    extractor.feed(section1)
    body_text = ' '.join(extractor._text_parts).strip()
    headings = extractor._headings

    faq_questions = []
    faq_matches = re.findall(
        r'<summary>(.*?)</summary>\s*<p>(.*?)</p>',
        section2, re.DOTALL
    )
    for q, a in faq_matches:
        faq_questions.append({
            'question': re.sub(r'<[^>]+>', '', q).strip(),
            'answer': re.sub(r'<[^>]+>', '', a).strip(),
        })

    return {
        'title': title,
        'body_text': body_text,
        'headings': headings,
        'faq_questions': faq_questions,
        'section1_html': section1,
        'section2_html': section2,
    }


def _build_prompt(content: dict, metadata: dict) -> str:
    """Build the Claude prompt for generating social content."""
    return f"""You are a social media content strategist for {metadata['business_name']}.

Given this blog article, generate TWO things in a single JSON response:

1. A **video narration script** for a YouTube video (target 8-12 minutes).
2. **Social media posts** for LinkedIn, Facebook, X (Twitter), Instagram, and Google Business Profile.

## Article Title
{content['title']}

## Article Body
{content['body_text']}

## FAQ Questions
{json.dumps(content['faq_questions'], indent=2)}

## Article URL
{metadata['post_url']}

## Booking URL
{metadata['booking_url']}

## Instructions

### Video Script
- Structure as scenes. Each scene has: narration text, visual_type (ken_burns, slide, text_overlay, or mixed), visual_description, duration_hint, source_image (banner.jpg or null), text_overlay (optional).
- Mix visual types for variety — don't use the same type for consecutive scenes.
- Target 8-12 minutes total narration (roughly 1200-1800 words of narration).
- Include an engaging intro scene and a CTA closing scene with booking URL.
- Also identify 3-5 best "short-worthy" segments as shorts. Each short needs: type (myth_bust, faq_answer, quick_tip, surprising_fact, or cta), a hook (compelling first line for the first 3 seconds), narration (20-45 seconds worth), visual_type, text_overlays (3-5 short lines for on-screen text), duration_target, and source_scenes (which scene numbers it draws from).

### Social Posts
- **LinkedIn**: Professional tone, 200-300 words, include article link, 3-5 relevant hashtags.
- **Facebook**: Conversational tone, 100-150 words, include article link, 2-3 hashtags.
- **X thread** (x_thread): 4 tweets. Tweet 1 has media: "banner". Others media: null. Each tweet max 280 chars.
- **X standalone** (x_standalone): 5 standalone tweets with day_offset 0-4. Each max 280 chars. Include article link in tweets 1 and 5.
- **Instagram**: Long caption 200-300 words with line breaks, 15-20 hashtags, media: "banner".
- **GBP**: Short locally-focused post 100-150 words, cta_type: "BOOK", cta_url: "{metadata['booking_url']}", media: "banner".

## Output Format

Respond with ONLY valid JSON (no markdown, no code blocks, no explanation):

{{
  "video_script": {{
    "title": "YouTube video title",
    "description": "YouTube description with keywords and links",
    "tags": ["tag1", "tag2"],
    "thumbnail_text": "2-3 word thumbnail text",
    "scenes": [...],
    "shorts": [...]
  }},
  "social_posts": {{
    "linkedin": {{"text": "...", "hashtags": [...]}},
    "facebook": {{"text": "...", "hashtags": [...]}},
    "x_thread": [{{"text": "...", "media": "banner"}}, ...],
    "x_standalone": [{{"text": "...", "day_offset": 0}}, ...],
    "instagram": {{"caption": "...", "hashtags": [...], "media": "banner"}},
    "gbp": {{"text": "...", "cta_type": "BOOK", "cta_url": "...", "media": "banner"}}
  }}
}}"""


class SocialPostGenerator:
    """Generates video scripts and social posts from blog articles."""

    def __init__(self, api_key: str | None = None):
        self._client = anthropic.Anthropic(
            api_key=api_key or os.getenv('ANTHROPIC_API_KEY')
        )

    def generate(self, html: str, metadata: dict) -> tuple[dict, float]:
        """Generate video script + social posts from blog HTML.
        Returns (result_dict, cost_usd).
        """
        content = extract_content_from_html(html)
        prompt = _build_prompt(content, metadata)

        for attempt in range(2):
            try:
                with self._client.messages.stream(
                    model=MODEL,
                    max_tokens=8096,
                    messages=[{'role': 'user', 'content': prompt}],
                ) as stream:
                    final = stream.get_final_message()
                break
            except anthropic.RateLimitError:
                if attempt == 0:
                    import time
                    print('    → Rate limited — waiting 70 seconds...')
                    time.sleep(70)
                else:
                    raise

        cost = (
            (final.usage.input_tokens / 1_000_000 * INPUT_COST_PER_M) +
            (final.usage.output_tokens / 1_000_000 * OUTPUT_COST_PER_M)
        )

        text = final.content[0].text.strip()
        if text.startswith('```'):
            text = re.sub(r'^```\w*\n?', '', text)
            text = re.sub(r'\n?```$', '', text)
            text = text.strip()

        result = json.loads(text)
        return result, cost
