"""Unit tests for GoHighLevel Social Planner publisher."""
import sys
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'data_sources' / 'modules'))


def test_constructor_sets_bearer_token():
    """Constructor sets Authorization header from token."""
    from ghl_publisher import GHLPublisher

    with patch('ghl_publisher.requests.Session') as MockSession:
        pub = GHLPublisher(location_id='loc123', api_token='test-token-abc')
        assert pub._access_token == 'test-token-abc'
        assert pub._location_id == 'loc123'


def test_create_post_calls_correct_endpoint():
    """create_post hits /social-media-posting/{locationId}/posts."""
    from ghl_publisher import GHLPublisher

    with patch('ghl_publisher.requests.Session') as MockSession:
        mock_session = MockSession.return_value
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'id': 'post-123', 'status': 'scheduled'}
        mock_resp.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_resp

        pub = GHLPublisher(location_id='loc123', api_token='test-token')

        post_id = pub.create_post(
            account_id='acc-yt-1',
            text='Test post content',
            scheduled_at='2026-04-01T10:00:00Z',
        )

        assert post_id == 'post-123'
        call_args = mock_session.post.call_args
        assert 'social-media-posting/loc123/posts' in call_args[0][0]


def test_upload_media_returns_url():
    """upload_media uploads file and returns hosted URL."""
    from ghl_publisher import GHLPublisher

    with patch('ghl_publisher.requests.Session') as MockSession:
        mock_session = MockSession.return_value
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'url': 'https://storage.ghl.com/media/abc.jpg'}
        mock_resp.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_resp

        pub = GHLPublisher(location_id='loc123', api_token='test-token')

        dummy = Path('/tmp/test-upload.jpg')
        dummy.write_bytes(b'\xff\xd8\xff\xe0' * 10)

        url = pub.upload_media(dummy)
        assert url == 'https://storage.ghl.com/media/abc.jpg'

        dummy.unlink(missing_ok=True)


def test_from_config_reads_token_file():
    """from_config reads token from ghl-tokens.json."""
    from ghl_publisher import GHLPublisher

    token_dir = Path('/tmp/test-ghl-client')
    token_dir.mkdir(exist_ok=True)
    token_file = token_dir / 'ghl-tokens.json'
    token_file.write_text(json.dumps({'token': 'file-token-xyz'}))

    with patch('ghl_publisher.requests.Session'):
        pub = GHLPublisher.from_config(
            {'location_id': 'loc456'},
            client_dir=token_dir,
        )
        assert pub._access_token == 'file-token-xyz'
        assert pub._location_id == 'loc456'

    token_file.unlink()
    token_dir.rmdir()


def test_week_alternation_even_odd():
    """Even ISO weeks use thread, odd use standalone."""
    from ghl_publisher import get_x_format_for_date
    from datetime import date

    # 2026-01-05 is ISO week 2 (even) → thread
    # 2026-01-12 is ISO week 3 (odd) → standalone
    d_even = date(2026, 1, 5)
    d_odd = date(2026, 1, 12)

    assert get_x_format_for_date(d_even) == 'thread'
    assert get_x_format_for_date(d_odd) == 'standalone'
