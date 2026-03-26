# Content Repurposing Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully automated pipeline that takes each published blog article, creates a narrated long-form YouTube video + 3-5 shorts, generates platform-specific social media posts, and publishes everything via the GoHighLevel Social Planner API on a staggered weekly schedule.

**Architecture:** Two-stage pipeline. Stage 1 (existing) publishes blog articles to WordPress. Stage 2 (new) runs via cron ~2 hours later: reads the publish log for unprocessed articles, uses Claude to generate a video script + social posts, ElevenLabs for TTS voiceover, FFmpeg for video composition, then schedules everything through GoHighLevel's API. Five new files: three in `src/social/` (orchestrator, video producer, social post generator) and two in `data_sources/modules/` (GHL publisher, ElevenLabs TTS wrapper).

**Tech Stack:** Python 3.11+, ElevenLabs SDK (`elevenlabs`), FFmpeg (`ffmpeg-python`), Pillow, Claude API (Sonnet 4.6), GoHighLevel REST API (OAuth 2.0), existing `google_sheets.send_email()` for notifications.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `data_sources/modules/elevenlabs_tts.py` | Create | TTS wrapper: text → MP3 audio file with word-level timestamps |
| `data_sources/modules/ghl_publisher.py` | Create | GoHighLevel Social Planner API client: OAuth, media upload, post scheduling |
| `src/social/__init__.py` | Create | Empty init for package |
| `src/social/social_post_generator.py` | Create | Claude-powered: blog HTML → video script JSON + social posts JSON |
| `src/social/video_producer.py` | Create | FFmpeg composition: script + audio + images → long-form MP4 + shorts |
| `src/social/repurpose_content.py` | Create | Orchestrator CLI: finds unprocessed articles, runs full pipeline, schedules via GHL |
| `data_sources/requirements.txt` | Modify | Add `elevenlabs`, `ffmpeg-python` |
| `.env.example` | Modify | Add `ELEVENLABS_API_KEY`, `GHL_CLIENT_ID`, `GHL_CLIENT_SECRET` |
| `.gitignore` | Modify | Add `clients/*/ghl-tokens.json` |
| `tests/test_elevenlabs_tts.py` | Create | Unit tests for TTS wrapper |
| `tests/test_ghl_publisher.py` | Create | Unit tests for GHL publisher |
| `tests/test_social_post_generator.py` | Create | Unit tests for social post generator |
| `tests/test_video_producer.py` | Create | Unit tests for video producer |
| `tests/test_repurpose_content.py` | Create | Unit tests for orchestrator |

---

## Task 1: Install dependencies and update config files

**Files:**
- Modify: `data_sources/requirements.txt`
- Modify: `.env.example`
- Modify: `.gitignore`
- Create: `src/social/__init__.py`

- [ ] **Step 1: Add new packages to requirements.txt**

Append these lines to `data_sources/requirements.txt`:

```
elevenlabs>=1.0.0               # ElevenLabs TTS SDK
ffmpeg-python>=0.2.0            # FFmpeg wrapper (requires ffmpeg binary)
```

- [ ] **Step 2: Install packages and FFmpeg**

Run:
```bash
pip install -r data_sources/requirements.txt
brew install ffmpeg
```

Expected: both install cleanly. Verify FFmpeg:
```bash
ffmpeg -version
```
Expected: outputs version info (e.g. `ffmpeg version 7.x`)

- [ ] **Step 3: Add env vars to .env.example**

Append to `.env.example`:

```bash

# ElevenLabs TTS (for video voiceover)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# GoHighLevel OAuth (for social media publishing)
GHL_CLIENT_ID=your_ghl_client_id_here
GHL_CLIENT_SECRET=your_ghl_client_secret_here
```

- [ ] **Step 4: Add GHL tokens to .gitignore**

Append to `.gitignore`:

```
# GoHighLevel OAuth tokens (per-client, auto-refreshed)
clients/*/ghl-tokens.json
```

- [ ] **Step 5: Create src/social package**

```bash
touch src/social/__init__.py
```

- [ ] **Step 6: Commit**

```bash
git add data_sources/requirements.txt .env.example .gitignore src/social/__init__.py
git commit -m "feat: add dependencies and config for content repurposing pipeline"
```

---

## Task 2: ElevenLabs TTS wrapper

**Files:**
- Create: `data_sources/modules/elevenlabs_tts.py`
- Create: `tests/test_elevenlabs_tts.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_elevenlabs_tts.py`:

```python
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
        # Mock generate returns audio bytes iterator
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
        assert cost > 0  # cost based on character count
        # Cleanup
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
        # Cleanup
        audio_path.unlink(missing_ok=True)


def test_cost_calculation():
    """Cost is ~$0.30 per 1000 characters."""
    from elevenlabs_tts import ElevenLabsTTS

    tts = ElevenLabsTTS.__new__(ElevenLabsTTS)
    # 1000 chars should cost ~$0.30
    cost = tts._calculate_cost(1000)
    assert 0.25 <= cost <= 0.35

    # 8000 chars (typical blog script) should cost ~$2.40
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_elevenlabs_tts.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'elevenlabs_tts'`

- [ ] **Step 3: Write the implementation**

Create `data_sources/modules/elevenlabs_tts.py`:

```python
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

# ElevenLabs pricing: ~$0.30 per 1,000 characters
COST_PER_1K_CHARS = 0.30

# Default model — natural, expressive multilingual
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
        """Generate speech audio from text.

        Returns (audio_path, cost_usd).
        """
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
        alignment_data contains character_start_times_seconds and character_end_times_seconds.
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_elevenlabs_tts.py -v`

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add data_sources/modules/elevenlabs_tts.py tests/test_elevenlabs_tts.py
git commit -m "feat: add ElevenLabs TTS wrapper with timestamp support"
```

---

## Task 3: GoHighLevel publisher module

**Files:**
- Create: `data_sources/modules/ghl_publisher.py`
- Create: `tests/test_ghl_publisher.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ghl_publisher.py`:

```python
"""Unit tests for GoHighLevel Social Planner publisher."""
import sys
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))


def test_token_refresh_on_expired():
    """Auto-refreshes token when access_token is expired."""
    from ghl_publisher import GHLPublisher

    tokens = {
        'access_token': 'expired-token',
        'refresh_token': 'valid-refresh',
        'expires_at': 0,  # already expired
    }
    tokens_path = Path('/tmp/test-ghl-tokens.json')
    tokens_path.write_text(json.dumps(tokens))

    new_tokens = {
        'access_token': 'new-access-token',
        'refresh_token': 'new-refresh-token',
        'expires_in': 86399,
    }

    with patch('ghl_publisher.requests.post') as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = new_tokens
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        pub = GHLPublisher(
            location_id='loc123',
            tokens_path=tokens_path,
            client_id='cid',
            client_secret='csec',
        )

        assert pub._access_token == 'new-access-token'
        # Verify new tokens were saved
        saved = json.loads(tokens_path.read_text())
        assert saved['access_token'] == 'new-access-token'
        assert saved['refresh_token'] == 'new-refresh-token'

    tokens_path.unlink(missing_ok=True)


def test_create_post_calls_correct_endpoint():
    """create_post hits /social-media-posting/{locationId}/posts."""
    from ghl_publisher import GHLPublisher

    tokens = {
        'access_token': 'valid-token',
        'refresh_token': 'refresh',
        'expires_at': time.time() + 86400,
    }
    tokens_path = Path('/tmp/test-ghl-tokens.json')
    tokens_path.write_text(json.dumps(tokens))

    with patch('ghl_publisher.requests.Session') as MockSession:
        mock_session = MockSession.return_value
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'id': 'post-123', 'status': 'scheduled'}
        mock_resp.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_resp

        pub = GHLPublisher(
            location_id='loc123',
            tokens_path=tokens_path,
            client_id='cid',
            client_secret='csec',
        )

        post_id = pub.create_post(
            account_id='acc-yt-1',
            text='Test post content',
            scheduled_at='2026-04-01T10:00:00Z',
        )

        assert post_id == 'post-123'
        call_args = mock_session.post.call_args
        assert 'social-media-posting/loc123/posts' in call_args[0][0]

    tokens_path.unlink(missing_ok=True)


def test_upload_media_returns_url():
    """upload_media uploads file and returns hosted URL."""
    from ghl_publisher import GHLPublisher

    tokens = {
        'access_token': 'valid-token',
        'refresh_token': 'refresh',
        'expires_at': time.time() + 86400,
    }
    tokens_path = Path('/tmp/test-ghl-tokens.json')
    tokens_path.write_text(json.dumps(tokens))

    with patch('ghl_publisher.requests.Session') as MockSession:
        mock_session = MockSession.return_value
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'url': 'https://storage.ghl.com/media/abc.jpg'}
        mock_resp.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_resp

        pub = GHLPublisher(
            location_id='loc123',
            tokens_path=tokens_path,
            client_id='cid',
            client_secret='csec',
        )

        # Create a dummy file
        dummy = Path('/tmp/test-upload.jpg')
        dummy.write_bytes(b'\xff\xd8\xff\xe0' * 10)

        url = pub.upload_media(dummy)
        assert url == 'https://storage.ghl.com/media/abc.jpg'

        dummy.unlink(missing_ok=True)

    tokens_path.unlink(missing_ok=True)


