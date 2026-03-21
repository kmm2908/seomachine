#!/usr/bin/env python3
"""
Image Generation Test Script
Tests DALL-E 3, GPT-image-1, Gemini Flash/Pro, Stability AI, Ideogram
against GTM-specific prompts to evaluate quality before full pipeline integration.

Usage:
    python3 test_image_generation.py                         # run all available models
    python3 test_image_generation.py --model dalle3          # DALL-E 3
    python3 test_image_generation.py --model gpt-image-1    # GPT-image-1 (OpenAI newest)
    python3 test_image_generation.py --model gemini-flash    # Gemini 3.1 Flash Image Preview
    python3 test_image_generation.py --model gemini-pro      # Gemini 3 Pro Image Preview
    python3 test_image_generation.py --topic "deep tissue massage Glasgow"
"""

import os
import sys
import argparse
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Output directory ────────────────────────────────────────────────────────

OUTPUT_DIR = Path("test_images")
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── Test prompts ─────────────────────────────────────────────────────────────

BANNER_PROMPT_TEMPLATE = (
    "Thai massage studio interior, {topic_context}, "
    "warm amber lighting, Thai silk cushions, wooden accents, orchid decorations, "
    "shot on Canon EOS R5, 24mm wide lens, f/4, natural light, ultra-detailed, "
    "8K resolution, hyperrealistic DSLR photography, no illustration, no art style"
)

SECTION_PROMPT_TEMPLATE = (
    "{topic_context}, "
    "warm soft natural window light, professional spa environment, "
    "shot on Sony A7R IV, 50mm lens, f/2.8 shallow depth of field, "
    "ultra-detailed, 8K, hyperrealistic DSLR photography, no illustration, no art style"
)

# Maps topic keywords to scene descriptions for the prompts
TOPIC_CONTEXT_MAP = {
    "couples": {
        "banner": "two side-by-side massage tables with white linen, rose petals, candlelit luxury spa room, no people",
        "section": "spa therapist giving a back massage to a woman on a treatment table, second treatment table visible in background, luxury spa room, warm light",
    },
    "deep tissue": {
        "banner": "professional massage studio with white treatment table, therapeutic spa setting, no people",
        "section": "massage therapist performing back massage on a client lying on a treatment table, professional studio lighting",
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
}

def build_topic_context(topic: str, image_type: str = "section") -> str:
    """Return the appropriate scene description for the given topic and image type."""
    topic_lower = topic.lower()
    for keyword, contexts in TOPIC_CONTEXT_MAP.items():
        if keyword in topic_lower:
            return contexts.get(image_type, contexts["section"])
    # Generic fallback
    if image_type == "banner":
        return "professional Thai massage studio interior, warm Thai decor, treatment table, orchids, no people"
    return "massage therapist working on a client lying on a treatment table, professional Thai spa setting"

DEFAULT_TOPICS = [
    "Thai massage Glasgow city centre",
    "deep tissue massage for back pain relief",
    "couples massage relaxation treatment",
]

# ─── DALL-E (OpenAI) ──────────────────────────────────────────────────────────

def generate_dalle(topic: str, image_type: str, model: str = "dall-e-3") -> Path | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  ✗ OPENAI_API_KEY not set — skipping")
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except ImportError:
        print("  ✗ openai not installed — run: pip install openai")
        return None

    topic_context = build_topic_context(topic, image_type)
    if image_type == "banner":
        prompt = BANNER_PROMPT_TEMPLATE.format(topic_context=topic_context)
        # DALL-E 3: 1792x1024 is the widest available; we'll crop to 1200x500
        size = "1792x1024" if model == "dall-e-3" else "1024x1024"
    else:
        prompt = SECTION_PROMPT_TEMPLATE.format(topic_context=topic_context)
        size = "1024x1024"  # will crop to 400x300

    print(f"  Generating with {model} ({size})...")
    t0 = time.time()
    try:
        response = client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            quality="standard",
            n=1,
        )
        elapsed = time.time() - t0
        image_url = response.data[0].url

        # Download and save
        slug = topic.lower().replace(" ", "-")[:40]
        filename = OUTPUT_DIR / f"{model}-{image_type}-{slug}.png"
        img_data = requests.get(image_url, timeout=30).content
        filename.write_bytes(img_data)

        # Crop to target dimensions
        target = (1200, 500) if image_type == "banner" else (400, 300)
        crop_image(filename, target)

        print(f"  ✓ Saved: {filename} ({elapsed:.1f}s)")
        return filename

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


# ─── Stability AI ─────────────────────────────────────────────────────────────

