"""Unit tests for ElevenLabs TTS wrapper."""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))


def test_generate_returns_audio_path_and_cost():
    """TTS generates audio file and returns (path, cost)."""
    from elevenlabs_tts import ElevenLabsTTS

    mock_audio_bytes = b'\xff\xfb\x90\x00' * 100  # fake MP3 bytes

    with patch('elevenlabs_tts.ElevenLabs') as MockClient:
        mock_client = MockClient.return_value
        mock_client.text_to_speech.convert.return_value = iter([mock_audio_bytes])

        tts = ElevenLabsTTS(api_key='test-key')
        output_dir = Path('/tmp/test_tts_output')
        output_dir.mkdir(exist_ok=True)

        audio_path, cost = tts.generate(
            text='Hello world, this is a test narration.',
            voice_id='test-voice-id',
            output_path=output_dir / 'test-voiceover.mp3',
        )

        assert audio_path.exists()
        assert audio_path.suffix == '.mp3'
        assert cost > 0
        audio_path.unlink(missing_ok=True)


def test_generate_with_timestamps_returns_alignment():
    """TTS with timestamps returns word-level alignment data."""
    from elevenlabs_tts import ElevenLabsTTS

    mock_audio_bytes = b'\xff\xfb\x90\x00' * 100
    mock_alignment = {
        'characters': list('Hello world'),
        'character_start_times_seconds': [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5],
        'character_end_times_seconds': [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55],
    }

    with patch('elevenlabs_tts.ElevenLabs') as MockClient:
        mock_client = MockClient.return_value
        mock_client.text_to_speech.convert_with_timestamps.return_value = iter([
            {'audio_base64': 'AAAA', 'alignment': mock_alignment}
        ])

        tts = ElevenLabsTTS(api_key='test-key')
        output_dir = Path('/tmp/test_tts_output')
        output_dir.mkdir(exist_ok=True)

        audio_path, cost, alignment = tts.generate_with_timestamps(
            text='Hello world',
            voice_id='test-voice-id',
            output_path=output_dir / 'test-voiceover.mp3',
        )

        assert alignment is not None
        assert 'character_start_times_seconds' in alignment
        audio_path.unlink(missing_ok=True)


def test_cost_calculation():
    """Cost is ~$0.30 per 1000 characters."""
    from elevenlabs_tts import ElevenLabsTTS

    tts = ElevenLabsTTS.__new__(ElevenLabsTTS)
    cost = tts._calculate_cost(1000)
    assert 0.25 <= cost <= 0.35

    cost = tts._calculate_cost(8000)
    assert 2.0 <= cost <= 3.0


def test_generate_raises_without_api_key():
    """Constructor raises if no API key."""
    from elevenlabs_tts import ElevenLabsTTS

    with patch.dict('os.environ', {}, clear=True):
        try:
            tts = ElevenLabsTTS()
            assert False, "Should have raised"
        except (ValueError, EnvironmentError):
            pass
