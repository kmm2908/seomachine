"""ElevenLabs text-to-speech wrapper.

Generates MP3 voiceover audio from text using the ElevenLabs API.
Supports word-level timestamps for caption generation.
"""
import os
import base64
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent.parent.resolve()
load_dotenv(_ROOT / '.env')

from elevenlabs import ElevenLabs

COST_PER_1K_CHARS = 0.30
DEFAULT_MODEL = 'eleven_multilingual_v2'


class ElevenLabsTTS:
    """ElevenLabs TTS provider."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.getenv('ELEVENLABS_API_KEY')
        if not self._api_key:
            raise EnvironmentError('ELEVENLABS_API_KEY not set')
        self._client = ElevenLabs(api_key=self._api_key)

    def generate(self, text: str, voice_id: str, output_path: Path,
                 model: str = DEFAULT_MODEL) -> tuple[Path, float]:
        """Generate speech audio from text. Returns (audio_path, cost_usd)."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        audio_chunks = self._client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model,
            output_format='mp3_44100_128',
        )

        with open(output_path, 'wb') as f:
            for chunk in audio_chunks:
                f.write(chunk)

        cost = self._calculate_cost(len(text))
        return output_path, cost

    def generate_with_timestamps(self, text: str, voice_id: str,
                                  output_path: Path,
                                  model: str = DEFAULT_MODEL) -> tuple[Path, float, dict | None]:
        """Generate speech with word-level timestamps for captions.
        Returns (audio_path, cost_usd, alignment_data).
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        response_chunks = self._client.text_to_speech.convert_with_timestamps(
            text=text,
            voice_id=voice_id,
            model_id=model,
            output_format='mp3_44100_128',
        )

        audio_bytes = b''
        alignment = None
        for chunk in response_chunks:
            if isinstance(chunk, dict):
                if 'audio_base64' in chunk and chunk['audio_base64']:
                    audio_bytes += base64.b64decode(chunk['audio_base64'])
                if 'alignment' in chunk and chunk['alignment']:
                    alignment = chunk['alignment']
            else:
                audio_bytes += chunk

        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

        cost = self._calculate_cost(len(text))
        return output_path, cost, alignment

    def _calculate_cost(self, char_count: int) -> float:
        """Calculate cost in USD based on character count."""
        return round((char_count / 1000) * COST_PER_1K_CHARS, 4)
