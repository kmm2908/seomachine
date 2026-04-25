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

# ── gpt-image-1 API (fallback, replaces deprecated DALL-E 3) ─────────────────

GPT_IMAGE_URL = "https://api.openai.com/v1/images/generations"

# ── Pricing ───────────────────────────────────────────────────────────────────

COST_PER_IMAGE = 0.09        # Gemini 3.1 Flash, 2K image
DALLE_COST_BANNER = 0.063    # gpt-image-1, 1536x1024, medium quality
DALLE_COST_SECTION = 0.042   # gpt-image-1, 1024x1024, medium quality

# ── Gemini retry settings ─────────────────────────────────────────────────────

GEMINI_RETRY_DELAYS = [30, 60, 120]  # seconds between retries on 503

# ── Shared treatment reference images ────────────────────────────────────────
# Keyword → filename in assets/image-references/treatments/
# Used as style reference for section images (therapist + client scenes).
# Add new entries here as more reference photos are added to the folder.

TREATMENT_REFERENCES_DIR = Path(__file__).parent.parent.parent / 'assets' / 'image-references' / 'treatments'

TREATMENT_REFERENCE_MAP = {
    "hair":         "hair-oiling.png",
    "oiling":       "hair-oiling.png",
    "scalp":        "hair-oiling.png",
    "foot":         "foot-massage.png",
    "reflexology":  "foot-massage.png",
    "couples":      "couples-massage.png",
    "aromatherapy": "aromatherapy.png",
    "swedish":      "swedish-massage.png",
    "thai":         "thai-massage.png",
    "deep tissue":  "thai-massage.png",
    "sports":       "thai-massage.png",
    "hot stone":    "thai-massage.png",
    "oil":          "oil-massage.jpg",
}

# ── Topic → scene description map ────────────────────────────────────────────
# "banner": foreground subject / props only — room backdrop injected separately
#           when room_description is set on ImageGenerator; otherwise self-contained
# "section": therapist + client interaction (room visible in background)

TOPIC_CONTEXT_MAP = {
    "couples": {
        "banner": "two Thai female massage therapists simultaneously performing back massage on two female clients lying side by side on treatment tables, wide shot showing both therapists and clients",
        "section": "spa therapist giving a back massage to a woman on a treatment table, second treatment table with another client visible in the background",
    },
    "deep tissue": {
        "banner": "massage therapist performing deep tissue back massage on a female client lying face-down on a treatment table, medium shot from the side showing firm pressure technique",
        "section": "close-up of massage therapist's hands applying deep tissue pressure to a client's upper back and shoulders",
    },
    "sports": {
        "banner": "sports massage therapist working on a female client's back and shoulders on a treatment table, medium shot showing the therapist using focused pressure",
        "section": "close-up of sports massage therapist's hands working on a client's calf muscles on a treatment table",
    },
    "aromatherapy": {
        "banner": "spa therapist performing aromatherapy oil back massage on a female client lying face-down on a treatment table, wide shot showing the full treatment",
        "section": "close-up of spa therapist's oiled hands applying long gliding strokes to a client's back during aromatherapy massage",
    },
    "hot stone": {
        "banner": "spa therapist carefully placing warm basalt stones along a female client's spine as she lies face-down on a treatment table, medium shot",
        "section": "close-up of dark basalt stones resting on a client's back, spa therapist's hands visible guiding a stone along the spine",
    },
    "foot": {
        "banner": "spa therapist performing Thai foot massage on a female client who is lying on a treatment table, medium shot from the side showing therapist working on the client's feet",
        "section": "wide shot of a spa treatment room, female client lying fully on a treatment table covered in white sheets, client's bare feet and lower legs extending off the foot of the table, spa therapist seated at the foot of the table with both hands working on the client's feet, both the client and therapist fully visible in frame with the client's body clearly on the table",
    },
    "facial": {
        "banner": "spa therapist performing facial massage on a female client lying face-up on a treatment table, medium shot showing therapist's hands on the client's face and décolletage",
        "section": "close-up of spa therapist's fingertips performing gentle facial massage strokes on a client's cheekbones and temples",
    },
    "hair": {
        "banner": "spa therapist massaging warm nourishing oil into a seated female client's scalp and long hair, medium shot from behind showing both therapist and client",
        "section": "close-up of spa therapist's hands working nourishing oil through a client's hair, scalp massage technique visible",
    },
    "oiling": {
        "banner": "therapist applying warm Ayurvedic oil to a seated female client's scalp, medium shot from the side showing the treatment in progress",
        "section": "close-up of therapist's oiled hands parting a client's hair and massaging warm oil into the scalp",
    },
    "scalp": {
        "banner": "therapist performing Indian head massage on a seated female client, medium shot showing the therapist's hands working through the client's hair",
        "section": "close-up of therapist performing circular scalp massage on a client's head, fingertips visible pressing into the scalp",
    },
    "reflexology": {
        "banner": "spa therapist performing reflexology on a female client's feet, client lying on a treatment table with feet elevated, medium shot showing the full scene",
        "section": "spa therapist applying reflexology to a female client's foot, client lying on treatment table with her leg extended and foot resting in the therapist's hands, therapist's thumbs pressing into the sole, client's leg and lower body visible to anchor the foot",
    },
    "swedish": {
        "banner": "spa therapist performing Swedish massage on a female client lying face-down on a treatment table, wide shot showing long flowing effleurage strokes",
        "section": "close-up of spa therapist's hands performing smooth petrissage strokes on a client's upper back and shoulders",
    },
    "head": {
        "banner": "therapist performing Indian head massage on a seated female client, medium shot from the side showing relaxed client and therapist's hands on head",
        "section": "close-up of therapist's hands performing acupressure and kneading on a client's scalp and temples",
    },
    "thai": {
        "banner": "Thai massage therapist performing traditional Thai massage on a female client lying on a floor mat, wide shot showing a full-body stretch technique",
        "section": "close-up of Thai massage therapist applying a deep assisted stretch to a client's legs on the floor mat",
    },
}

