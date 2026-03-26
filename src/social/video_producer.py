"""Video producer: composes long-form videos and shorts using FFmpeg.

Takes a video script JSON, TTS audio (ElevenLabs), and article images,
then produces MP4 videos with Ken Burns effects, captions, and thumbnails.
"""
import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))
load_dotenv(ROOT / '.env')

from elevenlabs_tts import ElevenLabsTTS

LONGFORM_RES = (1920, 1080)
SHORT_RES = (1080, 1920)
FPS = 30
THUMBNAIL_RES = (1280, 720)
SLIDE_BG_COLOR = (25, 25, 35)
SLIDE_TEXT_COLOR = (255, 255, 255)
SLIDE_ACCENT_COLOR = (78, 172, 135)
SLIDE_SUBTITLE_COLOR = (180, 180, 200)
KB_DIRECTIONS = ['zoom_in', 'zoom_out', 'pan_left', 'pan_right']


def build_ken_burns_filter(duration_secs: float, direction: str, fps: int = FPS) -> str:
    """Return an FFmpeg zoompan filter string for Ken Burns effect.

    Args:
        duration_secs: Duration of the effect in seconds.
        direction: One of 'zoom_in', 'zoom_out', 'pan_left', 'pan_right'.
        fps: Frames per second (default 30).

    Returns:
        FFmpeg filter_complex string with zoompan.
    """
    total_frames = int(duration_secs * fps)
    w, h = LONGFORM_RES

    if direction == 'zoom_in':
        return (
            f"zoompan=z='min(zoom+0.001,1.3)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={w}x{h}:fps={fps}"
        )
    elif direction == 'zoom_out':
        return (
            f"zoompan=z='if(eq(on,1),1.3,max(zoom-0.001,1.0))':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={w}x{h}:fps={fps}"
        )
    elif direction == 'pan_left':
        return (
            f"zoompan=z='1.1':"
            f"x='iw/2-(iw/zoom/2)+on*{w}/(zoom*{total_frames})':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={w}x{h}:fps={fps}"
        )
    elif direction == 'pan_right':
        return (
            f"zoompan=z='1.1':"
            f"x='iw/2-(iw/zoom/2)-on*{w}/(zoom*{total_frames})':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={w}x{h}:fps={fps}"
        )
    else:
        return (
            f"zoompan=z='min(zoom+0.001,1.3)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={w}x{h}:fps={fps}"
        )


def generate_srt(alignment: dict, words_per_group: int = 3) -> str:
    """Generate SRT subtitle content from ElevenLabs character-level alignment.

    Args:
        alignment: Dict with 'characters', 'character_start_times_seconds',
                   'character_end_times_seconds'.
        words_per_group: Number of words per subtitle block.

    Returns:
        SRT formatted string.
    """
    characters = alignment.get('characters', [])
    starts = alignment.get('character_start_times_seconds', [])
    ends = alignment.get('character_end_times_seconds', [])

    # Reconstruct words with their start/end times
    words = []
    current_word = []
    word_start = None
    word_end = None

    for i, char in enumerate(characters):
        if char == ' ':
            if current_word:
                words.append((''.join(current_word), word_start, word_end))
                current_word = []
                word_start = None
        else:
            if word_start is None:
                word_start = starts[i] if i < len(starts) else 0.0
            word_end = ends[i] if i < len(ends) else 0.0
            current_word.append(char)

    if current_word:
        words.append((''.join(current_word), word_start, word_end))

    # Group words into subtitle blocks
    lines = []
    index = 1
    for i in range(0, len(words), words_per_group):
        group = words[i:i + words_per_group]
        if not group:
            continue
        text = ' '.join(w[0] for w in group)
        start_sec = group[0][1] or 0.0
        end_sec = group[-1][2] or 0.0

        lines.append(str(index))
        lines.append(f"{_format_srt_time(start_sec)} --> {_format_srt_time(end_sec)}")
        lines.append(text)
        lines.append('')
        index += 1

    return '\n'.join(lines)


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp HH:MM:SS,mmm."""
    ms = int((seconds % 1) * 1000)
    total_secs = int(seconds)
    secs = total_secs % 60
    mins = (total_secs // 60) % 60
    hours = total_secs // 3600
    return f"{hours:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Load a TrueType font, falling back to default if not found."""
    try:
        return ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', size)
    except (IOError, OSError):
        return ImageFont.load_default()