def test_week_alternation_even_odd():
    """Even ISO weeks use thread, odd use standalone."""
    from ghl_publisher import get_x_format_for_date
    from datetime import date

    # ISO week 1 is odd → standalone
    # ISO week 2 is even → thread
    d_odd = date(2026, 1, 5)   # ISO week 1
    d_even = date(2026, 1, 12)  # ISO week 2

    assert get_x_format_for_date(d_odd) == 'standalone'
    assert get_x_format_for_date(d_even) == 'thread'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_ghl_publisher.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'ghl_publisher'`

- [ ] **Step 3: Write the implementation**

Create `data_sources/modules/ghl_publisher.py`:

```python
"""GoHighLevel Social Planner API client.

Handles OAuth 2.0 token management, media upload, and post scheduling
across all social platforms via the GHL Social Planner API.
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import date, datetime, timedelta

import requests
from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent.parent.resolve()
load_dotenv(_ROOT / '.env')

GHL_API_BASE = 'https://services.leadconnectorhq.com'
GHL_TOKEN_URL = f'{GHL_API_BASE}/oauth/token'

# Rate limit: 10 requests/second
REQUEST_DELAY = 0.15  # slight buffer


def get_x_format_for_date(d: date) -> str:
    """Return 'thread' for even ISO weeks, 'standalone' for odd."""
    iso_week = d.isocalendar()[1]
    return 'thread' if iso_week % 2 == 0 else 'standalone'


class GHLPublisher:
    """GoHighLevel Social Planner API client with OAuth auto-refresh."""

    def __init__(self, location_id: str, tokens_path: Path,
                 client_id: str | None = None, client_secret: str | None = None):
        self._location_id = location_id
        self._tokens_path = Path(tokens_path)
        self._client_id = client_id or os.getenv('GHL_CLIENT_ID')
        self._client_secret = client_secret or os.getenv('GHL_CLIENT_SECRET')

        if not self._client_id or not self._client_secret:
            raise EnvironmentError('GHL_CLIENT_ID and GHL_CLIENT_SECRET must be set')

        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'Version': '2021-07-28',
            'User-Agent': 'SEOMachine/1.0 (Social Publisher)',
        })

        self._load_tokens()

    @classmethod
    def from_config(cls, ghl_config: dict, client_dir: Path) -> 'GHLPublisher':
        """Create from client config dict.

        ghl_config should be the 'ghl' block from config.json.
        """
        return cls(
            location_id=ghl_config['location_id'],
            tokens_path=client_dir / 'ghl-tokens.json',
        )

    def _load_tokens(self) -> None:
        """Load tokens from disk; refresh if expired."""
        if not self._tokens_path.exists():
            raise FileNotFoundError(
                f'GHL tokens not found at {self._tokens_path}. '
                f'Run the OAuth onboarding flow first.'
            )

        tokens = json.loads(self._tokens_path.read_text())
        expires_at = tokens.get('expires_at', 0)

        if time.time() >= expires_at - 300:  # refresh 5 min early
            self._refresh_tokens(tokens['refresh_token'])
        else:
            self._access_token = tokens['access_token']
            self._session.headers['Authorization'] = f'Bearer {self._access_token}'

    def _refresh_tokens(self, refresh_token: str) -> None:
        """Refresh OAuth tokens and save to disk."""
        resp = requests.post(GHL_TOKEN_URL, data={
            'grant_type': 'refresh_token',
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'refresh_token': refresh_token,
        })
        resp.raise_for_status()
        data = resp.json()

        self._access_token = data['access_token']
        self._session.headers['Authorization'] = f'Bearer {self._access_token}'

        # Save new tokens (refresh token is single-use)
        tokens = {
            'access_token': data['access_token'],
            'refresh_token': data['refresh_token'],
            'expires_at': time.time() + data.get('expires_in', 86399),
        }
        self._tokens_path.write_text(json.dumps(tokens, indent=2))

    def _post(self, endpoint: str, payload: dict) -> dict:
        """POST to GHL API with rate limiting."""
        url = f'{GHL_API_BASE}/{endpoint}'
        time.sleep(REQUEST_DELAY)
        resp = self._session.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """GET from GHL API."""
        url = f'{GHL_API_BASE}/{endpoint}'
        time.sleep(REQUEST_DELAY)
        resp = self._session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def upload_media(self, file_path: Path) -> str:
        """Upload image/video to GHL media storage. Returns hosted URL."""
        url = f'{GHL_API_BASE}/medias/upload-file'
        time.sleep(REQUEST_DELAY)

        # Remove Content-Type for multipart upload
        headers = {k: v for k, v in self._session.headers.items()
                   if k.lower() != 'content-type'}

        with open(file_path, 'rb') as f:
            resp = requests.post(
                url,
                headers=headers,
                files={'file': (file_path.name, f)},
                data={'locationId': self._location_id},
            )
        resp.raise_for_status()
        return resp.json()['url']

    def create_post(self, account_id: str, text: str,
                    media_urls: list[str] | None = None,
                    scheduled_at: str | None = None,
                    platform_details: dict | None = None) -> str:
        """Create/schedule a social media post. Returns GHL post ID."""
        payload = {
            'locationId': self._location_id,
            'accountIds': [account_id],
            'summary': text,
            'status': 'scheduled' if scheduled_at else 'published',
        }
        if scheduled_at:
            payload['scheduledAt'] = scheduled_at
        if media_urls:
            payload['mediaUrls'] = media_urls
        if platform_details:
            payload['details'] = platform_details

        result = self._post(
            f'social-media-posting/{self._location_id}/posts',
            payload,
        )
        return result.get('id', '')

    def schedule_youtube_video(self, account_id: str, video_url: str,
                                title: str, description: str,
                                tags: list[str], thumbnail_url: str | None,
                                scheduled_at: str) -> str:
        """Schedule a YouTube video upload. Returns GHL post ID."""
        details = {
            'youtube': {
                'title': title,
                'description': description,
                'tags': tags,
                'type': 'video',
            }
        }
        if thumbnail_url:
            details['youtube']['thumbnailUrl'] = thumbnail_url

        return self.create_post(
            account_id=account_id,
            text=title,
            media_urls=[video_url],
            scheduled_at=scheduled_at,
            platform_details=details,
        )

    def schedule_youtube_short(self, account_id: str, video_url: str,
                                title: str, description: str,
                                scheduled_at: str) -> str:
        """Schedule a YouTube Short upload. Returns GHL post ID."""
        details = {
            'youtube': {
                'title': title,
                'description': description,
                'type': 'short',
            }
        }
        return self.create_post(
            account_id=account_id,
            text=title,
            media_urls=[video_url],
            scheduled_at=scheduled_at,
            platform_details=details,
        )

    def get_accounts(self) -> list[dict]:
        """List connected social media accounts for this location."""
        result = self._get(
            f'social-media-posting/{self._location_id}/oauth/accounts'
        )
        return result.get('accounts', [])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_ghl_publisher.py -v`

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add data_sources/modules/ghl_publisher.py tests/test_ghl_publisher.py
git commit -m "feat: add GoHighLevel Social Planner API client"
```

---

## Task 4: Social post generator (Claude-powered)

**Files:**
- Create: `src/social/social_post_generator.py`
- Create: `tests/test_social_post_generator.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_social_post_generator.py`:

```python
"""Unit tests for social post generator."""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src' / 'social'))


SAMPLE_HTML = """<!-- SECTION 1 -->
<h2>Thai Massage Benefits: Why This Ancient Practice Works</h2>
<p>Thai massage has been practised for over 2,500 years.</p>
<h3>Improved Flexibility</h3>
<p>Regular sessions can increase range of motion by up to 15%.</p>
<h3>Stress Relief</h3>
<p>Studies show cortisol levels drop significantly after a session.</p>

<!-- SECTION 2 FAQ -->
<h2>Frequently Asked Questions</h2>
<details><summary>Does Thai massage hurt?</summary>
<p>You may feel deep pressure, but it should never be painful.</p></details>
<details><summary>How often should I get Thai massage?</summary>
<p>Once a week for therapeutic benefits, or monthly for maintenance.</p></details>

