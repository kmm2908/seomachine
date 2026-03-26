"""Unit tests for video producer."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src' / 'social'))


def test_generate_slide_image():
    """generate_slide() creates a 1920x1080 image with text."""
    from video_producer import VideoProducer

    producer = VideoProducer.__new__(VideoProducer)
    output = Path('/tmp/test-slide.jpg')

    producer._generate_slide(
        text='Improved Flexibility',
        subtitle='Regular Thai massage sessions can increase range of motion',
        output_path=output,
        resolution=(1920, 1080),
    )

    assert output.exists()
    from PIL import Image
    img = Image.open(output)
    assert img.size == (1920, 1080)
    output.unlink()


def test_generate_thumbnail():
    """generate_thumbnail() creates a 1280x720 thumbnail."""
    from video_producer import VideoProducer

    producer = VideoProducer.__new__(VideoProducer)
    from PIL import Image
    banner = Path('/tmp/test-banner.jpg')
    Image.new('RGB', (1920, 1080), 'blue').save(banner)

    output = Path('/tmp/test-thumbnail.jpg')
    producer._generate_thumbnail(
        title_text='Thai Massage',
        banner_path=banner,
        output_path=output,
        logo_url=None,
    )

    assert output.exists()
    img = Image.open(output)
    assert img.size == (1280, 720)

    output.unlink()
    banner.unlink()


def test_generate_srt_from_alignment():
    """SRT generation from word timestamps."""
    from video_producer import generate_srt

    alignment = {
        'characters': list('Hello world test'),
        'character_start_times_seconds': [
            0.0, 0.05, 0.1, 0.15, 0.2,
            0.25,
            0.3, 0.35, 0.4, 0.45, 0.5,
            0.55,
            0.6, 0.65, 0.7, 0.75,
        ],
        'character_end_times_seconds': [
            0.05, 0.1, 0.15, 0.2, 0.25,
            0.3,
            0.35, 0.4, 0.45, 0.5, 0.55,
            0.6,
            0.65, 0.7, 0.75, 0.8,
        ],
    }

    srt = generate_srt(alignment, words_per_group=2)
    assert '00:00:00,000' in srt
    assert 'Hello world' in srt
    assert 'test' in srt


def test_build_ffmpeg_ken_burns_filter():
    """Ken Burns filter produces zoompan command."""
    from video_producer import build_ken_burns_filter

    filter_str = build_ken_burns_filter(
        duration_secs=10.0,
        direction='zoom_in',
        fps=30,
    )

    assert 'zoompan' in filter_str
    assert 'd=300' in filter_str  # 10s * 30fps