FAQ_SCENE_POOL = [
    (
        "A spa therapist neatly arranging folded white towels on a wooden treatment tray beside a row of small "
        "glass bottles of massage oil, no client in the frame, clean spa bench visible behind."
    ),
    (
        "A relaxed female client in a white spa robe seated with both feet resting in a warm floral foot bath, "
        "rose petals floating on the water, a lit candle glowing beside her, eyes closed in contentment."
    ),
    (
        "Close-up of a therapist's hands pouring warm herbal massage oil from a small ceramic vessel into an "
        "open palm, the oil catching the light as it streams, clean neutral spa background."
    ),
    (
        "A male client in a dark dressing gown reclining in a cushioned spa chair, head resting back, eyes "
        "closed, smiling softly in a calm and relaxed manner, warm ambient lighting."
    ),
    (
        "A female therapist pressing a folded hot herbal compress firmly to a male client's upper shoulder, "
        "both in a professional spa setting, mid-treatment, client eyes closed."
    ),
    (
        "A relaxed female client in a white spa robe seated in a spa chair, cradling a glass cup of herbal tea "
        "with both hands, soft natural light from a window beside her, serene expression."
    ),
]

BANNER_PHOTO_SUFFIX = (
    "Shot on Leica M11, 28mm f/2 Summicron, Kodak Portra 400 film grain, "
    "natural skylight from above, authentic location feel. "
    "Real photograph, no CGI, no illustration, no digital art."
)

SECTION_PHOTO_SUFFIX = (
    "Anatomically grounded — any visible body part must be clearly attached to a person in the scene, "
    "never floating or disembodied. "
    "Warm soft natural window light, professional spa environment, "
    "shot on Leica M11, 50mm f/2 Summicron, Kodak Portra 400 film grain, "
    "authentic location feel. Real photograph, no CGI, no illustration."
)

CLAUDE_PROMPT_SYSTEM = (
    "You write image prompts for a photorealistic AI image generator. "
    "Prompts must describe a spa or wellness treatment scene with a therapist performing the named treatment on a client. "
    "Do NOT default to a generic back massage unless the treatment literally is one. "
    "Keep the response to 1-2 sentences, no preamble, no explanation."
)