<!-- SCHEMA -->
<script type="application/ld+json">{"@type": "BlogPosting"}</script>"""

SAMPLE_METADATA = {
    'title': 'Thai Massage Benefits: Why This Ancient Practice Works',
    'post_url': 'https://glasgowthaimassage.co.uk/blog/thai-massage-benefits/',
    'booking_url': 'https://glasgowthaimassage.co.uk/booking/',
    'business_name': 'Glasgow Thai Massage',
    'abbreviation': 'GTM',
    'content_type': 'blog',
}


def _make_mock_response(content_json: dict):
    """Build a mock Claude API response."""
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(type='text', text=json.dumps(content_json))]
    mock_msg.usage.input_tokens = 5000
    mock_msg.usage.output_tokens = 3000
    return mock_msg


def test_generate_returns_video_script_and_social_posts():
    """generate() returns structured video script and social posts."""
    from social_post_generator import SocialPostGenerator

    expected_output = {
        'video_script': {
            'title': 'Thai Massage Benefits',
            'description': 'Learn why Thai massage works',
            'tags': ['thai massage'],
            'thumbnail_text': 'Thai Massage Benefits',
            'scenes': [
                {
                    'scene_number': 1,
                    'narration': 'Thai massage has been practised for 2500 years.',
                    'visual_type': 'ken_burns',
                    'visual_description': 'Spa treatment scene',
                    'duration_hint': '15s',
                    'source_image': 'banner.jpg',
                    'text_overlay': None,
                }
            ],
            'shorts': [
                {
                    'short_number': 1,
                    'type': 'surprising_fact',
                    'hook': 'Did you know Thai massage is 2500 years old?',
                    'narration': 'Thai massage dates back 2500 years.',
                    'visual_type': 'text_overlay',
                    'text_overlays': ['2,500 Years', 'Of Healing'],
                    'duration_target': '30s',
                    'source_scenes': [1],
                }
            ],
        },
        'social_posts': {
            'linkedin': {'text': 'Professional post about Thai massage.', 'hashtags': ['#ThaiMassage']},
            'facebook': {'text': 'Check out Thai massage benefits!', 'hashtags': ['#ThaiMassage']},
            'x_thread': [{'text': 'Thai massage thread tweet 1', 'media': 'banner'}],
            'x_standalone': [{'text': 'Thai massage tweet 1', 'day_offset': 0}],
            'instagram': {'caption': 'Thai massage caption', 'hashtags': ['#ThaiMassage'], 'media': 'banner'},
            'gbp': {'text': 'Local Thai massage post', 'cta_type': 'BOOK', 'cta_url': 'https://example.com/booking/', 'media': 'banner'},
        },
    }

    with patch('social_post_generator.anthropic') as mock_anthropic:
        mock_client = mock_anthropic.Anthropic.return_value
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        mock_stream_ctx.get_final_message.return_value = _make_mock_response(expected_output)
        mock_client.messages.stream.return_value = mock_stream_ctx

        gen = SocialPostGenerator()
        result, cost = gen.generate(SAMPLE_HTML, SAMPLE_METADATA)

        assert 'video_script' in result
        assert 'social_posts' in result
        assert len(result['video_script']['scenes']) >= 1
        assert len(result['video_script']['shorts']) >= 1
        assert 'linkedin' in result['social_posts']
        assert 'x_thread' in result['social_posts']
        assert 'x_standalone' in result['social_posts']
        assert 'gbp' in result['social_posts']
        assert cost > 0


def test_extract_content_from_html():
    """extract_content() parses HTML into structured text."""
    from social_post_generator import extract_content_from_html

    result = extract_content_from_html(SAMPLE_HTML)

    assert result['title'] == 'Thai Massage Benefits: Why This Ancient Practice Works'
    assert 'practised for over 2,500 years' in result['body_text']
    assert len(result['faq_questions']) == 2
    assert result['faq_questions'][0]['question'] == 'Does Thai massage hurt?'
    assert 'headings' in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_social_post_generator.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'social_post_generator'`

- [ ] **Step 3: Write the implementation**

Create `src/social/social_post_generator.py`:

```python
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
    # Split sections
    section1 = ''
    section2 = ''
    if '<!-- SECTION 1 -->' in html:
        parts = html.split('<!-- SECTION 2 FAQ -->')
        section1 = parts[0].replace('<!-- SECTION 1 -->', '').strip()
        if len(parts) > 1:
            faq_and_schema = parts[1].split('<!-- SCHEMA -->')
            section2 = faq_and_schema[0].strip()

    # Extract title from first h2
    title_match = re.search(r'<h2[^>]*>(.*?)</h2>', section1, re.DOTALL)
    title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else ''

    # Extract body text
    extractor = _HTMLTextExtractor()
    extractor.feed(section1)
    body_text = ' '.join(extractor._text_parts).strip()
    headings = extractor._headings

    # Extract FAQ questions
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
        result_dict has keys: 'video_script', 'social_posts'.
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

        # Extract JSON from response
        text = final.content[0].text.strip()
        # Strip markdown code block if present
        if text.startswith('```'):
            text = re.sub(r'^```\w*\n?', '', text)
            text = re.sub(r'\n?```$', '', text)
            text = text.strip()

        result = json.loads(text)
        return result, cost
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_social_post_generator.py -v`

Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/social/social_post_generator.py tests/test_social_post_generator.py
git commit -m "feat: add Claude-powered social post and video script generator"
```

---

## Task 5: Video producer (FFmpeg + slides + Ken Burns)

**Files:**
- Create: `src/social/video_producer.py`
- Create: `tests/test_video_producer.py`

This is the largest component. It takes a video script JSON, TTS audio, and article images, then composes a long-form MP4 and 3-5 shorts.

- [ ] **Step 1: Write the failing test**

Create `tests/test_video_producer.py`:

```python
"""Unit tests for video producer."""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, call

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src' / 'social'))


SAMPLE_SCRIPT = {
    'title': 'Thai Massage Benefits',
    'description': 'Learn about Thai massage',
    'tags': ['thai massage'],
    'thumbnail_text': 'Thai Massage',
    'scenes': [
        {
            'scene_number': 1,
            'narration': 'Thai massage has been practised for over 2500 years.',
            'visual_type': 'ken_burns',
            'visual_description': 'Spa treatment scene',
            'duration_hint': '10s',
            'source_image': 'banner.jpg',
            'text_overlay': 'Thai Massage Benefits',
        },
        {
            'scene_number': 2,
            'narration': 'Regular sessions improve flexibility.',
            'visual_type': 'slide',
            'visual_description': 'Key benefit: flexibility',
            'duration_hint': '8s',
            'source_image': None,
            'text_overlay': 'Improved Flexibility',
        },
    ],
    'shorts': [
        {
            'short_number': 1,
            'type': 'surprising_fact',
            'hook': 'Did you know?',
            'narration': 'Thai massage is 2500 years old and still one of the most effective therapies.',
            'visual_type': 'text_overlay',
            'text_overlays': ['2,500 Years Old', 'Still Effective'],
            'duration_target': '20s',
            'source_scenes': [1],
        },
    ],
}


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
    # Create a dummy banner image
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
            0.0, 0.05, 0.1, 0.15, 0.2,  # Hello
            0.25,                         # space
            0.3, 0.35, 0.4, 0.45, 0.5,   # world
            0.55,                         # space
            0.6, 0.65, 0.7, 0.75,         # test
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
    assert '00:00:00,000' in srt  # starts at 0
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_video_producer.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'video_producer'`

- [ ] **Step 3: Write the implementation**

Create `src/social/video_producer.py`:

```python
"""Video producer — composes long-form videos and shorts from scripts.

Uses FFmpeg for video composition with three visual styles:
- Ken Burns (pan/zoom on images)
- Slides (Pillow-generated text cards)
- Text overlays (animated text on gradient backgrounds)

Audio comes from ElevenLabs TTS (via elevenlabs_tts module).
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

# Video specs
LONGFORM_RES = (1920, 1080)
SHORT_RES = (1080, 1920)
FPS = 30
THUMBNAIL_RES = (1280, 720)

# Slide styling
SLIDE_BG_COLOR = (25, 25, 35)       # dark navy
SLIDE_TEXT_COLOR = (255, 255, 255)   # white
SLIDE_ACCENT_COLOR = (78, 172, 135) # teal accent
SLIDE_SUBTITLE_COLOR = (180, 180, 200)

# Ken Burns directions cycle
KB_DIRECTIONS = ['zoom_in', 'zoom_out', 'pan_left', 'pan_right']


def build_ken_burns_filter(duration_secs: float, direction: str = 'zoom_in',
                            fps: int = FPS) -> str:
    """Build FFmpeg zoompan filter for Ken Burns effect."""
    total_frames = int(duration_secs * fps)
    if direction == 'zoom_in':
        return f"zoompan=z='min(zoom+0.001,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
    elif direction == 'zoom_out':
        return f"zoompan=z='if(lte(zoom,1.0),1.3,max(1.001,zoom-0.001))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
    elif direction == 'pan_left':
        return f"zoompan=z='1.15':x='if(lte(on,1),iw/4,x-1)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
    elif direction == 'pan_right':
        return f"zoompan=z='1.15':x='if(lte(on,1),0,x+1)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
    return f"zoompan=z='1.15':d={total_frames}:s=1920x1080:fps={fps}"


