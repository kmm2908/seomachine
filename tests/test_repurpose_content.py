"""Unit tests for content repurposer orchestrator."""
import sys
import csv
import json
from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src' / 'social'))


def test_find_unprocessed_articles():
    """Finds articles in publish log that haven't been socially processed."""
    from repurpose_content import find_unprocessed_articles

    publish_log = Path('/tmp/test-publish-log.csv')
    with open(publish_log, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'abbr', 'topic', 'content_type', 'status', 'post_id', 'cost', 'notes'])
        writer.writeheader()
        writer.writerow({'date': '2026-03-25', 'abbr': 'gtm', 'topic': 'Thai Massage Benefits', 'content_type': 'blog', 'status': 'published', 'post_id': '123', 'cost': '$0.40', 'notes': 'https://example.com/wp-admin/post.php?post=123'})
        writer.writerow({'date': '2026-03-25', 'abbr': 'gtm', 'topic': 'Already Processed', 'content_type': 'blog', 'status': 'published', 'post_id': '124', 'cost': '$0.40', 'notes': ''})
        writer.writerow({'date': '2026-03-25', 'abbr': 'sdy', 'topic': 'Failed Post', 'content_type': 'blog', 'status': 'failed', 'post_id': '', 'cost': '', 'notes': ''})

    social_log = Path('/tmp/test-social-log.csv')
    with open(social_log, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'abbr', 'topic', 'content_type', 'video_status', 'shorts_count', 'platforms', 'ghl_post_ids', 'cost', 'notes'])
        writer.writeheader()
        writer.writerow({'date': '2026-03-25', 'abbr': 'gtm', 'topic': 'Already Processed', 'content_type': 'blog', 'video_status': 'uploaded', 'shorts_count': '3', 'platforms': 'yt,fb', 'ghl_post_ids': 'p1|p2', 'cost': '$3.20', 'notes': ''})

    articles = find_unprocessed_articles('gtm', publish_log, social_log)

    assert len(articles) == 1
    assert articles[0]['topic'] == 'Thai Massage Benefits'

    publish_log.unlink()
    social_log.unlink()


def test_build_schedule_offsets():
    """Schedule assigns correct day offsets for each platform."""
    from repurpose_content import build_schedule

    publish_date = date(2026, 3, 30)  # Monday
    schedule = build_schedule(publish_date, shorts_count=3, x_format='standalone')

    assert any(s['platform'] == 'youtube' and s['content_type'] == 'longform'
               for s in schedule if s['day_offset'] == 1)
    day2 = [s for s in schedule if s['day_offset'] == 2]
    platforms_day2 = {s['platform'] for s in day2}
    assert 'linkedin' in platforms_day2
    assert 'facebook' in platforms_day2
    assert 'gbp' in platforms_day2
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