class ImageGenerator:

    def __init__(self, room_description: str = "", room_reference_image_path: str = ""):
        self.api_key = os.getenv("GOOGLE_AI_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.room_description = room_description.strip().rstrip('.')
        # Load reference image as base64 if path provided and file exists
        self.room_reference_image_b64: str = ""
        self.room_reference_image_mime: str = "image/jpeg"
        if room_reference_image_path:
            ref_path = Path(room_reference_image_path)
            if ref_path.exists():
                self.room_reference_image_b64 = base64.b64encode(ref_path.read_bytes()).decode()
                self.room_reference_image_mime = (
                    "image/png" if ref_path.suffix.lower() == ".png" else "image/jpeg"
                )
            else:
                print(f"    ⚠ Room reference image not found: {room_reference_image_path}")
        if not self.api_key:
            raise EnvironmentError("GOOGLE_AI_API_KEY not set in environment")
        self._faq_seed = 0  # set per-post in generate_for_post for deterministic scene selection

    def _get_treatment_reference(self, text: str) -> tuple[str, str]:
        """Return (base64, mime_type) for the best matching treatment reference image.

        Matches text against TREATMENT_REFERENCE_MAP keywords.
        Returns ('', '') if no match or file missing.
        """
        text_lower = text.lower()
        for keyword, filename in TREATMENT_REFERENCE_MAP.items():
            if keyword in text_lower:
                path = TREATMENT_REFERENCES_DIR / filename
                if path.exists():
                    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
                    return base64.b64encode(path.read_bytes()).decode(), mime
                break
        return "", ""

    def generate_for_post(self, html_content: str, topic: str, filepath: Path,
                          content_type: str = "blog") -> float:
        """Generate banner + section images for a post.

        Saves images alongside the HTML file and injects <img> tags into the HTML.
        Returns the total image cost in USD.
        """
        article_dir = filepath.parent
        # Strip date suffix to get a clean keyword slug, e.g. "glasgow-central-station"
        base_slug = re.sub(r'-\d{4}-\d{2}-\d{2}$', '', filepath.stem)

        self._faq_seed = sum(ord(c) for c in base_slug)
        section_headings = self._extract_section_headings(html_content)
        is_location_type = content_type == "location"

        # Look up treatment reference once — used for both banner and section images
        treat_b64, treat_mime = self._get_treatment_reference(topic)
        if treat_b64:
            print(f"    → Treatment reference: matched for \"{topic}\"")

        # Generate banner — filename includes article keywords
        # Location banners (street scenes) skip validation; treatment banners are validated.
        banner_path = article_dir / f"{base_slug}-banner.jpg"
        if is_location_type:
            banner_prompt = self._build_location_banner_prompt(topic)
            total_cost = self._generate(banner_prompt, banner_path, "banner")
        else:
            banner_prompt = self._build_banner_prompt(topic)
            total_cost = self._generate_validated(banner_prompt, banner_path, "banner", treat_b64, treat_mime)
        print(f"    → {banner_path.name}")

        section_paths = []
        for i, heading in enumerate(section_headings, 1):
            heading_lower = heading.lower()
            is_faq = "faq" in heading_lower or "frequently" in heading_lower or not heading.strip()
            if is_faq:
                heading_slug = f"{base_slug}-faq"
            else:
                heading_slug = _slugify(heading) or f"{base_slug}-section-{i}"
            section_path = article_dir / f"{heading_slug}.jpg"
            section_prompt = self._build_section_prompt(heading, i)
            # FAQ image: room reference only (client in robe — no anatomy risk, skip validation)
            # Section image: room reference + treatment reference, validated
            t_b64 = "" if is_faq else treat_b64
            t_mime = "" if is_faq else treat_mime
            if is_faq:
                total_cost += self._generate(section_prompt, section_path, "section", t_b64, t_mime)
            else:
                total_cost += self._generate_validated(section_prompt, section_path, "section", t_b64, t_mime)
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
        """Build a topic-specific banner prompt from TOPIC_CONTEXT_MAP, or Claude if no match."""
        topic_lower = topic.lower()
        for keyword, contexts in TOPIC_CONTEXT_MAP.items():
            if keyword in topic_lower:
                foreground = contexts['banner']
                return self._assemble_banner(foreground)
        print(f"    → Image prompt: Claude fallback (no map match for \"{topic}\")")
        return self._build_prompt_with_claude(topic, "banner")

    def _assemble_banner(self, foreground: str) -> str:
        """Combine treatment scene with room backdrop (if set) and photo suffix."""
        if self.room_description:
            return (
                f"Editorial spa photograph. {foreground}. "
                f"Background: {self.room_description}. "
                f"{BANNER_PHOTO_SUFFIX}"
            )
        return f"Editorial spa photograph. {foreground}. {BANNER_PHOTO_SUFFIX}"

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
        """Build a topic-specific section image prompt, or Claude if no match."""
        if section_num >= 2 or "faq" in h2_heading.lower() or "frequently" in h2_heading.lower():
            scene = FAQ_SCENE_POOL[self._faq_seed % len(FAQ_SCENE_POOL)]
            if self.room_description:
                return (
                    f"{scene} "
                    f"{self.room_description}. "
                    f"Shot on Leica M11, 50mm f/2 Summicron, Kodak Portra 400 film grain, "
                    f"natural window light from the side. Real photograph, no CGI, no illustration."
                )
            return (
                f"{scene} "
                "Shot on Leica M11, 50mm f/2 Summicron, Kodak Portra 400 film grain, "
                "natural window light from the side. Real photograph, no CGI, no illustration."
            )
        heading_lower = h2_heading.lower()
        for keyword, contexts in TOPIC_CONTEXT_MAP.items():
            if keyword in heading_lower:
                scene = contexts['section']
                if self.room_description:
                    return (
                        f"{scene}. Background: {self.room_description}. "
                        f"{SECTION_PHOTO_SUFFIX}"
                    )
                return f"{scene}. {SECTION_PHOTO_SUFFIX}"
        print(f"    → Image prompt: Claude fallback (no map match for \"{h2_heading}\")")
        return self._build_prompt_with_claude(h2_heading, "section")

    def _build_prompt_with_claude(self, topic: str, image_type: str) -> str:
        """Ask Claude Haiku to generate a topic-specific image prompt.

        Called only when no keyword in BANNER_ACTION_MAP / TOPIC_CONTEXT_MAP matches.
        Cost: ~$0.001 per call.
        """
        if not self.anthropic_api_key:
            suffix = BANNER_PHOTO_SUFFIX if image_type == "banner" else SECTION_PHOTO_SUFFIX
            return f"Professional spa treatment room, white treatment table, warm natural lighting. {suffix}"

        if image_type == "banner":
            user_msg = (
                f"Write 1-2 sentences describing a therapist performing '{topic}' on a client "
                f"for a wide banner image on a spa page. Medium or wide shot. "
                "Be specific to this treatment — do not default to a back massage."
            )
        else:
            user_msg = (
                f"Write 1-2 sentences describing a therapist performing '{topic}' on a client. "
                "Foreground action only — no room or background details. "
                "Be specific — do not default to a back massage unless this treatment literally is one."
            )

        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 120,
                    "system": CLAUDE_PROMPT_SYSTEM,
                    "messages": [{"role": "user", "content": user_msg}],
                },
                timeout=20,
            )
            if r.status_code == 200:
                foreground = r.json()["content"][0]["text"].strip()
                if image_type == "banner":
                    return self._assemble_banner(foreground)
                # Section: append room if available
                if self.room_description:
                    return (
                        f"{foreground}. {self.room_description} visible in the background. "
                        f"{SECTION_PHOTO_SUFFIX}"
                    )
                return f"{foreground}. {SECTION_PHOTO_SUFFIX}"
        except Exception:
            pass

        # Last resort
        suffix = BANNER_PHOTO_SUFFIX if image_type == "banner" else SECTION_PHOTO_SUFFIX
        return f"Professional spa treatment room, white treatment table, warm natural lighting. {suffix}"

    def _generate(self, prompt: str, output_path: Path, image_type: str,
                  treatment_ref_b64: str = "", treatment_ref_mime: str = "") -> float:
        """Try Gemini with retries on 503, fall back to gpt-image-1. Returns image cost."""
        last_err = None
        for attempt, delay in enumerate(GEMINI_RETRY_DELAYS):
            try:
                self._generate_gemini(prompt, output_path, image_type,
                                      treatment_ref_b64, treatment_ref_mime)
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
                f"Gemini failed ({last_err}) and OPENAI_API_KEY not set for gpt-image-1 fallback"
            )
        print(f"    → gpt-image-1 fallback...")
        self._generate_dalle(prompt, output_path, image_type)
        return DALLE_COST_BANNER if image_type == "banner" else DALLE_COST_SECTION

    def _generate_gemini(self, prompt: str, output_path: Path, image_type: str,
                         treatment_ref_b64: str = "", treatment_ref_mime: str = "") -> Path:
        """Call Gemini API, decode base64 response, save and crop the image."""
        if image_type == "banner":
            aspect_ratio = "21:9"
            image_size = "2K"
            crop_target = (1200, 500)
        else:
            aspect_ratio = "4:3"
            image_size = "1K"
            crop_target = (400, 300)

        # Build parts list:
        #   1. Room reference image (if set) — establishes the location
        #   2. Treatment reference image (if set) — shows the correct treatment style
        #   3. Text prompt — describes the specific foreground subject
        parts = []
        text_prefix = ""

        if self.room_reference_image_b64:
            parts.append({
                "inline_data": {
                    "mime_type": self.room_reference_image_mime,
                    "data": self.room_reference_image_b64,
                }
            })
            text_prefix = "Using the room in the first reference image as the setting"

        if treatment_ref_b64:
            parts.append({
                "inline_data": {
                    "mime_type": treatment_ref_mime,
                    "data": treatment_ref_b64,
                }
            })
            if text_prefix:
                text_prefix += ", and the treatment style in the second reference image as inspiration"
            else:
                text_prefix = "Using the treatment style in the reference image as inspiration"

        if text_prefix:
            parts.append({"text": f"{text_prefix}: {prompt}"})
        else:
            parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": parts}],
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
        """Call gpt-image-1 API, decode base64 response, save and crop.

        gpt-image-1 differences from DALL-E 3:
        - Always returns base64 (no response_format=url support)
        - Max landscape size is 1536x1024 (was 1792x1024)
        - Quality values: low/medium/high (was standard/hd)
        """
        size = "1536x1024" if image_type == "banner" else "1024x1024"
        crop_target = (1200, 500) if image_type == "banner" else (400, 300)

        response = requests.post(
            GPT_IMAGE_URL,
            headers={
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-image-1",
                "prompt": prompt,
                "size": size,
                "quality": "medium",
                "n": 1,
            },
            timeout=90,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"gpt-image-1 API error {response.status_code}: {response.text[:300]}"
            )

        img_bytes = base64.b64decode(response.json()["data"][0]["b64_json"])
        output_path.write_bytes(img_bytes)
        self._crop_image(output_path, crop_target)
        return output_path

    def _validate_image(self, image_path: Path, image_type: str) -> tuple[bool, str]:
        """Check a generated image for anatomical issues using Claude Haiku vision.

        Returns (is_valid, reason). On any API error returns (True, '') so a
        validation failure never blocks publishing.
        """
        if not self.anthropic_api_key:
            return True, ""
        try:
            img_b64 = base64.b64encode(image_path.read_bytes()).decode()
            mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
            if image_type == "banner":
                question = (
                    "Does this spa treatment image show a therapist performing a treatment on a client? "
                    "Are there any anatomically incorrect or disembodied body parts "
                    "(e.g. a hand or foot with no visible body attached)? "
                    "Reply VALID if it looks correct, or ISSUE: [brief reason] if not."
                )
            else:
                question = (
                    "Are all visible body parts in this spa treatment image anatomically grounded — "
                    "clearly attached to a person, not floating or disembodied? "
                    "Reply VALID if correct, or ISSUE: [brief reason] if there are floating limbs."
                )
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 80,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": img_b64}},
                            {"type": "text", "text": question},
                        ],
                    }],
                },
                timeout=20,
            )
            if r.status_code == 200:
                reply = r.json()["content"][0]["text"].strip()
                if reply.upper().startswith("ISSUE"):
                    return False, reply
        except Exception:
            pass
        return True, ""

    def _generate_validated(self, prompt: str, output_path: Path, image_type: str,
                            treatment_ref_b64: str = "", treatment_ref_mime: str = "") -> float:
        """Generate an image and validate it for anatomical correctness.

        On validation failure: regenerates once. If the retry also fails,
        logs a warning and returns the image anyway — never blocks publishing.
        Returns total cost in USD.
        """
        cost = self._generate(prompt, output_path, image_type, treatment_ref_b64, treatment_ref_mime)
        valid, reason = self._validate_image(output_path, image_type)
        if not valid:
            print(f"    ⚠ Validation: {reason} — regenerating...")
            cost += self._generate(prompt, output_path, image_type, treatment_ref_b64, treatment_ref_mime)
            valid2, reason2 = self._validate_image(output_path, image_type)
            if not valid2:
                print(f"    ⚠ Retry also flagged ({reason2}) — using image anyway")
            else:
                print(f"    ✓ Retry passed validation")
        return cost

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