def generate_srt(alignment: dict, words_per_group: int = 5) -> str:
    """Generate SRT subtitle file from character-level alignment data."""
    chars = alignment.get('characters', [])
    starts = alignment.get('character_start_times_seconds', [])
    ends = alignment.get('character_end_times_seconds', [])

    if not chars or len(chars) != len(starts):
        return ''

    # Reconstruct words with timing
    words = []
    current_word = ''
    word_start = 0.0
    for i, char in enumerate(chars):
        if char == ' ':
            if current_word:
                words.append((current_word, word_start, ends[i - 1] if i > 0 else starts[i]))
                current_word = ''
        else:
            if not current_word:
                word_start = starts[i]
            current_word += char
    if current_word:
        words.append((current_word, word_start, ends[-1]))

    # Group words into subtitle blocks
    srt_blocks = []
    for i in range(0, len(words), words_per_group):
        group = words[i:i + words_per_group]
        text = ' '.join(w[0] for w in group)
        start_time = group[0][1]
        end_time = group[-1][2]

        def _fmt(secs):
            h = int(secs // 3600)
            m = int((secs % 3600) // 60)
            s = int(secs % 60)
            ms = int((secs % 1) * 1000)
            return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

        idx = len(srt_blocks) + 1
        srt_blocks.append(f'{idx}\n{_fmt(start_time)} --> {_fmt(end_time)}\n{text}\n')

    return '\n'.join(srt_blocks)


class VideoProducer:
    """Produces long-form videos and shorts from video scripts."""

    def __init__(self, voice_id: str, elevenlabs_api_key: str | None = None):
        self._voice_id = voice_id
        self._tts = ElevenLabsTTS(api_key=elevenlabs_api_key)

    def produce(self, script: dict, article_dir: Path, video_dir: Path,
                logo_url: str | None = None) -> tuple[dict, float]:
        """Produce long-form video and shorts.

        Returns (result_dict, total_cost_usd).
        result_dict has: longform_path, shorts_paths, thumbnail_path, srt_path.
        """
        video_dir.mkdir(parents=True, exist_ok=True)
        shorts_dir = video_dir / 'shorts'
        shorts_dir.mkdir(exist_ok=True)
        total_cost = 0.0

        slug = article_dir.name

        # 1. Generate full narration text and TTS audio
        full_narration = ' '.join(
            scene['narration'] for scene in script['scenes']
        )
        audio_path = video_dir / f'{slug}-voiceover.mp3'
        print(f'  → Generating voiceover ({len(full_narration)} chars)...')
        audio_path, tts_cost, alignment = self._tts.generate_with_timestamps(
            text=full_narration,
            voice_id=self._voice_id,
            output_path=audio_path,
        )
        total_cost += tts_cost
        print(f'    → TTS done (${tts_cost:.4f})')

        # 2. Generate SRT captions
        srt_path = video_dir / f'{slug}-captions.srt'
        if alignment:
            srt_content = generate_srt(alignment)
            srt_path.write_text(srt_content, encoding='utf-8')
            print(f'    → Captions: {srt_path.name}')

        # 3. Generate scene visuals (slides / ken burns source images)
        scene_clips = []
        tmp_dir = Path(tempfile.mkdtemp(prefix='seomachine_video_'))

        try:
            for i, scene in enumerate(script['scenes']):
                duration = self._parse_duration(scene.get('duration_hint', '10s'))
                visual_type = scene.get('visual_type', 'slide')
                scene_video = tmp_dir / f'scene-{i:03d}.mp4'

                if visual_type == 'ken_burns' and scene.get('source_image'):
                    source_img = article_dir / scene['source_image']
                    if source_img.exists():
                        self._render_ken_burns_scene(
                            source_img, scene_video, duration,
                            direction=KB_DIRECTIONS[i % len(KB_DIRECTIONS)],
                            text_overlay=scene.get('text_overlay'),
                        )
                    else:
                        self._render_slide_scene(scene, scene_video, duration)
                elif visual_type == 'text_overlay':
                    self._render_text_overlay_scene(scene, scene_video, duration)
                else:
                    self._render_slide_scene(scene, scene_video, duration)

                scene_clips.append(scene_video)

            # 4. Concatenate scenes with transitions + audio
            longform_path = video_dir / f'{slug}-longform.mp4'
            print(f'  → Composing long-form video ({len(scene_clips)} scenes)...')
            self._concat_with_audio(scene_clips, audio_path, longform_path)
            print(f'    → Long-form: {longform_path.name}')

            # 5. Generate thumbnail
            thumbnail_path = video_dir / f'{slug}-thumbnail.jpg'
            banner_path = self._find_banner(article_dir)
            self._generate_thumbnail(
                title_text=script.get('thumbnail_text', script['title'][:30]),
                banner_path=banner_path,
                output_path=thumbnail_path,
                logo_url=logo_url,
            )
            print(f'    → Thumbnail: {thumbnail_path.name}')

            # 6. Generate shorts
            shorts_paths = []
            for short in script.get('shorts', []):
                short_path = self._produce_short(
                    short, shorts_dir, slug, article_dir,
                )
                if short_path:
                    shorts_paths.append(short_path)
                    print(f'    → Short {short["short_number"]}: {short_path.name}')

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        return {
            'longform_path': longform_path,
            'shorts_paths': shorts_paths,
            'thumbnail_path': thumbnail_path,
            'srt_path': srt_path,
            'audio_path': audio_path,
        }, total_cost

    def _parse_duration(self, hint: str) -> float:
        """Parse duration hint like '15s' or '1m30s' to seconds."""
        hint = hint.strip().lower()
        if hint.endswith('s'):
            try:
                return float(hint[:-1])
            except ValueError:
                pass
        if 'm' in hint:
            parts = hint.replace('s', '').split('m')
            try:
                return float(parts[0]) * 60 + float(parts[1] or 0)
            except (ValueError, IndexError):
                pass
        return 10.0  # default

    def _find_banner(self, article_dir: Path) -> Path | None:
        """Find the banner image in the article directory."""
        for f in article_dir.iterdir():
            if 'banner' in f.name.lower() and f.suffix.lower() in ('.jpg', '.jpeg', '.png'):
                return f
        # Fallback: first jpg
        jpgs = list(article_dir.glob('*.jpg'))
        return jpgs[0] if jpgs else None

    def _generate_slide(self, text: str, subtitle: str | None,
                        output_path: Path, resolution: tuple[int, int] = LONGFORM_RES) -> None:
        """Generate a slide image with text overlay."""
        img = Image.new('RGB', resolution, SLIDE_BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Use default font (Pillow built-in) with appropriate sizes
        try:
            title_font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 72)
            sub_font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 36)
        except (IOError, OSError):
            title_font = ImageFont.load_default()
            sub_font = ImageFont.load_default()

        # Center title text
        w, h = resolution
        bbox = draw.textbbox((0, 0), text, font=title_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (w - text_w) // 2
        y = (h - text_h) // 2 - 40

        # Accent bar above title
        bar_y = y - 20
        draw.rectangle([(w // 2 - 60, bar_y), (w // 2 + 60, bar_y + 4)],
                       fill=SLIDE_ACCENT_COLOR)

        draw.text((x, y), text, fill=SLIDE_TEXT_COLOR, font=title_font)

        if subtitle:
            sub_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
            sub_w = sub_bbox[2] - sub_bbox[0]
            draw.text(((w - sub_w) // 2, y + text_h + 30), subtitle,
                      fill=SLIDE_SUBTITLE_COLOR, font=sub_font)

        img.save(output_path, quality=95)

    def _generate_thumbnail(self, title_text: str, banner_path: Path | None,
                            output_path: Path, logo_url: str | None = None) -> None:
        """Generate YouTube thumbnail (1280x720)."""
        if banner_path and banner_path.exists():
            img = Image.open(banner_path).resize(THUMBNAIL_RES, Image.LANCZOS)
            # Darken for text readability
            from PIL import ImageEnhance
            img = ImageEnhance.Brightness(img).enhance(0.5)
        else:
            img = Image.new('RGB', THUMBNAIL_RES, SLIDE_BG_COLOR)

        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 96)
        except (IOError, OSError):
            font = ImageFont.load_default()

        # Center the title
        w, h = THUMBNAIL_RES
        bbox = draw.textbbox((0, 0), title_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (w - text_w) // 2
        y = (h - text_h) // 2

        # Text shadow
        draw.text((x + 3, y + 3), title_text, fill=(0, 0, 0), font=font)
        draw.text((x, y), title_text, fill=(255, 255, 255), font=font)

        img.save(output_path, quality=95)

    def _render_slide_scene(self, scene: dict, output_path: Path,
                            duration: float) -> None:
        """Render a slide scene as an MP4 clip."""
        slide_path = output_path.with_suffix('.jpg')
        self._generate_slide(
            text=scene.get('text_overlay') or scene.get('visual_description', ''),
            subtitle=scene.get('visual_description') if scene.get('text_overlay') else None,
            output_path=slide_path,
        )
        # Convert still image to video with duration
        subprocess.run([
            'ffmpeg', '-y', '-loop', '1', '-i', str(slide_path),
            '-c:v', 'libx264', '-t', str(duration),
            '-pix_fmt', 'yuv420p', '-r', str(FPS),
            '-vf', f'scale={LONGFORM_RES[0]}:{LONGFORM_RES[1]}',
            str(output_path),
        ], capture_output=True, check=True)
        slide_path.unlink(missing_ok=True)

    def _render_ken_burns_scene(self, source_image: Path, output_path: Path,
                                 duration: float, direction: str = 'zoom_in',
                                 text_overlay: str | None = None) -> None:
        """Render a Ken Burns scene from a source image."""
        # Ensure image is large enough for zoompan
        img = Image.open(source_image)
        if img.size[0] < LONGFORM_RES[0] * 2 or img.size[1] < LONGFORM_RES[1] * 2:
            new_size = (max(img.size[0], LONGFORM_RES[0] * 2),
                        max(img.size[1], LONGFORM_RES[1] * 2))
            img = img.resize(new_size, Image.LANCZOS)

        tmp_img = output_path.with_name(output_path.stem + '_src.jpg')
        img.save(tmp_img, quality=95)

        kb_filter = build_ken_burns_filter(duration, direction)

        cmd = [
            'ffmpeg', '-y', '-i', str(tmp_img),
            '-vf', kb_filter,
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            str(output_path),
        ]

        # Add text overlay if specified
        if text_overlay:
            # Overlay text on the Ken Burns output
            cmd_overlay = [
                'ffmpeg', '-y', '-i', str(tmp_img),
                '-vf', f"{kb_filter},drawtext=text='{text_overlay}':fontsize=64:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h-120",
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                str(output_path),
            ]
            subprocess.run(cmd_overlay, capture_output=True, check=True)
        else:
            subprocess.run(cmd, capture_output=True, check=True)

        tmp_img.unlink(missing_ok=True)

    def _render_text_overlay_scene(self, scene: dict, output_path: Path,
                                    duration: float) -> None:
        """Render a text-overlay scene (gradient background + animated text)."""
        # For now, render as a slide — animation can be enhanced later
        self._render_slide_scene(scene, output_path, duration)

    def _concat_with_audio(self, clips: list[Path], audio_path: Path,
                            output_path: Path) -> None:
        """Concatenate video clips and mix with audio track."""
        # Create concat file
        concat_file = output_path.with_suffix('.txt')
        with open(concat_file, 'w') as f:
            for clip in clips:
                f.write(f"file '{clip}'\n")

        subprocess.run([
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0', '-i', str(concat_file),
            '-i', str(audio_path),
            '-c:v', 'libx264', '-c:a', 'aac', '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            '-shortest',
            str(output_path),
        ], capture_output=True, check=True)

        concat_file.unlink(missing_ok=True)

    def _produce_short(self, short: dict, shorts_dir: Path, slug: str,
                       article_dir: Path) -> Path | None:
        """Produce a single short video clip."""
        num = short['short_number']
        hook_slug = short.get('hook', 'short')[:20].lower()
        hook_slug = ''.join(c if c.isalnum() else '-' for c in hook_slug).strip('-')
        short_path = shorts_dir / f'short-{num}-{hook_slug}.mp4'

        # Generate TTS for this short's narration
        audio_path = shorts_dir / f'short-{num}-audio.mp3'
        narration = short.get('narration', '')
        if not narration:
            return None

        try:
            audio_path, _, alignment = self._tts.generate_with_timestamps(
                text=narration,
                voice_id=self._voice_id,
                output_path=audio_path,
            )
        except Exception as e:
            print(f'    → Short {num} TTS failed: {e}')
            return None

        # Generate slide for the short (vertical 9:16)
        slide_path = shorts_dir / f'short-{num}-slide.jpg'
        text_overlays = short.get('text_overlays', [short.get('hook', '')])
        self._generate_slide(
            text='\n'.join(text_overlays[:3]),
            subtitle=None,
            output_path=slide_path,
            resolution=SHORT_RES,
        )

        # Get audio duration
        duration = self._get_audio_duration(audio_path)

        # Compose: slide video + audio + burned captions
        slide_video = shorts_dir / f'short-{num}-raw.mp4'
        subprocess.run([
            'ffmpeg', '-y', '-loop', '1', '-i', str(slide_path),
            '-c:v', 'libx264', '-t', str(duration + 2),  # +2s for CTA
            '-pix_fmt', 'yuv420p', '-r', str(FPS),
            '-vf', f'scale={SHORT_RES[0]}:{SHORT_RES[1]}',
            str(slide_video),
        ], capture_output=True, check=True)

        # Add audio
        subprocess.run([
            'ffmpeg', '-y',
            '-i', str(slide_video), '-i', str(audio_path),
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k',
            '-shortest',
            str(short_path),
        ], capture_output=True, check=True)

        # Cleanup temp files
        slide_path.unlink(missing_ok=True)
        slide_video.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)

        return short_path

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds using ffprobe."""
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', str(audio_path),
        ], capture_output=True, text=True)
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 30.0  # default
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_video_producer.py -v`

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/social/video_producer.py tests/test_video_producer.py
git commit -m "feat: add FFmpeg video producer with Ken Burns, slides, and shorts"
```

---

## Task 6: Orchestrator CLI (repurpose_content.py)

**Files:**
- Create: `src/social/repurpose_content.py`
- Create: `tests/test_repurpose_content.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_repurpose_content.py`:

```python
"""Unit tests for content repurposer orchestrator."""
import sys
import csv
import json
from pathlib import Path
from datetime import date
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src' / 'social'))


def test_find_unprocessed_articles():
    """Finds articles in publish log that haven't been socially processed."""
    from repurpose_content import find_unprocessed_articles

    # Create a fake publish log
    publish_log = Path('/tmp/test-publish-log.csv')
    with open(publish_log, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'abbr', 'topic', 'content_type', 'status', 'post_id', 'cost', 'notes'])
        writer.writeheader()
        writer.writerow({'date': '2026-03-25', 'abbr': 'gtm', 'topic': 'Thai Massage Benefits', 'content_type': 'blog', 'status': 'published', 'post_id': '123', 'cost': '$0.40', 'notes': 'https://example.com/wp-admin/post.php?post=123'})
        writer.writerow({'date': '2026-03-25', 'abbr': 'gtm', 'topic': 'Already Processed', 'content_type': 'blog', 'status': 'published', 'post_id': '124', 'cost': '$0.40', 'notes': ''})
        writer.writerow({'date': '2026-03-25', 'abbr': 'sdy', 'topic': 'Failed Post', 'content_type': 'blog', 'status': 'failed', 'post_id': '', 'cost': '', 'notes': ''})

    # Create a fake social log (one already processed)
    social_log = Path('/tmp/test-social-log.csv')
    with open(social_log, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'abbr', 'topic', 'content_type', 'video_status', 'shorts_count', 'platforms', 'ghl_post_ids', 'cost', 'notes'])
        writer.writeheader()
        writer.writerow({'date': '2026-03-25', 'abbr': 'gtm', 'topic': 'Already Processed', 'content_type': 'blog', 'video_status': 'uploaded', 'shorts_count': '3', 'platforms': 'yt,fb', 'ghl_post_ids': 'p1|p2', 'cost': '$3.20', 'notes': ''})

    articles = find_unprocessed_articles('gtm', publish_log, social_log)

    # Should find 1: "Thai Massage Benefits" (published, not in social log)
    # Should NOT find: "Already Processed" (in social log) or "Failed Post" (not published)
    assert len(articles) == 1
    assert articles[0]['topic'] == 'Thai Massage Benefits'

    publish_log.unlink()
    social_log.unlink()


def test_build_schedule_offsets():
    """Schedule assigns correct day offsets for each platform."""
    from repurpose_content import build_schedule

    publish_date = date(2026, 3, 30)  # Monday
    schedule = build_schedule(publish_date, shorts_count=3, x_format='standalone')

    # Day +1 = YouTube long-form
    assert any(s['platform'] == 'youtube' and s['content_type'] == 'longform'
               for s in schedule if s['day_offset'] == 1)
    # Day +2 = Short 1 + LinkedIn + Facebook + GBP
    day2 = [s for s in schedule if s['day_offset'] == 2]
    platforms_day2 = {s['platform'] for s in day2}
    assert 'linkedin' in platforms_day2
    assert 'facebook' in platforms_day2
    assert 'gbp' in platforms_day2
    # Day +3 = Short 2 + X posts
    day3 = [s for s in schedule if s['day_offset'] == 3]
    platforms_day3 = {s['platform'] for s in day3}
    assert 'x' in platforms_day3


def test_append_social_log():
    """Social log is appended correctly."""
    from repurpose_content import append_social_log, SOCIAL_LOG_HEADERS

    log_path = Path('/tmp/test-social-log-write.csv')
    log_path.unlink(missing_ok=True)

    append_social_log({
        'date': '2026-03-26',
        'abbr': 'gtm',
        'topic': 'Test Topic',
        'content_type': 'blog',
        'video_status': 'uploaded',
        'shorts_count': '3',
        'platforms': 'yt,fb,ig,li,x,tt,gbp',
        'ghl_post_ids': 'p1|p2|p3',
        'cost': '$3.20',
        'notes': '7 posts scheduled',
    }, log_path)

    assert log_path.exists()
    with open(log_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]['topic'] == 'Test Topic'
    assert rows[0]['shorts_count'] == '3'

    log_path.unlink()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_repurpose_content.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'repurpose_content'`

- [ ] **Step 3: Write the implementation**

Create `src/social/repurpose_content.py`:

```python
"""Content repurposer orchestrator.

Finds published blog articles that haven't been socially distributed,
generates video + social content, and schedules everything via GoHighLevel.

Usage:
    python3 src/social/repurpose_content.py --abbr gtm
    python3 src/social/repurpose_content.py --abbr gtm --topic "Thai Massage Benefits"
    python3 src/social/repurpose_content.py --abbr gtm --status
    python3 src/social/repurpose_content.py --abbr gtm --dry-run
"""
import sys
import os
import csv
import json
import argparse
from pathlib import Path
from datetime import date, datetime, timedelta

ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT / 'src' / 'social'))
sys.path.insert(0, str(ROOT / 'src' / 'content'))
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

