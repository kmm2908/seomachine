"""
ImageGenerator
==============
Generates banner and section images for content posts using Gemini 3.1 Flash.

Per post: 1 banner (1200x500) + 1 section image per HTML section (400x300).
Images are saved alongside the HTML file and injected as <img> tags into the HTML.

Cost: ~$0.09/image (Gemini 3.1 Flash, 2K)
"""

import base64
import os
import re
import time
from pathlib import Path

import requests

# ── Gemini API ────────────────────────────────────────────────────────────────

GEMINI_MODEL = "gemini-3.1-flash-image-preview"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# ── DALL-E 3 API (fallback) ───────────────────────────────────────────────────

DALLE_URL = "https://api.openai.com/v1/images/generations"

# ── Pricing ───────────────────────────────────────────────────────────────────

COST_PER_IMAGE = 0.09        # Gemini 3.1 Flash, 2K image
DALLE_COST_BANNER = 0.080    # DALL-E 3, 1792x1024 standard
DALLE_COST_SECTION = 0.040   # DALL-E 3, 1024x1024 standard

# ── Gemini retry settings ─────────────────────────────────────────────────────

GEMINI_RETRY_DELAYS = [30, 60, 120]  # seconds between retries on 503

# ── Banner action phrases ─────────────────────────────────────────────────────
# Short action phrases for use inside BANNER_TEMPLATE's {scene} slot.
# Must be grammatically compatible with "...performs {scene} on a female client..."

BANNER_ACTION_MAP = {
    "couples":      "a couples Thai back massage",
    "deep tissue":  "a deep tissue back massage",
    "sports":       "a sports massage on a client's leg",
    "aromatherapy": "an aromatherapy oil back massage",
    "hot stone":    "a hot stone back massage",
    "foot":         "a Thai foot massage",
    "facial":       "a facial massage",
    "head":         "an Indian head massage",
    "thai":         "a traditional Thai back massage",
}

BANNER_FALLBACK_ACTION = "a traditional Thai back massage"

# ── Topic → scene description map ────────────────────────────────────────────
# Keywords are matched against the topic/H2 text (lowercase).
# "section": therapist + client interaction scene for the section image

TOPIC_CONTEXT_MAP = {
    "couples": {
        "banner": "two side-by-side massage tables with white linen, rose petals, candlelit luxury spa room, no people",
        "section": "spa therapist giving a back massage to a woman on a treatment table, second treatment table visible in background, luxury spa room, warm light",
    },
    "deep tissue": {
        "banner": "professional massage studio with white treatment table, therapeutic spa setting, no people",
        "section": "massage therapist performing deep tissue back massage on a client lying on a treatment table, professional studio lighting",
    },
    "sports": {
        "banner": "sports therapy studio, white treatment table, clean professional setting, no people",
        "section": "sports massage therapist working on client's calf muscles, treatment table, professional studio",
    },
    "aromatherapy": {
        "banner": "aromatherapy spa studio, essential oil bottles, candles, white treatment table, orchids, no people",
        "section": "spa therapist applying aromatherapy oil massage to a client's back, warm candlelit room",
    },
    "hot stone": {
        "banner": "luxury spa treatment room with basalt stones on white treatment table, candles, no people",
        "section": "spa therapist placing hot basalt stones on client's back, professional spa setting",
    },
    "foot": {
        "banner": "Thai spa room with foot bath bowl, flower petals, pebbles, candles, no people",
        "section": "spa therapist performing foot massage on a client, close view of hands and feet, treatment room",
    },
    "facial": {
        "banner": "facial spa treatment room, white table, botanical skincare products, orchids, no people",
        "section": "spa therapist performing facial massage on a woman lying on treatment table, soft lighting",
    },
    "head": {
        "banner": "Thai massage studio interior, warm amber lighting, Thai silk decor, no people",
        "section": "therapist performing head and scalp massage on a seated client, professional spa setting",
    },
    "thai": {
        "banner": "Thai massage studio interior, warm amber lighting, Thai silk cushions, wooden accents, orchid decorations, no people",
        "section": "Thai massage therapist performing traditional Thai massage on a client lying on a floor mat, professional studio",
    },
}

FAQ_SECTION_PROMPT = (
    "A relaxed female client in a white spa robe seated in a Thai spa waiting area. "
    "Orchids on a carved wooden stand, teak wood walls, warm amber pendant lighting, "
    "folded white towels on a shelf. "
    "Shot on Leica M11, 50mm f/2 Summicron, Kodak Portra 400 film grain, "
    "natural window light from the side. Real photograph, no CGI, no illustration."
)

