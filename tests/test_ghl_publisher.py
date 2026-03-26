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
        'expires_at': 0,
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

    d_odd = date(2026, 1, 5)   # ISO week 1
    d_even = date(2026, 1, 12)  # ISO week 2

    assert get_x_format_for_date(d_odd) == 'standalone'
    assert get_x_format_for_date(d_even) == 'thread'