from social_post_generator import SocialPostGenerator, extract_content_from_html
from video_producer import VideoProducer
from ghl_publisher import GHLPublisher, get_x_format_for_date
from google_sheets import send_email

CLIENTS_DIR = ROOT / 'clients'
CONTENT_DIR = ROOT / 'content'
PUBLISH_LOG = ROOT / 'logs' / 'scheduled-publish-log.csv'
SOCIAL_LOG = ROOT / 'logs' / 'social-publish-log.csv'

SOCIAL_LOG_HEADERS = [
    'date', 'abbr', 'topic', 'content_type', 'video_status',
    'shorts_count', 'platforms', 'ghl_post_ids', 'cost', 'notes',
]

# Default schedule: day offsets from blog publish date
DEFAULT_SCHEDULE = {
    1: ['youtube_longform'],
    2: ['youtube_short_1', 'tiktok_short_1', 'facebook_reel_1', 'instagram_reel_1',
        'linkedin', 'facebook', 'gbp'],
    3: ['youtube_short_2', 'tiktok_short_2', 'facebook_reel_2', 'instagram_reel_2',
        'x'],
    4: ['youtube_short_3', 'tiktok_short_3', 'facebook_reel_3', 'instagram_reel_3',
        'instagram'],
    5: ['youtube_short_4', 'tiktok_short_4'],
    6: ['youtube_short_5', 'tiktok_short_5'],
}

