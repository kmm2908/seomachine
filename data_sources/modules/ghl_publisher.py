"""GoHighLevel Social Planner API client.

Uses Private Integration tokens (static Bearer tokens) for authentication.
Handles media upload and post scheduling across all social platforms
via the GHL Social Planner API.
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
REQUEST_DELAY = 0.15


def get_x_format_for_date(d: date) -> str:
    """Return 'thread' for even ISO weeks, 'standalone' for odd."""
    iso_week = d.isocalendar()[1]
    return 'thread' if iso_week % 2 == 0 else 'standalone'


class GHLPublisher:
    """GoHighLevel Social Planner API client using Private Integration tokens."""

    def __init__(self, location_id: str, api_token: str):
        self._location_id = location_id
        self._access_token = api_token

        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'Version': '2021-07-28',
            'Authorization': f'Bearer {api_token}',
            'User-Agent': 'SEOMachine/1.0 (Social Publisher)',
        })

    @classmethod
    def from_config(cls, ghl_config: dict, client_dir: Path) -> 'GHLPublisher':
        """Create from client config dict.
        Reads token from clients/[abbr]/ghl-tokens.json (single line, gitignored).
        """
        token_path = client_dir / 'ghl-tokens.json'
        if not token_path.exists():
            raise FileNotFoundError(
                f'GHL token not found at {token_path}. '
                f'Create a Private Integration token in GHL Settings > Private Integrations, '
                f'then save it as {{"token": "YOUR_TOKEN"}} in {token_path}'
            )
        token_data = json.loads(token_path.read_text())
        return cls(
            location_id=ghl_config['location_id'],
            api_token=token_data['token'],
        )

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