class VideoProducer:
    """Produces long-form MP4 videos and shorts from article content."""

    def __init__(self, voice_id: str, elevenlabs_api_key: str | None = None):
        self.voice_id = voice_id
        self._tts = ElevenLabsTTS(api_key=elevenlabs_api_key)

    def produce(
        self,
        script: dict,
        article_dir: Path,
        video_dir: Path,
        logo_url: str | None = None,
    ) -> tuple[dict, float]:
        """Orchestrate the full video production pipeline.

        Args:
            script: Video script JSON from social_post_generator.
            article_dir: Directory containing article HTML and images.
            video_dir: Output directory for produced videos.
            logo_url: Optional URL to a logo image for thumbnails.

        Returns:
            Tuple of (result_dict, total_cost_usd).
        """
        article_dir = Path(article_dir)
        video_dir = Path(video_dir)
        video_dir.mkdir(parents=True, exist_ok=True)

        total_cost = 0.0
        slug = script.get('slug', 'video')
        longform = script.get('long_form_video', {})
        shorts_list = script.get('shorts', [])

        print(f"  → Video: producing '{slug}'")

        # Step 1: Concatenate all scene narrations for TTS
        scenes = longform.get('scenes', [])
        full_narration = ' '.join(
            s.get('narration', '') for s in scenes if s.get('narration')
        )
        audio_path = video_dir / f"{slug}-narration.mp3"
        srt_path = video_dir / f"{slug}.srt"

        if full_narration:
            print(f"  → TTS: generating narration ({len(full_narration)} chars)")
            audio_path, tts_cost, alignment = self._tts.generate_with_timestamps(
                text=full_narration,
                voice_id=self.voice_id,
                output_path=audio_path,
            )
            total_cost += tts_cost

            # Step 2: Generate SRT captions
            if alignment:
                srt_content = generate_srt(alignment, words_per_group=3)
                srt_path.write_text(srt_content, encoding='utf-8')
                print(f"  → Captions: {srt_path.name}")
        else:
            alignment = None

        # Step 3: Generate scene visuals
        clip_paths = []
        banner_path = self._find_banner(article_dir)

        for i, scene in enumerate(scenes):
            direction = KB_DIRECTIONS[i % len(KB_DIRECTIONS)]
            clip_out = video_dir / f"{slug}-scene-{i:02d}.mp4"
            duration = self._parse_duration(scene.get('duration', '10s'))
            scene_type = scene.get('type', 'slide')

            print(f"  → Scene {i + 1}/{len(scenes)}: {scene_type} ({direction})")

            if scene_type == 'ken_burns' and banner_path:
                self._render_ken_burns_scene(
                    source_image=banner_path,
                    output_path=clip_out,
                    duration=duration,
                    direction=direction,
                    text_overlay=scene.get('text_overlay'),
                )
            elif scene_type == 'text_overlay':
                self._render_text_overlay_scene(scene, clip_out, duration)
            else:
                self._render_slide_scene(scene, clip_out, duration)

            if clip_out.exists():
                clip_paths.append(clip_out)

        # Step 4: Concatenate scenes + audio → long-form MP4
        longform_out = video_dir / f"{slug}-longform.mp4"
        if clip_paths and audio_path.exists():
            print(f"  → Concat: {len(clip_paths)} scenes + audio")
            self._concat_with_audio(clip_paths, audio_path, longform_out)

        # Step 5: Generate thumbnail
        thumbnail_out = video_dir / f"{slug}-thumbnail.jpg"
        title_text = longform.get('title', slug.replace('-', ' ').title())
        if banner_path:
            self._generate_thumbnail(
                title_text=title_text,
                banner_path=banner_path,
                output_path=thumbnail_out,
                logo_url=logo_url,
            )

        # Step 6: Generate shorts
        shorts_dir = video_dir / 'shorts'
        shorts_dir.mkdir(exist_ok=True)
        shorts_results = []
        for short in shorts_list:
            short_result = self._produce_short(short, shorts_dir, slug, article_dir)
            if short_result:
                shorts_results.append(short_result)
                total_cost += short_result.get('cost', 0.0)

        result = {
            'slug': slug,
            'longform': str(longform_out) if longform_out.exists() else None,
            'thumbnail': str(thumbnail_out) if thumbnail_out.exists() else None,
            'srt': str(srt_path) if srt_path.exists() else None,
            'shorts': shorts_results,
        }

        print(f"  → Video: done (cost ${total_cost:.4f})")
        return result, total_cost

    def _generate_slide(
        self,
        text: str,
        subtitle: str | None,
        output_path: Path,
        resolution: tuple[int, int] = LONGFORM_RES,
    ) -> None:
        """Generate a slide image with centered text and optional subtitle.

        Args:
            text: Main heading text.
            subtitle: Optional smaller subtitle text.
            output_path: Where to save the JPEG.
            resolution: (width, height) tuple.
        """
        w, h = resolution
        img = Image.new('RGB', (w, h), color=SLIDE_BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Accent bar — horizontal line near bottom third
        bar_y = int(h * 0.58)
        bar_height = 6
        bar_margin = int(w * 0.1)
        draw.rectangle(
            [(bar_margin, bar_y), (w - bar_margin, bar_y + bar_height)],
            fill=SLIDE_ACCENT_COLOR,
        )

        # Main text — centered vertically above accent bar
        font_size = max(48, int(h * 0.07))
        font = _load_font(font_size)

        # Wrap text if too wide
        max_width = int(w * 0.8)
        wrapped = _wrap_text(draw, text, font, max_width)

        total_text_h = sum(
            draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1]
            for line in wrapped
        ) + (len(wrapped) - 1) * 10

        text_y = bar_y - total_text_h - int(h * 0.06)
        for line in wrapped:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            line_h = bbox[3] - bbox[1]
            draw.text(
                ((w - line_w) // 2, text_y),
                line,
                font=font,
                fill=SLIDE_TEXT_COLOR,
            )
            text_y += line_h + 10

        # Subtitle text
        if subtitle:
            sub_font_size = max(28, int(h * 0.038))
            sub_font = _load_font(sub_font_size)
            sub_wrapped = _wrap_text(draw, subtitle, sub_font, max_width)
            sub_y = bar_y + bar_height + int(h * 0.04)
            for line in sub_wrapped:
                bbox = draw.textbbox((0, 0), line, font=sub_font)
                line_w = bbox[2] - bbox[0]
                line_h = bbox[3] - bbox[1]
                draw.text(
                    ((w - line_w) // 2, sub_y),
                    line,
                    font=sub_font,
                    fill=SLIDE_SUBTITLE_COLOR,
                )
                sub_y += line_h + 6

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), 'JPEG', quality=92)

    def _generate_thumbnail(
        self,
        title_text: str,
        banner_path: Path,
        output_path: Path,
        logo_url: str | None = None,
    ) -> None:
        """Generate a 1280x720 YouTube thumbnail.

        Darkens the banner image and overlays bold title text.

        Args:
            title_text: Title to display on the thumbnail.
            banner_path: Path to the source banner image.
            output_path: Where to save the JPEG.
            logo_url: Optional logo URL (not implemented; reserved for future use).
        """
        w, h = THUMBNAIL_RES
        banner = Image.open(banner_path).convert('RGB').resize((w, h), Image.LANCZOS)

        # Darken by blending with black
        dark_overlay = Image.new('RGB', (w, h), (0, 0, 0))
        thumb = Image.blend(banner, dark_overlay, alpha=0.5)

        draw = ImageDraw.Draw(thumb)

        font_size = max(60, int(h * 0.12))
        font = _load_font(font_size)

        max_width = int(w * 0.85)
        wrapped = _wrap_text(draw, title_text, font, max_width)

        total_h = sum(
            draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1]
            for line in wrapped
        ) + (len(wrapped) - 1) * 12

        text_y = (h - total_h) // 2
        for line in wrapped:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            line_h = bbox[3] - bbox[1]
            # Drop shadow
            draw.text(((w - line_w) // 2 + 3, text_y + 3), line, font=font, fill=(0, 0, 0, 180))
            draw.text(((w - line_w) // 2, text_y), line, font=font, fill=SLIDE_TEXT_COLOR)
            text_y += line_h + 12

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        thumb.save(str(output_path), 'JPEG', quality=92)

    def _render_slide_scene(self, scene: dict, output_path: Path, duration: float) -> None:
        """Render a static slide as an MP4 clip.

        Args:
            scene: Scene dict with 'text' and optionally 'subtitle'.
            output_path: Output MP4 path.
            duration: Duration in seconds.
        """
        with tempfile.TemporaryDirectory() as tmp:
            slide_path = Path(tmp) / 'slide.jpg'
            self._generate_slide(
                text=scene.get('text', ''),
                subtitle=scene.get('subtitle'),
                output_path=slide_path,
                resolution=LONGFORM_RES,
            )
            subprocess.run(
                [
                    'ffmpeg', '-y',
                    '-loop', '1',
                    '-i', str(slide_path),
                    '-t', str(duration),
                    '-vf', f'fps={FPS},format=yuv420p',
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    str(output_path),
                ],
                capture_output=True,
                check=True,
            )

    def _render_ken_burns_scene(
        self,
        source_image: Path,
        output_path: Path,
        duration: float,
        direction: str,
        text_overlay: str | None = None,
    ) -> None:
        """Render an image with Ken Burns (zoompan) effect as MP4.

        Args:
            source_image: Source image path.
            output_path: Output MP4 path.
            duration: Duration in seconds.
            direction: Ken Burns direction (zoom_in/zoom_out/pan_left/pan_right).
            text_overlay: Optional text to overlay.
        """
        kb_filter = build_ken_burns_filter(duration, direction, FPS)
        filters = f"{kb_filter},format=yuv420p"

        if text_overlay:
            safe_text = text_overlay.replace("'", "\\'").replace(':', '\\:')
            font_size = 52
            filters += (
                f",drawtext=text='{safe_text}':fontsize={font_size}:"
                f"fontcolor=white:x=(w-text_w)/2:y=h-th-60:"
                f"shadowcolor=black:shadowx=2:shadowy=2"
            )

        subprocess.run(
            [
                'ffmpeg', '-y',
                '-i', str(source_image),
                '-vf', filters,
                '-t', str(duration),
                '-c:v', 'libx264',
                '-preset', 'fast',
                str(output_path),
            ],
            capture_output=True,
            check=True,
        )

    def _render_text_overlay_scene(self, scene: dict, output_path: Path, duration: float) -> None:
        """Render a text overlay scene (delegates to slide for now).

        Args:
            scene: Scene dict.
            output_path: Output MP4 path.
            duration: Duration in seconds.
        """
        self._render_slide_scene(scene, output_path, duration)

    def _concat_with_audio(
        self,
        clips: list[Path],
        audio_path: Path,
        output_path: Path,
    ) -> None:
        """Concatenate video clips and mix with audio using FFmpeg concat demuxer.

        Args:
            clips: List of clip MP4 paths.
            audio_path: Audio file path (MP3).
            output_path: Final MP4 output path.
        """
        with tempfile.TemporaryDirectory() as tmp:
            concat_list = Path(tmp) / 'concat.txt'
            lines = [f"file '{str(c.resolve())}'\n" for c in clips]
            concat_list.write_text(''.join(lines), encoding='utf-8')

            subprocess.run(
                [
                    'ffmpeg', '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(concat_list),
                    '-i', str(audio_path),
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-shortest',
                    str(output_path),
                ],
                capture_output=True,
                check=True,
            )

    def _produce_short(
        self,
        short: dict,
        shorts_dir: Path,
        slug: str,
        article_dir: Path,
    ) -> dict | None:
        """Produce a single short video with TTS + slide.

        Args:
            short: Short dict with 'title', 'hook', 'script', 'duration'.
            shorts_dir: Directory to save the short.
            slug: Base slug for filenames.
            article_dir: Article directory (for banner image).

        Returns:
            Dict with short result info or None on failure.
        """
        short_title = short.get('title', 'short')
        short_slug = short_title.lower().replace(' ', '-')[:40]
        narration = short.get('script', short.get('hook', ''))
        if not narration:
            return None

        cost = 0.0
        audio_out = shorts_dir / f"{slug}-{short_slug}.mp3"
        slide_out = shorts_dir / f"{slug}-{short_slug}-slide.jpg"
        video_out = shorts_dir / f"{slug}-{short_slug}.mp4"

        print(f"  → Short: '{short_title}'")

        try:
            audio_path, tts_cost = self._tts.generate(
                text=narration,
                voice_id=self.voice_id,
                output_path=audio_out,
            )
            cost += tts_cost

            self._generate_slide(
                text=short.get('hook', short_title),
                subtitle=short.get('title'),
                output_path=slide_out,
                resolution=SHORT_RES,
            )

            duration = self._get_audio_duration(audio_path) if audio_path.exists() else \
                self._parse_duration(short.get('duration', '30s'))

            subprocess.run(
                [
                    'ffmpeg', '-y',
                    '-loop', '1',
                    '-i', str(slide_out),
                    '-i', str(audio_path),
                    '-vf', f'fps={FPS},format=yuv420p',
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-preset', 'fast',
                    '-shortest',
                    str(video_out),
                ],
                capture_output=True,
                check=True,
            )

            return {
                'title': short_title,
                'file': str(video_out),
                'cost': cost,
            }
        except Exception as e:
            print(f"  → Short failed: {short_title} — {e}")
            return None

    def _parse_duration(self, hint: str) -> float:
        """Parse a duration hint like '15s' or '1m30s' to float seconds.

        Args:
            hint: Duration string.

        Returns:
            Duration in seconds as float.
        """
        hint = str(hint).strip().lower()
        total = 0.0
        if 'm' in hint:
            parts = hint.split('m')
            total += float(parts[0]) * 60
            remainder = parts[1].replace('s', '').strip()
            if remainder:
                total += float(remainder)
        elif 's' in hint:
            total = float(hint.replace('s', ''))
        else:
            try:
                total = float(hint)
            except ValueError:
                total = 10.0
        return total

    def _find_banner(self, article_dir: Path) -> Path | None:
        """Find the banner image in the article directory.

        Args:
            article_dir: Directory to search.

        Returns:
            Path to banner image or None.
        """
        article_dir = Path(article_dir)
        for pattern in ['*banner*', '*-banner.*']:
            matches = list(article_dir.glob(pattern))
            if matches:
                return matches[0]
        # Fallback: any image file
        for ext in ('*.jpg', '*.jpeg', '*.png', '*.webp'):
            matches = list(article_dir.glob(ext))
            if matches:
                return matches[0]
        return None

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds using ffprobe.

        Args:
            audio_path: Path to audio file.

        Returns:
            Duration in seconds.
        """
        result = subprocess.run(
            [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(audio_path),
            ],
            capture_output=True,
            check=True,
        )
        return float(result.stdout.strip())


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """Wrap text to fit within max_width pixels.

    Args:
        draw: ImageDraw instance.
        text: Text to wrap.
        font: PIL font.
        max_width: Maximum line width in pixels.

    Returns:
        List of line strings.
    """
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]
        if line_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    return lines if lines else [text]