BANNER_TEMPLATE = (
    "Editorial spa photograph. "
    "A Thai female massage therapist in a white uniform performs {scene} "
    "on a female client lying face-down on a white-linen treatment table. "
    "No other people visible. "
    "Room: dark teak wood walls, warm amber pendant lighting, white orchids on a carved wooden stand, "
    "folded white towels on a shelf. "
    "Shot on Leica M11, 28mm f/2 Summicron, Kodak Portra 400 film grain, "
    "natural skylight from above, no studio flash, authentic location feel. "
    "Real photograph, no CGI, no illustration, no digital art."
)

SECTION_TEMPLATE = (
    "{scene}, "
    "warm soft natural window light, professional spa environment, "
    "shot on Leica M11, 50mm f/2 Summicron, Kodak Portra 400 film grain, "
    "authentic location feel, real photograph, no CGI, no illustration."
)

BANNER_FALLBACK_SCENE = (
    "a traditional Thai back massage"
)

SECTION_FALLBACK_SCENE = (
    "spa therapist performing a back massage on a client lying on a white-linen treatment table, "
    "professional Thai spa setting"
)


class ImageGenerator:

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_AI_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise EnvironmentError("GOOGLE_AI_API_KEY not set in environment")

    def generate_for_post(self, html_content: str, topic: str, filepath: Path,
                          content_type: str = "blog") -> float:
        """Generate banner + section images for a post.

        Saves images alongside the HTML file and injects <img> tags into the HTML.
        Returns the total image cost in USD.
        """
        article_dir = filepath.parent
        # Strip date suffix to get a clean keyword slug, e.g. "glasgow-central-station"
        base_slug = re.sub(r'-\d{4}-\d{2}-\d{2}$', '', filepath.stem)

        section_headings = self._extract_section_headings(html_content)
        is_location_type = content_type == "location"

        # Generate banner — filename includes article keywords
        banner_path = article_dir / f"{base_slug}-banner.jpg"
        if is_location_type:
            banner_prompt = self._build_location_banner_prompt(topic)
        else:
            banner_prompt = self._build_banner_prompt(topic)
        total_cost = self._generate(banner_prompt, banner_path, "banner")
        print(f"    → {banner_path.name}")

        # Generate one section image per section — filename is the slugified heading
        section_paths = []
        for i, heading in enumerate(section_headings, 1):
            heading_lower = heading.lower()
            if "faq" in heading_lower or "frequently" in heading_lower or not heading.strip():
                heading_slug = f"{base_slug}-faq"
            else:
                heading_slug = _slugify(heading) or f"{base_slug}-section-{i}"
            section_path = article_dir / f"{heading_slug}.jpg"
            section_prompt = self._build_section_prompt(heading, i)
            total_cost += self._generate(section_prompt, section_path, "section")
            section_paths.append(section_path)
            print(f"    → {section_path.name}")
            if i < len(section_headings):
                time.sleep(2)

        # Inject <img> tags into the HTML and rewrite the file
        self._inject_into_html(filepath, banner_path, section_paths, section_headings, topic)

        return round(total_cost, 4)

    # ── Private methods ───────────────────────────────────────────────────────

    def _extract_section_headings(self, html_content: str) -> list:
        """Split HTML on <!-- SECTION N --> comments and extract the first H2 from each."""
        blocks = re.split(r'<!--\s*SECTION\s*\d+[^>]*-->', html_content)
        # First element is always empty (before SECTION 1), skip it
        blocks = [b for b in blocks if b.strip()]

        headings = []
        for block in blocks:
            match = re.search(r'<h2[^>]*>(.*?)</h2>', block, re.IGNORECASE | re.DOTALL)
            if match:
                # Strip any inner HTML tags from the heading text
                heading_text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                headings.append(heading_text)
            else:
                headings.append("")

        return headings if headings else ["Thai massage treatment", "Frequently Asked Questions"]

    def _build_banner_prompt(self, topic: str) -> str:
        """Build a photorealistic banner prompt from the topic."""
        topic_lower = topic.lower()
        scene = BANNER_FALLBACK_ACTION
        for keyword, action in BANNER_ACTION_MAP.items():
            if keyword in topic_lower:
                scene = action
                break
        return BANNER_TEMPLATE.format(scene=scene)

    def _build_location_banner_prompt(self, topic: str) -> str:
        """Build a wide street/area scene prompt for the banner on location content."""
        return (
            f"Wide editorial street photograph of {topic}, Glasgow city centre. "
            "Sandstone tenement buildings, busy pavement, pedestrians crossing, "
            "parked cars, overcast Scottish daylight, panoramic urban streetscape. "
            "Shot on Leica M11, 28mm f/2 Summicron, Kodak Portra 400 film grain, "
            "real photograph, no CGI, no illustration, no digital art."
        )

    def _build_location_section_prompt(self, topic: str) -> str:
        """Build a street/area scene prompt for section images on location content (unused — kept for reference)."""
        return (
            f"Documentary street photograph of {topic}, Glasgow city centre. "
            "Sandstone tenement buildings, busy pavement, pedestrians crossing, "
            "parked cars, overcast Scottish daylight, urban streetscape. "
            "Shot on Leica M11, 35mm f/2 Summicron, Kodak Portra 400 film grain, "
            "real photograph, no CGI, no illustration, no digital art."
        )

    def _build_section_prompt(self, h2_heading: str, section_num: int) -> str:
        """Build a photorealistic section image prompt from the H2 heading."""
        # FAQ section always gets the waiting-area scene
        if section_num >= 2 or "faq" in h2_heading.lower() or "frequently" in h2_heading.lower():
            return FAQ_SECTION_PROMPT

        scene = self._lookup_scene(h2_heading, "section")
        return SECTION_TEMPLATE.format(scene=scene)

    def _lookup_scene(self, text: str, image_type: str) -> str:
        """Match text against TOPIC_CONTEXT_MAP keywords, return scene description."""
        text_lower = text.lower()
        for keyword, contexts in TOPIC_CONTEXT_MAP.items():
            if keyword in text_lower:
                return contexts.get(image_type, contexts["section"])
        return BANNER_FALLBACK_SCENE if image_type == "banner" else SECTION_FALLBACK_SCENE

    def _generate(self, prompt: str, output_path: Path, image_type: str) -> float:
        """Try Gemini with retries on 503, fall back to DALL-E 3. Returns image cost."""
        last_err = None
        for attempt, delay in enumerate(GEMINI_RETRY_DELAYS):
            try:
                self._generate_gemini(prompt, output_path, image_type)
                return COST_PER_IMAGE
            except RuntimeError as e:
                if '503' in str(e):
                    print(f"    → Gemini 503, retry {attempt + 1}/{len(GEMINI_RETRY_DELAYS)} in {delay}s...")
                    time.sleep(delay)
                    last_err = e
                else:
                    last_err = e
                    break

        if not self.openai_api_key:
            raise RuntimeError(
                f"Gemini failed ({last_err}) and OPENAI_API_KEY not set for DALL-E fallback"
            )
        print(f"    → DALL-E 3 fallback...")
        self._generate_dalle(prompt, output_path, image_type)
        return DALLE_COST_BANNER if image_type == "banner" else DALLE_COST_SECTION

    def _generate_gemini(self, prompt: str, output_path: Path, image_type: str) -> Path:
        """Call Gemini API, decode base64 response, save and crop the image."""
        if image_type == "banner":
            aspect_ratio = "21:9"
            image_size = "2K"
            crop_target = (1200, 500)
        else:
            aspect_ratio = "4:3"
            image_size = "1K"
            crop_target = (400, 300)

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {
                    "aspectRatio": aspect_ratio,
                    "imageSize": image_size,
                },
            },
        }

        response = requests.post(
            f"{GEMINI_URL}?key={self.api_key}",
            json=payload,
            timeout=90,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Gemini API error {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        parts = data["candidates"][0]["content"]["parts"]
        image_part = next((p for p in parts if "inlineData" in p), None)
        if not image_part:
            raise RuntimeError(f"No image in Gemini response: {str(data)[:200]}")

        img_bytes = base64.b64decode(image_part["inlineData"]["data"])
        output_path.write_bytes(img_bytes)
        self._crop_image(output_path, crop_target)
        return output_path

    def _generate_dalle(self, prompt: str, output_path: Path, image_type: str) -> Path:
        """Call DALL-E 3 API, download image, save and crop."""
        size = "1792x1024" if image_type == "banner" else "1024x1024"
        crop_target = (1200, 500) if image_type == "banner" else (400, 300)

        response = requests.post(
            DALLE_URL,
            headers={
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "dall-e-3",
                "prompt": prompt,
                "size": size,
                "quality": "standard",
                "n": 1,
                "response_format": "url",
            },
            timeout=90,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"DALL-E API error {response.status_code}: {response.text[:300]}"
            )

        image_url = response.json()["data"][0]["url"]
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()
        output_path.write_bytes(img_response.content)
        self._crop_image(output_path, crop_target)
        return output_path

    def _crop_image(self, path: Path, target: tuple) -> None:
        """Centre-crop image to target (width, height) using Pillow."""
        try:
            from PIL import Image
            with Image.open(path) as img:
                w, h = img.size
                tw, th = target
                scale = tw / w
                new_h = int(h * scale)
                img = img.resize((tw, new_h), Image.LANCZOS)
                if new_h > th:
                    top = (new_h - th) // 2
                    img = img.crop((0, top, tw, top + th))
                img.save(path, quality=92, optimize=True)
        except ImportError:
            pass  # Pillow not installed — save at original size
        except Exception as e:
            print(f"    ⚠ Crop failed for {path.name}: {e}")

    def _inject_into_html(
        self,
        filepath: Path,
        banner_path: Path,
        section_paths: list,
        section_headings: list,
        topic: str,
    ) -> None:
        """Inject <img> tags into section content at specific positions.

        Banner:       centre-aligned, after the first sentence of section 1
        Section img:  right-aligned, after the 3rd paragraph of section 1
        FAQ img:      left-aligned, 3 paragraphs before the end of section 1
                      (both body images appear before the FAQ section starts)
        Section 2:    no image injection
        """
        html = filepath.read_text(encoding="utf-8")

        # Split on <!-- SECTION N --> comments, keeping the delimiters
        delimiter = re.compile(r'(<!--\s*SECTION\s*\d+[^>]*-->)')
        parts = delimiter.split(html)

        section_num = 0
        result = []
        for part in parts:
            if delimiter.match(part.strip()):
                result.append(part)
                section_num += 1
            elif section_num == 1 and section_paths:
                s1_alt = section_headings[0] if section_headings else topic
                s2_alt = section_headings[1] if len(section_headings) > 1 else topic
                banner_img = (
                    f'<img src="{banner_path.name}" alt="{_escape(topic)}"'
                    f' class="aligncenter" width="1200" height="500">'
                )
                s1_img = (
                    f'<img src="{section_paths[0].name}" alt="{_escape(s1_alt)}"'
                    f' class="alignright" width="400" height="300">'
                )
                faq_img = (
                    f'<img src="{section_paths[1].name}" alt="{_escape(s2_alt)}"'
                    f' class="alignleft" width="400" height="300">'
                ) if len(section_paths) >= 2 else None

                part = _inject_after_first_sentence(part, banner_img)
                part = _inject_at_nth(part, s1_img, tag='p', nth=3)
                if faq_img:
                    part = _inject_near_end(part, faq_img, tag='p', paragraphs_from_end=3)
                result.append(part)
            else:
                # Section 2 (FAQ) and beyond: no image injection
                result.append(part)

        filepath.write_text(''.join(result), encoding="utf-8")


def _escape(text: str) -> str:
    """Escape double quotes for use in HTML attribute values."""
    return text.replace('"', '&quot;')


def _inject_after_first_sentence(html: str, img_tag: str) -> str:
    """Insert img_tag after the first sentence in the first <p> of html.

    Splits the paragraph at the first '. ' boundary. Falls back to inserting
    after the whole first paragraph if no sentence boundary is found.
    """
    p_match = re.search(r'(<p[^>]*>)(.*?)(</p>)', html, re.DOTALL | re.IGNORECASE)
    if not p_match:
        return img_tag + '\n' + html

    p_open, p_content, p_close = p_match.group(1), p_match.group(2), p_match.group(3)
    dot_pos = p_content.find('. ')
    if dot_pos == -1:
        # No sentence boundary — insert after the whole paragraph
        return html[:p_match.end()] + '\n' + img_tag + '\n' + html[p_match.end():]

    first_sent = p_content[:dot_pos + 1]   # up to and including the period
    rest = p_content[dot_pos + 2:]          # skip the space after the period
    rebuilt = (
        p_open + first_sent + p_close +
        '\n' + img_tag + '\n' +
        (p_open + rest + p_close if rest.strip() else '')
    )
    return html[:p_match.start()] + rebuilt + html[p_match.end():]


def _inject_at_nth(html: str, img_tag: str, tag: str = 'p', nth: int = 3) -> str:
    """Insert img_tag after the nth closing </tag> (1-based). Falls back to last if nth exceeds count."""
    positions = [m.end() for m in re.finditer(f'</{re.escape(tag)}>', html, re.IGNORECASE)]
    if not positions:
        return html + '\n' + img_tag
    pos = positions[min(nth - 1, len(positions) - 1)]
    return html[:pos] + '\n' + img_tag + '\n' + html[pos:]


def _inject_near_end(html: str, img_tag: str, tag: str = 'p', paragraphs_from_end: int = 3) -> str:
    """Insert img_tag before the last N closing </tag> tags."""
    positions = [m.end() for m in re.finditer(f'</{re.escape(tag)}>', html, re.IGNORECASE)]
    if not positions:
        return html + '\n' + img_tag
    idx = max(0, len(positions) - paragraphs_from_end)
    pos = positions[idx]
    return html[:pos] + '\n' + img_tag + '\n' + html[pos:]


def _slugify(text: str) -> str:
    """Convert heading text to a lowercase hyphenated filename slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text[:80]  # cap length
