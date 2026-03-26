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
REQUEST_DELAY = 0.15


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
        """Create from client config dict."""
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

        if time.time() >= expires_at - 300:
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

        headers = {k: v for k, v in self._session.headers.items()
                   if k.lower() != 'content-type'}

        with open(file_path, 'rb') as f:
            resp = self._session.post(
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