PUBLISH_TIME = '10:00:00'  # default post time


def find_unprocessed_articles(abbr: str,
                               publish_log: Path = PUBLISH_LOG,
                               social_log: Path = SOCIAL_LOG) -> list[dict]:
    """Find published articles that haven't been socially processed."""
    if not publish_log.exists():
        return []

    # Read published articles
    with open(publish_log, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        published = [
            row for row in reader
            if row.get('abbr') == abbr and row.get('status') == 'published'
        ]

    # Read already-processed topics
    processed_topics = set()
    if social_log.exists():
        with open(social_log, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('abbr') == abbr:
                    processed_topics.add(row.get('topic', ''))

    return [row for row in published if row.get('topic') not in processed_topics]


def append_social_log(row: dict, log_path: Path = SOCIAL_LOG) -> None:
    """Append a row to the social publish log."""
    log_path.parent.mkdir(exist_ok=True)
    write_header = not log_path.exists()
    with open(log_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=SOCIAL_LOG_HEADERS)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, '') for k in SOCIAL_LOG_HEADERS})


def build_schedule(publish_date: date, shorts_count: int,
                   x_format: str) -> list[dict]:
    """Build a publishing schedule with day offsets and platform assignments."""
    schedule = []

    for day_offset, items in DEFAULT_SCHEDULE.items():
        scheduled_date = publish_date + timedelta(days=day_offset)
        scheduled_at = f'{scheduled_date.isoformat()}T{PUBLISH_TIME}Z'

        for item in items:
            # Skip shorts beyond what we have
            if '_short_' in item:
                short_num = int(item.split('_')[-1])
                if short_num > shorts_count:
                    continue

            # Determine platform and content type
            if item == 'youtube_longform':
                platform, content_type = 'youtube', 'longform'
            elif item.startswith('youtube_short'):
                platform, content_type = 'youtube', 'short'
            elif item.startswith('tiktok_short'):
                platform, content_type = 'tiktok', 'short'
            elif item.startswith('facebook_reel'):
                platform, content_type = 'facebook', 'reel'
            elif item.startswith('instagram_reel'):
                platform, content_type = 'instagram', 'reel'
            elif item == 'x':
                platform, content_type = 'x', x_format
            else:
                platform, content_type = item, 'post'

            schedule.append({
                'platform': platform,
                'content_type': content_type,
                'day_offset': day_offset,
                'scheduled_at': scheduled_at,
                'item_key': item,
            })

    return schedule


def load_business_config(abbr: str) -> dict:
    """Load client config.json."""
    config_path = CLIENTS_DIR / abbr.lower() / 'config.json'
    if not config_path.exists():
        raise FileNotFoundError(f'Client config not found: {config_path}')
    return json.loads(config_path.read_text())


def _find_article_dir(abbr: str, topic: str, content_type: str) -> Path | None:
    """Find the article directory for a given topic."""
    from geo_batch_runner import slugify
    slug = slugify(topic)
    type_dir = CONTENT_DIR / abbr.lower() / content_type
    if not type_dir.exists():
        return None
    # Look for matching directory
    for d in sorted(type_dir.iterdir(), reverse=True):
        if d.is_dir() and slug in d.name:
            return d
    return None