def generate_stability(topic: str, image_type: str) -> Path | None:
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key:
        print("  ✗ STABILITY_API_KEY not set — skipping")
        return None

    topic_context = build_topic_context(topic, image_type)
    if image_type == "banner":
        prompt = BANNER_PROMPT_TEMPLATE.format(topic_context=topic_context)
        width, height = 1216, 512  # closest to 1200x500 in SD3 supported sizes
    else:
        prompt = SECTION_PROMPT_TEMPLATE.format(topic_context=topic_context)
        width, height = 400, 304  # closest to 400x300

    print(f"  Generating with Stable Diffusion 3.5 ({width}x{height})...")
    t0 = time.time()
    try:
        response = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/sd3",
            headers={
                "authorization": f"Bearer {api_key}",
                "accept": "image/*",
            },
            files={"none": ""},
            data={
                "prompt": prompt,
                "model": "sd3.5-large",
                "aspect_ratio": "21:9" if image_type == "banner" else "4:3",
                "output_format": "jpeg",
            },
            timeout=60,
        )
        elapsed = time.time() - t0

        if response.status_code == 200:
            slug = topic.lower().replace(" ", "-")[:40]
            filename = OUTPUT_DIR / f"sd35-{image_type}-{slug}.jpg"
            filename.write_bytes(response.content)
            target = (1200, 500) if image_type == "banner" else (400, 300)
            crop_image(filename, target)
            print(f"  ✓ Saved: {filename} ({elapsed:.1f}s)")
            return filename
        else:
            print(f"  ✗ API error {response.status_code}: {response.text[:200]}")
            return None

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


# ─── GPT-image-1 (OpenAI newest) ──────────────────────────────────────────────

def generate_gpt_image1(topic: str, image_type: str) -> Path | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  ✗ OPENAI_API_KEY not set — skipping")
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except ImportError:
        print("  ✗ openai not installed — run: pip install openai")
        return None

    topic_context = build_topic_context(topic, image_type)
    if image_type == "banner":
        prompt = BANNER_PROMPT_TEMPLATE.format(topic_context=topic_context)
        size = "1536x1024"  # widest available for gpt-image-1; crop to 1200x500
    else:
        prompt = SECTION_PROMPT_TEMPLATE.format(topic_context=topic_context)
        size = "1024x1024"

    print(f"  Generating with gpt-image-1 ({size})...")
    t0 = time.time()
    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size=size,
            quality="high",
            n=1,
        )
        elapsed = time.time() - t0
        item = response.data[0]
        slug = topic.lower().replace(" ", "-")[:40]
        filename = OUTPUT_DIR / f"gpt-image1-{image_type}-{slug}.png"

        if item.url:
            img_data = requests.get(item.url, timeout=30).content
        else:
            import base64
            img_data = base64.b64decode(item.b64_json)
        filename.write_bytes(img_data)

        target = (1200, 500) if image_type == "banner" else (400, 300)
        crop_image(filename, target)

        print(f"  ✓ Saved: {filename} ({elapsed:.1f}s)")
        return filename

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


# ─── Gemini (Google AI Studio) ────────────────────────────────────────────────

def generate_gemini(topic: str, image_type: str, model: str = "gemini-3.1-flash-image-preview") -> Path | None:
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        print("  ✗ GOOGLE_AI_API_KEY not set — skipping")
        return None

    topic_context = build_topic_context(topic, image_type)
    if image_type == "banner":
        prompt = BANNER_PROMPT_TEMPLATE.format(topic_context=topic_context)
        aspect_ratio = "21:9"
        image_size = "2K"
    else:
        prompt = SECTION_PROMPT_TEMPLATE.format(topic_context=topic_context)
        aspect_ratio = "4:3"
        image_size = "1K"

    model_short = "gemini-flash" if "flash" in model else "gemini-pro"
    print(f"  Generating with {model} ({aspect_ratio}, {image_size})...")
    t0 = time.time()
    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
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
        response = requests.post(url, json=payload, timeout=60)
        elapsed = time.time() - t0

        if response.status_code != 200:
            print(f"  ✗ API error {response.status_code}: {response.text[:200]}")
            return None

        data = response.json()
        parts = data["candidates"][0]["content"]["parts"]
        image_part = next((p for p in parts if "inlineData" in p), None)
        if not image_part:
            print(f"  ✗ No image in response: {str(data)[:200]}")
            return None

        import base64
        img_bytes = base64.b64decode(image_part["inlineData"]["data"])
        slug = topic.lower().replace(" ", "-")[:40]
        filename = OUTPUT_DIR / f"{model_short}-{image_type}-{slug}.png"
        filename.write_bytes(img_bytes)

        target = (1200, 500) if image_type == "banner" else (400, 300)
        crop_image(filename, target)

        print(f"  ✓ Saved: {filename} ({elapsed:.1f}s)")
        return filename

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


# ─── Ideogram ─────────────────────────────────────────────────────────────────