def _process_article(abbr: str, article: dict, config: dict,
                     dry_run: bool = False) -> dict:
    """Process a single article through the full pipeline."""
    topic = article['topic']
    content_type = article.get('content_type', 'blog')
    total_cost = 0.0

    print(f'\n→ Repurposing [{content_type}]: {topic}')

    # 1. Find article directory and HTML
    article_dir = _find_article_dir(abbr, topic, content_type)
    if not article_dir:
        print(f'  ✗ Article directory not found for: {topic}')
        return {'status': 'failed', 'cost': 0, 'notes': 'Article directory not found'}

    html_files = list(article_dir.glob('*.html'))
    if not html_files:
        print(f'  ✗ No HTML file found in: {article_dir}')
        return {'status': 'failed', 'cost': 0, 'notes': 'No HTML file found'}

    html_content = html_files[0].read_text(encoding='utf-8')

    # 2. Build metadata
    post_url = article.get('notes', '')  # edit URL from publish log
    metadata = {
        'title': topic,
        'post_url': post_url.replace('/wp-admin/post.php?post=', '/').replace('&action=edit', '/') if post_url else '',
        'booking_url': config.get('booking_url', ''),
        'business_name': config.get('name', ''),
        'abbreviation': abbr.upper(),
        'content_type': content_type,
    }

    # 3. Generate social posts + video script
    print(f'  → Generating social content + video script...')
    generator = SocialPostGenerator()
    result, gen_cost = generator.generate(html_content, metadata)
    total_cost += gen_cost
    print(f'    → Content generated (${gen_cost:.4f})')

    video_script = result['video_script']
    social_posts = result['social_posts']

    # Save outputs
    social_dir = article_dir / 'social'
    social_dir.mkdir(exist_ok=True)
    (social_dir / 'social-posts.json').write_text(
        json.dumps(social_posts, indent=2), encoding='utf-8')

    # Save video script as markdown for human review
    script_lines = [f'# Video Script: {video_script["title"]}\n']
    for scene in video_script.get('scenes', []):
        script_lines.append(f'\n## Scene {scene["scene_number"]} ({scene["visual_type"]}, {scene["duration_hint"]})')
        script_lines.append(f'**Visual:** {scene["visual_description"]}')
        if scene.get('text_overlay'):
            script_lines.append(f'**Text overlay:** {scene["text_overlay"]}')
        script_lines.append(f'\n> {scene["narration"]}\n')
    (social_dir / 'video-script.md').write_text('\n'.join(script_lines), encoding='utf-8')

    # 4. Produce video
    video_dir = article_dir / 'video'
    voice_id = config.get('elevenlabs', {}).get('voice_id', '')
    if not voice_id:
        print(f'  ⚠ No voice_id in config — skipping video production')
        video_result = None
        video_cost = 0.0
    else:
        print(f'  → Producing video...')
        producer = VideoProducer(voice_id=voice_id)
        video_result, video_cost = producer.produce(
            script=video_script,
            article_dir=article_dir,
            video_dir=video_dir,
            logo_url=config.get('schema', {}).get('logo_url'),
        )
        total_cost += video_cost
        print(f'    → Video produced (${video_cost:.4f})')

    # 5. Schedule via GHL
    ghl_post_ids = []
    platforms_used = set()

    if dry_run:
        print(f'  → Dry run — skipping GHL publishing')
    else:
        ghl_config = config.get('ghl', {})
        if not ghl_config.get('location_id'):
            print(f'  ⚠ No GHL config — skipping social publishing')
        else:
            print(f'  → Scheduling via GoHighLevel...')
            client_dir = CLIENTS_DIR / abbr.lower()
            publisher = GHLPublisher.from_config(ghl_config, client_dir)
            accounts = ghl_config.get('accounts', {})

            # Determine schedule
            publish_date = date.fromisoformat(article.get('date', date.today().isoformat()))
            x_format = get_x_format_for_date(publish_date)
            shorts_count = len(video_script.get('shorts', []))
            schedule = build_schedule(publish_date, shorts_count, x_format)

            # Upload media first
            media_urls = {}
            banner_path = None
            for f in article_dir.iterdir():
                if 'banner' in f.name.lower() and f.suffix.lower() in ('.jpg', '.jpeg', '.png'):
                    banner_path = f
                    break

            if banner_path:
                print(f'    → Uploading banner image...')
                media_urls['banner'] = publisher.upload_media(banner_path)

            if video_result:
                if video_result.get('longform_path') and video_result['longform_path'].exists():
                    print(f'    → Uploading long-form video...')
                    media_urls['longform'] = publisher.upload_media(video_result['longform_path'])

                if video_result.get('thumbnail_path') and video_result['thumbnail_path'].exists():
                    media_urls['thumbnail'] = publisher.upload_media(video_result['thumbnail_path'])

                for i, short_path in enumerate(video_result.get('shorts_paths', []), 1):
                    if short_path.exists():
                        print(f'    → Uploading short {i}...')
                        media_urls[f'short_{i}'] = publisher.upload_media(short_path)

            # Create scheduled posts
            for entry in schedule:
                platform = entry['platform']
                account_id = accounts.get(platform, '')
                if not account_id:
                    continue

                try:
                    post_id = _schedule_post(
                        publisher, entry, social_posts, video_script,
                        media_urls, account_id, x_format,
                    )
                    if post_id:
                        ghl_post_ids.append(post_id)
                        platforms_used.add(platform)
                        print(f'    → Scheduled {platform}/{entry["content_type"]} for {entry["scheduled_at"][:10]}')
                except Exception as e:
                    print(f'    ✗ Failed to schedule {platform}: {e}')

    # 6. Log and return
    status = 'scheduled' if ghl_post_ids else ('dry_run' if dry_run else 'generated')
    shorts_count = len(video_script.get('shorts', []))
    platforms_str = ','.join(sorted(platforms_used))

    return {
        'status': status,
        'cost': total_cost,
        'shorts_count': shorts_count,
        'platforms': platforms_str,
        'ghl_post_ids': '|'.join(ghl_post_ids),
        'notes': f'{len(ghl_post_ids)} posts scheduled' if ghl_post_ids else '',
    }


def _schedule_post(publisher: 'GHLPublisher', entry: dict,
                   social_posts: dict, video_script: dict,
                   media_urls: dict, account_id: str,
                   x_format: str) -> str | None:
    """Schedule a single post via GHL. Returns post ID."""
    platform = entry['platform']
    content_type = entry['content_type']
    scheduled_at = entry['scheduled_at']

    if platform == 'youtube' and content_type == 'longform':
        video_url = media_urls.get('longform')
        if not video_url:
            return None
        return publisher.schedule_youtube_video(
            account_id=account_id,
            video_url=video_url,
            title=video_script['title'],
            description=video_script['description'],
            tags=video_script.get('tags', []),
            thumbnail_url=media_urls.get('thumbnail'),
            scheduled_at=scheduled_at,
        )

    if content_type == 'short' or content_type == 'reel':
        # Find which short number from the item key
        item_key = entry.get('item_key', '')
        short_num = 1
        if '_short_' in item_key:
            try:
                short_num = int(item_key.split('_')[-1])
            except ValueError:
                pass
        video_url = media_urls.get(f'short_{short_num}')
        if not video_url:
            return None

        short_data = None
        for s in video_script.get('shorts', []):
            if s['short_number'] == short_num:
                short_data = s
                break

        title = short_data['hook'] if short_data else f'Short #{short_num}'

        if platform == 'youtube':
            return publisher.schedule_youtube_short(
                account_id=account_id,
                video_url=video_url,
                title=title,
                description=video_script.get('description', ''),
                scheduled_at=scheduled_at,
            )
        else:
            # TikTok, FB Reel, IG Reel
            return publisher.create_post(
                account_id=account_id,
                text=title,
                media_urls=[video_url],
                scheduled_at=scheduled_at,
            )

    # Text-based social posts
    if platform == 'linkedin':
        post = social_posts.get('linkedin', {})
        text = post.get('text', '')
        if post.get('hashtags'):
            text += '\n\n' + ' '.join(post['hashtags'])
        banner_url = media_urls.get('banner')
        return publisher.create_post(
            account_id=account_id,
            text=text,
            media_urls=[banner_url] if banner_url else None,
            scheduled_at=scheduled_at,
        )

    if platform == 'facebook' and content_type == 'post':
        post = social_posts.get('facebook', {})
        text = post.get('text', '')
        if post.get('hashtags'):
            text += '\n\n' + ' '.join(post['hashtags'])
        banner_url = media_urls.get('banner')
        return publisher.create_post(
            account_id=account_id,
            text=text,
            media_urls=[banner_url] if banner_url else None,
            scheduled_at=scheduled_at,
        )

    if platform == 'instagram' and content_type == 'post':
        post = social_posts.get('instagram', {})
        caption = post.get('caption', '')
        if post.get('hashtags'):
            caption += '\n\n' + ' '.join(post['hashtags'])
        banner_url = media_urls.get('banner')
        return publisher.create_post(
            account_id=account_id,
            text=caption,
            media_urls=[banner_url] if banner_url else None,
            scheduled_at=scheduled_at,
        )

    if platform == 'gbp':
        post = social_posts.get('gbp', {})
        banner_url = media_urls.get('banner')
        return publisher.create_post(
            account_id=account_id,
            text=post.get('text', ''),
            media_urls=[banner_url] if banner_url else None,
            scheduled_at=scheduled_at,
            platform_details={'gbp': {
                'ctaType': post.get('cta_type', 'BOOK'),
                'ctaUrl': post.get('cta_url', ''),
            }},
        )

    if platform == 'x':
        if x_format == 'thread':
            tweets = social_posts.get('x_thread', [])
            if tweets:
                banner_url = media_urls.get('banner')
                first_media = [banner_url] if banner_url and tweets[0].get('media') == 'banner' else None
                return publisher.create_post(
                    account_id=account_id,
                    text=tweets[0].get('text', ''),
                    media_urls=first_media,
                    scheduled_at=scheduled_at,
                )
        else:
            tweets = social_posts.get('x_standalone', [])
            if tweets:
                return publisher.create_post(
                    account_id=account_id,
                    text=tweets[0].get('text', ''),
                    scheduled_at=scheduled_at,
                )

    return None


def show_status(abbr: str) -> None:
    """Show social publishing status for a client."""
    print(f'\n→ Social publishing status: {abbr.upper()}\n')

    if not SOCIAL_LOG.exists():
        print('  No social publish log found.')
        return

    with open(SOCIAL_LOG, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get('abbr') == abbr]

    if not rows:
        print(f'  No entries for {abbr.upper()}.')
        return

    print(f'  {"Date":<12} {"Topic":<40} {"Video":<12} {"Shorts":<8} {"Platforms":<25} {"Cost":<10}')
    print(f'  {"─" * 12} {"─" * 40} {"─" * 12} {"─" * 8} {"─" * 25} {"─" * 10}')
    for row in rows:
        print(f'  {row.get("date", ""):<12} {row.get("topic", "")[:39]:<40} '
              f'{row.get("video_status", ""):<12} {row.get("shorts_count", ""):<8} '
              f'{row.get("platforms", ""):<25} {row.get("cost", ""):<10}')

    # Check for unprocessed articles
    unprocessed = find_unprocessed_articles(abbr)
    if unprocessed:
        print(f'\n  {len(unprocessed)} article(s) awaiting social processing:')
        for a in unprocessed:
            print(f'    · {a["topic"]} ({a["content_type"]})')


def run(abbr: str, topic: str | None = None, dry_run: bool = False) -> None:
    """Run the content repurposing pipeline."""
    print(f'\n→ Content repurposer: {abbr.upper()}  [{datetime.now().strftime("%Y-%m-%d %H:%M")}]')

    config = load_business_config(abbr)

    # Find articles to process
    if topic:
        articles = [{'topic': topic, 'content_type': 'blog', 'date': date.today().isoformat()}]
    else:
        articles = find_unprocessed_articles(abbr)

    if not articles:
        print('  No unprocessed articles found.')
        return

    print(f'  {len(articles)} article(s) to process')

    for article in articles:
        result = _process_article(abbr, article, config, dry_run=dry_run)

        # Log
        append_social_log({
            'date': date.today().isoformat(),
            'abbr': abbr,
            'topic': article['topic'],
            'content_type': article.get('content_type', 'blog'),
            'video_status': 'uploaded' if result.get('status') == 'scheduled' else result.get('status', ''),
            'shorts_count': str(result.get('shorts_count', 0)),
            'platforms': result.get('platforms', ''),
            'ghl_post_ids': result.get('ghl_post_ids', ''),
            'cost': f'${result["cost"]:.4f}' if result.get('cost') else '',
            'notes': result.get('notes', ''),
        })

        # Print summary
        status_icon = '✓' if result['status'] in ('scheduled', 'dry_run', 'generated') else '✗'
        print(f'\n{status_icon} {article["topic"]}: {result["status"]} '
              f'(${result.get("cost", 0):.4f})')

        # Email notification
        if result['status'] == 'scheduled' and not dry_run:
            _email_success(abbr, article['topic'], article.get('content_type', 'blog'), result)
        elif result['status'] == 'failed':
            _email_failure(abbr, article['topic'], result.get('notes', ''))


def _email_success(abbr: str, topic: str, content_type: str, result: dict) -> None:
    """Send success email notification."""
    subject = f'[{abbr.upper()}] Social content scheduled: {topic}'
    lines = [
        f'Social content scheduled — {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        '',
        f'Client:       {abbr.upper()}',
        f'Topic:        {topic}',
        f'Type:         {content_type}',
        f'Shorts:       {result.get("shorts_count", 0)}',
        f'Platforms:    {result.get("platforms", "")}',
        f'GHL posts:    {len(result.get("ghl_post_ids", "").split("|"))} scheduled',
        f'Cost:         ${result.get("cost", 0):.4f}',
    ]
    try:
        send_email(subject, '\n'.join(lines))
    except Exception as e:
        print(f'    → Email skipped: {e}')


def _email_failure(abbr: str, topic: str, error: str) -> None:
    """Send failure email notification."""
    subject = f'[{abbr.upper()}] Social repurposing FAILED: {topic}'
    lines = [
        f'Social repurposing failed — {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        '',
        f'Client:  {abbr.upper()}',
        f'Topic:   {topic}',
        f'Error:   {error}',
    ]
    try:
        send_email(subject, '\n'.join(lines))
    except Exception as e:
        print(f'    → Email skipped: {e}')


def main():
    parser = argparse.ArgumentParser(description='Repurpose published blog articles into video + social content')
    parser.add_argument('--abbr', required=True, help='Client abbreviation e.g. gtm')
    parser.add_argument('--topic', help='Process a specific topic (otherwise processes all unprocessed)')
    parser.add_argument('--dry-run', action='store_true', help='Generate content but skip GHL publishing')
    parser.add_argument('--status', action='store_true', help='Show social publishing status')
    args = parser.parse_args()

    if args.status:
        show_status(args.abbr)
    else:
        run(args.abbr, topic=args.topic, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_repurpose_content.py -v`

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/social/repurpose_content.py tests/test_repurpose_content.py
git commit -m "feat: add content repurposer orchestrator with GHL scheduling"
```

---

## Task 7: Client config extension

**Files:**
- Modify: `clients/gtm/config.json`
- Modify: `clients/sdy/config.json`

Add the `ghl` and `elevenlabs` blocks to each client config. These will have placeholder values until the user completes the API onboarding.

- [ ] **Step 1: Add GHL and ElevenLabs blocks to GTM config**

Read `clients/gtm/config.json`, then add these blocks at the top level:

```json
{
  "elevenlabs": {
    "voice_id": ""
  },
  "ghl": {
    "location_id": "",
    "accounts": {
      "youtube": "",
      "facebook": "",
      "instagram": "",
      "linkedin": "",
      "x": "",
      "tiktok": "",
      "gbp": ""
    }
  }
}
```

- [ ] **Step 2: Add same blocks to SDY config**

Read `clients/sdy/config.json`, then add the same `elevenlabs` and `ghl` blocks.

- [ ] **Step 3: Commit**

```bash
git add clients/gtm/config.json clients/sdy/config.json
git commit -m "feat: add GHL and ElevenLabs config placeholders for GTM and SDY"
```

---

## Task 8: Update .env with actual keys and integration test

**Files:**
- Modify: `.env` (local only, not committed)

This task is manual — the user needs to:

- [ ] **Step 1: Add ElevenLabs API key to .env**

```bash
ELEVENLABS_API_KEY=your_actual_key_here
```

- [ ] **Step 2: Add GHL OAuth credentials to .env**

```bash
GHL_CLIENT_ID=your_client_id
GHL_CLIENT_SECRET=your_client_secret
```

- [ ] **Step 3: Run GHL OAuth flow to get initial tokens**

This is a one-time manual step per client. The user needs to:
1. Create a GHL Marketplace app (or use an existing one)
2. Complete the OAuth authorization flow to get initial access/refresh tokens
3. Save tokens to `clients/gtm/ghl-tokens.json`:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_at": 1234567890
}
```

- [ ] **Step 4: Get GHL account IDs**

Run a quick script to list connected accounts:

```bash
python3 -c "
import sys; sys.path.insert(0, 'data_sources/modules')
from ghl_publisher import GHLPublisher
from pathlib import Path
pub = GHLPublisher(location_id='YOUR_LOCATION_ID', tokens_path=Path('clients/gtm/ghl-tokens.json'))
for acc in pub.get_accounts():
    print(f'{acc.get(\"platform\", \"?\"): <15} {acc.get(\"id\", \"\")}')
"
```

Copy account IDs into `clients/gtm/config.json` under `ghl.accounts`.

- [ ] **Step 5: Choose and set ElevenLabs voice ID**

Browse ElevenLabs voice library, choose a voice, add the `voice_id` to `clients/gtm/config.json` under `elevenlabs.voice_id`.

- [ ] **Step 6: Run end-to-end dry run**

```bash
python3 src/social/repurpose_content.py --abbr gtm --topic "Thai Massage Benefits" --dry-run
```

Expected output:
```
→ Content repurposer: GTM  [2026-03-26 14:00]
  1 article(s) to process

→ Repurposing [blog]: Thai Massage Benefits
  → Generating social content + video script...
    → Content generated ($0.1500)
  → Producing video...
  → Generating voiceover (8000 chars)...
    → TTS done ($2.4000)
    → Captions: thai-massage-benefits-captions.srt
  → Composing long-form video (8 scenes)...
    → Long-form: thai-massage-benefits-longform.mp4
    → Thumbnail: thai-massage-benefits-thumbnail.jpg
    → Short 1: short-1-did-you-know.mp4
    → Short 2: short-2-myth-bust.mp4
    → Short 3: short-3-faq-answer.mp4
    → Video produced ($2.4000)
  → Dry run — skipping GHL publishing

✓ Thai Massage Benefits: dry_run ($2.5500)
```

- [ ] **Step 7: Run full pipeline (with GHL publishing)**

```bash
python3 src/social/repurpose_content.py --abbr gtm --topic "Thai Massage Benefits"
```

Verify in GHL Social Planner that posts appear in the calendar for the week.

- [ ] **Step 8: Commit any config updates**

```bash
git add clients/gtm/config.json clients/sdy/config.json
git commit -m "feat: populate GHL and ElevenLabs config for GTM"
```

---

## Task 9: Run all tests and final verification

- [ ] **Step 1: Run full test suite**

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine" && python3 -m pytest tests/test_elevenlabs_tts.py tests/test_ghl_publisher.py tests/test_social_post_generator.py tests/test_video_producer.py tests/test_repurpose_content.py -v
```

Expected: All tests PASS

- [ ] **Step 2: Verify status command**

```bash
python3 src/social/repurpose_content.py --abbr gtm --status
```

Expected: Shows status table (or "No entries" if no articles processed yet)

- [ ] **Step 3: Verify file structure**

```bash
ls -la src/social/
ls -la data_sources/modules/elevenlabs_tts.py data_sources/modules/ghl_publisher.py
ls -la tests/test_elevenlabs_tts.py tests/test_ghl_publisher.py tests/test_social_post_generator.py tests/test_video_producer.py tests/test_repurpose_content.py
```

Expected: All files exist

- [ ] **Step 4: Final commit if any changes**

```bash
git status
# If clean, skip. Otherwise:
git add -A && git commit -m "chore: final cleanup for content repurposing pipeline"
```