def generate_ideogram(topic: str, image_type: str) -> Path | None:
    api_key = os.getenv("IDEOGRAM_API_KEY")
    if not api_key:
        print("  ✗ IDEOGRAM_API_KEY not set — skipping")
        return None

    topic_context = build_topic_context(topic, image_type)
    if image_type == "banner":
        prompt = BANNER_PROMPT_TEMPLATE.format(topic_context=topic_context)
        aspect = "ASPECT_16_9"  # 1344x756 — closest wide banner available
    else:
        prompt = SECTION_PROMPT_TEMPLATE.format(topic_context=topic_context)
        aspect = "ASPECT_4_3"  # 1280x960

    print(f"  Generating with Ideogram 2.0 ({aspect})...")
    t0 = time.time()
    try:
        response = requests.post(
            "https://api.ideogram.ai/generate",
            headers={
                "Api-Key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "image_request": {
                    "prompt": prompt,
                    "model": "V_2",
                    "aspect_ratio": aspect,
                    "magic_prompt_option": "OFF",
                }
            },
            timeout=60,
        )
        elapsed = time.time() - t0

        if response.status_code == 200:
            data = response.json()
            image_url = data["data"][0]["url"]
            slug = topic.lower().replace(" ", "-")[:40]
            filename = OUTPUT_DIR / f"ideogram-{image_type}-{slug}.jpg"
            img_data = requests.get(image_url, timeout=30).content
            filename.write_bytes(img_data)
            target = (1200, 500) if image_type == "banner" else (400, 300)
            crop_image(filename, target)
            print(f"  ✓ Saved: {filename} ({elapsed:.1f}s)")
            return filename
        else:
            print(f"  ✗ API error {response.status_code}: {response.text[:200]}")
            return None

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


# ─── Image crop/resize utility ────────────────────────────────────────────────

def crop_image(path: Path, target: tuple[int, int]) -> None:
    """Centre-crop an image to target (width, height) using Pillow."""
    try:
        from PIL import Image
        with Image.open(path) as img:
            w, h = img.size
            tw, th = target
            # Scale down to fit target width, then crop height
            scale = tw / w
            new_h = int(h * scale)
            img = img.resize((tw, new_h), Image.LANCZOS)
            if new_h > th:
                top = (new_h - th) // 2
                img = img.crop((0, top, tw, top + th))
            img.save(path, quality=92, optimize=True)
    except ImportError:
        print("  ⚠ Pillow not installed — images saved at original size (pip install Pillow)")
    except Exception as e:
        print(f"  ⚠ Crop failed: {e}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Test image generation APIs")
    parser.add_argument("--model",
                        choices=["dalle3", "dalle2", "gpt-image-1", "gemini-flash", "gemini-pro",
                                 "stability", "ideogram", "all"],
                        default="all", help="Which model to test")
    parser.add_argument("--topic", default=None, help="Custom topic (overrides default test topics)")
    parser.add_argument("--type", choices=["banner", "section", "both"], default="banner",
                        dest="image_type", help="Image type to generate")
    args = parser.parse_args()

    topics = [args.topic] if args.topic else DEFAULT_TOPICS
    types = ["banner", "section"] if args.image_type == "both" else [args.image_type]

    print(f"\nImage Generation Test")
    print(f"Output directory: {OUTPUT_DIR.resolve()}")
    print(f"Topics: {topics}")
    print(f"Types: {types}")
    print("─" * 60)

    for topic in topics:
        print(f"\nTopic: \"{topic}\"")
        for image_type in types:
            print(f"\n  [{image_type.upper()}]")

            if args.model in ("dalle3", "all"):
                print("  → DALL-E 3")
                generate_dalle(topic, image_type, model="dall-e-3")

            if args.model in ("dalle2", "all"):
                print("  → DALL-E 2")
                generate_dalle(topic, image_type, model="dall-e-2")

            if args.model in ("gpt-image-1", "all"):
                print("  → GPT-image-1")
                generate_gpt_image1(topic, image_type)

            if args.model in ("gemini-flash", "all"):
                print("  → Gemini 3.1 Flash Image Preview")
                generate_gemini(topic, image_type, model="gemini-3.1-flash-image-preview")

            if args.model in ("gemini-pro", "all"):
                print("  → Gemini 3 Pro Image Preview")
                generate_gemini(topic, image_type, model="gemini-3-pro-image-preview")

            if args.model in ("stability", "all"):
                print("  → Stable Diffusion 3.5")
                generate_stability(topic, image_type)

            if args.model in ("ideogram", "all"):
                print("  → Ideogram 2.0")
                generate_ideogram(topic, image_type)

    print(f"\n{'─' * 60}")
    print(f"Done. Check {OUTPUT_DIR.resolve()} to compare results.")
    print("Pick your preferred model, then set IMAGE_API_PROVIDER in .env")


if __name__ == "__main__":
    main()
