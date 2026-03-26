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

# day_offset -> list of schedule item keys
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

PUBLISH_TIME = '10:00:00'

# Map schedule key prefixes -> (platform, content_type)
_KEY_MAP = {
    'youtube_longform': ('youtube', 'longform'),
    'youtube_short': ('youtube', 'short'),
    'tiktok_short': ('tiktok', 'short'),
    'facebook_reel': ('facebook', 'reel'),
    'instagram_reel': ('instagram', 'reel'),
    'linkedin': ('linkedin', 'post'),
    'facebook': ('facebook', 'post'),
    'instagram': ('instagram', 'post'),
    'gbp': ('gbp', 'post'),
    'x': ('x', 'post'),
}


def _key_to_platform(key: str) -> tuple[str, str]:
    """Map a schedule key to (platform, content_type)."""
    for prefix, pair in _KEY_MAP.items():
        if key == prefix or key.startswith(prefix + '_') and not prefix.endswith('_'):
            return pair
        if key == prefix:
            return pair
    # fallback: strip trailing _N
    base = '_'.join(key.split('_')[:-1]) if key[-1].isdigit() else key
    return _KEY_MAP.get(base, (base, 'post'))


def find_unprocessed_articles(
    abbr: str,
    publish_log: Path = PUBLISH_LOG,
    social_log: Path = SOCIAL_LOG,
) -> list[dict]:
    """Return published blog rows for abbr that haven't been socially processed.

    Reads the publish log for status=published rows matching abbr, then
    cross-references the social log to exclude already-processed topics.
    """
    if not publish_log.exists():
        return []

    # Load already-processed topics from social log
    processed: set[str] = set()
    if social_log.exists():
        with open(social_log, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if row.get('abbr', '').lower() == abbr.lower():
                    processed.add(row['topic'].strip())

    articles = []
    with open(publish_log, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('abbr', '').lower() != abbr.lower():
                continue
            if row.get('status', '').lower() != 'published':
                continue
            topic = row.get('topic', '').strip()
            if topic in processed:
                continue
            articles.append(dict(row))

    return articles


def append_social_log(row: dict, log_path: Path = SOCIAL_LOG) -> None:
    """Append a row to the social publish log, writing header if new file."""
    write_header = not log_path.exists() or log_path.stat().st_size == 0
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=SOCIAL_LOG_HEADERS)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, '') for k in SOCIAL_LOG_HEADERS})


def build_schedule(
    publish_date: date,
    shorts_count: int,
    x_format: str,
) -> list[dict]:
    """Build a flat list of schedule entries from DEFAULT_SCHEDULE.

    Each entry has: day_offset, platform, content_type, scheduled_at (ISO str),
    and short_index (for short items, 1-based; 0 for non-shorts).

    Shorts beyond shorts_count are omitted. x_format ('thread'/'standalone')
    is stored on the x entry so _schedule_post can dispatch correctly.
    """
    entries = []
    short_counters: dict[str, int] = {}  # platform -> count of shorts seen

    for day_offset, keys in sorted(DEFAULT_SCHEDULE.items()):
        scheduled_dt = datetime.combine(
            publish_date + timedelta(days=day_offset),
            datetime.strptime(PUBLISH_TIME, '%H:%M:%S').time(),
        )
        scheduled_at = scheduled_dt.strftime('%Y-%m-%dT%H:%M:%S')

        for key in keys:
            platform, content_type = _key_to_platform(key)

            # Track shorts per-platform and skip if beyond count
            if content_type in ('short', 'reel'):
                short_counters[platform] = short_counters.get(platform, 0) + 1
                if short_counters[platform] > shorts_count:
                    continue
                short_index = short_counters[platform]
            else:
                short_index = 0

            entry = {
                'key': key,
                'platform': platform,
                'content_type': content_type,
                'day_offset': day_offset,
                'scheduled_at': scheduled_at,
                'short_index': short_index,
            }
            if platform == 'x':
                entry['x_format'] = x_format

            entries.append(entry)

    return entries


def load_business_config(abbr: str) -> dict:
    """Load client config from clients/[abbr]/config.json."""
    config_path = CLIENTS_DIR / abbr.lower() / 'config.json'
    if not config_path.exists():
        raise FileNotFoundError(f'Client config not found: {config_path}')
    return json.loads(config_path.read_text(encoding='utf-8'))


def _find_article_dir(abbr: str, topic: str, content_type: str) -> Path | None:
    """Find article directory under content/[abbr]/[type]/ by topic slug match."""
    from geo_batch_runner import slugify

    slug = slugify(topic)
    base_dir = CONTENT_DIR / abbr.lower() / content_type
    if not base_dir.exists():
        return None

    # Match directories whose name starts with the slug
    for candidate in sorted(base_dir.iterdir(), reverse=True):
        if candidate.is_dir() and candidate.name.startswith(slug):
            return candidate

    return None


def _schedule_post(
    publisher: GHLPublisher,
    entry: dict,
    social_posts: dict,
    video_result: dict,
    media_urls: dict,
    account_id: str,
    x_format: str,
) -> str | None:
    """Dispatch a single GHL post for a schedule entry.

    Returns GHL post ID or None if nothing to schedule.

    media_urls keys: 'banner', 'longform_video', 'thumbnail', shorts list.
    """
    platform = entry['platform']
    content_type = entry['content_type']
    scheduled_at = entry['scheduled_at']
    short_index = entry.get('short_index', 0)

    posts = social_posts.get('social_posts', {})

    try:
        if platform == 'youtube' and content_type == 'longform':
            video_url = media_urls.get('longform_video')
            if not video_url:
                return None
            script = social_posts.get('video_script', {})
            return publisher.schedule_youtube_video(
                account_id=account_id,
                video_url=video_url,
                title=script.get('title', ''),
                description=script.get('description', ''),
                tags=script.get('tags', []),
                thumbnail_url=media_urls.get('thumbnail'),
                scheduled_at=scheduled_at,
            )

        if platform == 'youtube' and content_type == 'short':
            shorts = media_urls.get('shorts', [])
            idx = short_index - 1
            if idx >= len(shorts):
                return None
            short_data = shorts[idx]
            script = social_posts.get('video_script', {})
            shorts_scripts = script.get('shorts', [])
            short_script = shorts_scripts[idx] if idx < len(shorts_scripts) else {}
            return publisher.schedule_youtube_short(
                account_id=account_id,
                video_url=short_data['url'],
                title=short_script.get('title', f'Short {short_index}'),
                description=short_script.get('narration', '')[:500],
                scheduled_at=scheduled_at,
            )

        if platform in ('tiktok', 'facebook', 'instagram') and content_type in ('short', 'reel'):
            shorts = media_urls.get('shorts', [])
            idx = short_index - 1
            if idx >= len(shorts):
                return None
            short_data = shorts[idx]
            script = social_posts.get('video_script', {})
            shorts_scripts = script.get('shorts', [])
            short_script = shorts_scripts[idx] if idx < len(shorts_scripts) else {}
            text = short_script.get('hook', f'Short {short_index}')
            return publisher.create_post(
                account_id=account_id,
                text=text,
                media_urls=[short_data['url']],
                scheduled_at=scheduled_at,
            )

        if platform == 'linkedin':
            li = posts.get('linkedin', {})
            text = li.get('text', '')
            hashtags = li.get('hashtags', [])
            if hashtags:
                text += '\n\n' + ' '.join(f'#{h}' for h in hashtags)
            banner_url = media_urls.get('banner')
            return publisher.create_post(
                account_id=account_id,
                text=text,
                media_urls=[banner_url] if banner_url else None,
                scheduled_at=scheduled_at,
            )

        if platform == 'facebook' and content_type == 'post':
            fb = posts.get('facebook', {})
            text = fb.get('text', '')
            hashtags = fb.get('hashtags', [])
            if hashtags:
                text += '\n\n' + ' '.join(f'#{h}' for h in hashtags)
            banner_url = media_urls.get('banner')
            return publisher.create_post(
                account_id=account_id,
                text=text,
                media_urls=[banner_url] if banner_url else None,
                scheduled_at=scheduled_at,
            )

        if platform == 'instagram' and content_type == 'post':
            ig = posts.get('instagram', {})
            caption = ig.get('caption', '')
            hashtags = ig.get('hashtags', [])
            if hashtags:
                caption += '\n\n' + ' '.join(f'#{h}' for h in hashtags)
            banner_url = media_urls.get('banner')
            return publisher.create_post(
                account_id=account_id,
                text=caption,
                media_urls=[banner_url] if banner_url else None,
                scheduled_at=scheduled_at,
            )

        if platform == 'gbp':
            gbp = posts.get('gbp', {})
            text = gbp.get('text', '')
            banner_url = media_urls.get('banner')
            details = {
                'gmb': {
                    'cta_type': gbp.get('cta_type', 'BOOK'),
                    'cta_url': gbp.get('cta_url', ''),
                }
            }
            return publisher.create_post(
                account_id=account_id,
                text=text,
                media_urls=[banner_url] if banner_url else None,
                scheduled_at=scheduled_at,
                platform_details=details,
            )

        if platform == 'x':
            fmt = entry.get('x_format', x_format)
            if fmt == 'thread':
                thread = posts.get('x_thread', [])
                if not thread:
                    return None
                # Post first tweet of thread (GHL doesn't natively support threads;
                # post each tweet separately with its own scheduled_at)
                tweet = thread[0]
                text = tweet.get('text', '')
                banner_url = media_urls.get('banner') if tweet.get('media') == 'banner' else None
                return publisher.create_post(
                    account_id=account_id,
                    text=text,
                    media_urls=[banner_url] if banner_url else None,
                    scheduled_at=scheduled_at,
                )
            else:
                # Standalone: pick tweet at day_offset 0 by default
                standalone = posts.get('x_standalone', [])
                if not standalone:
                    return None
                tweet = standalone[0]
                text = tweet.get('text', '')
                return publisher.create_post(
                    account_id=account_id,
                    text=text,
                    scheduled_at=scheduled_at,
                )

    except Exception as e:
        print(f'  → GHL {platform}/{content_type}: failed — {e}')
        return None

    return None


def _process_article(
    abbr: str,
    article: dict,
    config: dict,
    dry_run: bool = False,
) -> dict:
    """Full pipeline for one article: generate → produce → schedule.

    Returns a result dict with keys: topic, video_status, shorts_count,
    platforms, ghl_post_ids, cost, notes, error.
    """
    topic = article.get('topic', '').strip()
    content_type = article.get('content_type', 'blog').strip()
    post_id = article.get('post_id', '').strip()

    print(f'\n→ Processing: {topic}')

    result = {
        'topic': topic,
        'content_type': content_type,
        'video_status': 'skipped',
        'shorts_count': '0',
        'platforms': '',
        'ghl_post_ids': '',
        'cost': '$0.0000',
        'notes': '',
        'error': None,
    }

    # Find article directory
    article_dir = _find_article_dir(abbr, topic, content_type)
    if not article_dir:
        result['error'] = f'Article directory not found for topic: {topic}'
        print(f'  → {result["error"]}')
        return result

    # Find HTML file
    html_files = list(article_dir.glob('*.html'))
    if not html_files:
        result['error'] = f'No HTML file in {article_dir}'
        print(f'  → {result["error"]}')
        return result

    html = html_files[0].read_text(encoding='utf-8')
    total_cost = 0.0

    # Build post URL from notes field (contains wp-admin URL) or config
    notes_url = article.get('notes', '')
    if post_id and config.get('wordpress', {}).get('url'):
        post_url = f"{config['wordpress']['url']}/wp-admin/post.php?post={post_id}&action=edit"
    else:
        post_url = notes_url or config.get('website', '')

    booking_url = config.get('booking_url', '')
    business_name = config.get('name', abbr)

    metadata = {
        'business_name': business_name,
        'post_url': post_url,
        'booking_url': booking_url,
    }

    # Step 1: Generate social content
    print(f'  → Generating social content...')
    generator = SocialPostGenerator()
    try:
        social_posts, gen_cost = generator.generate(html, metadata)
        total_cost += gen_cost
        print(f'  → Social content generated (${gen_cost:.4f})')
    except Exception as e:
        result['error'] = f'Social generation failed: {e}'
        print(f'  → {result["error"]}')
        return result

    video_script = social_posts.get('video_script', {})
    shorts_list = video_script.get('shorts', [])
    shorts_count = len(shorts_list)

    # Step 2: Produce video
    video_result = {'longform': None, 'thumbnail': None, 'shorts': []}
    video_status = 'skipped'

    ghl_config = config.get('ghl')
    voice_id = None
    if ghl_config:
        voice_id = ghl_config.get('voice_id')

    if voice_id and not dry_run:
        print(f'  → Producing video (voice: {voice_id})...')
        video_dir = article_dir / 'video'
        producer = VideoProducer(voice_id=voice_id)
        try:
            video_result, video_cost = producer.produce(
                script=video_script,
                article_dir=article_dir,
                video_dir=video_dir,
                logo_url=config.get('schema', {}).get('logo_url'),
            )
            total_cost += video_cost
            video_status = 'produced' if video_result.get('longform') else 'failed'
            print(f'  → Video: {video_status} (${video_cost:.4f})')
        except Exception as e:
            video_status = 'failed'
            print(f'  → Video production failed: {e}')
    else:
        if dry_run:
            print('  → Video: skipped (dry-run)')
        else:
            print('  → Video: skipped (no voice_id in ghl config)')

    result['video_status'] = video_status
    result['shorts_count'] = str(min(shorts_count, len(video_result.get('shorts', [])) or shorts_count))

    # Step 3: Upload media to GHL and schedule posts
    ghl_post_ids: list[str] = []
    platforms_used: list[str] = []

    if not ghl_config:
        print('  → GHL: skipped (no ghl config in client config.json)')
        result['notes'] = 'no ghl config'
        result['cost'] = f'${total_cost:.4f}'
        return result

    if dry_run:
        print(f'  → GHL: skipped (dry-run) — would schedule ~{len(DEFAULT_SCHEDULE)} days of posts')
        result['notes'] = 'dry-run'
        result['cost'] = f'${total_cost:.4f}'
        return result

    account_id = ghl_config.get('account_id', '')
    client_dir = CLIENTS_DIR / abbr.lower()

    try:
        publisher = GHLPublisher.from_config(ghl_config, client_dir)
    except Exception as e:
        result['error'] = f'GHL init failed: {e}'
        print(f'  → {result["error"]}')
        result['cost'] = f'${total_cost:.4f}'
        return result

    # Upload banner image
    media_urls: dict = {}
    banner_files = list(article_dir.glob('*banner*'))
    if banner_files:
        try:
            media_urls['banner'] = publisher.upload_media(banner_files[0])
            print(f'  → Uploaded banner: {media_urls["banner"]}')
        except Exception as e:
            print(f'  → Banner upload failed: {e}')

    # Upload longform video
    if video_result.get('longform') and Path(video_result['longform']).exists():
        try:
            media_urls['longform_video'] = publisher.upload_media(Path(video_result['longform']))
            video_status = 'uploaded'
            print(f'  → Uploaded longform video')
        except Exception as e:
            print(f'  → Longform video upload failed: {e}')

    # Upload thumbnail
    if video_result.get('thumbnail') and Path(video_result['thumbnail']).exists():
        try:
            media_urls['thumbnail'] = publisher.upload_media(Path(video_result['thumbnail']))
        except Exception as e:
            print(f'  → Thumbnail upload failed: {e}')

    # Upload shorts
    media_urls['shorts'] = []
    for short in video_result.get('shorts', []):
        short_file = short.get('file', '')
        if short_file and Path(short_file).exists():
            try:
                url = publisher.upload_media(Path(short_file))
                media_urls['shorts'].append({'url': url, 'title': short.get('title', '')})
            except Exception as e:
                print(f'  → Short upload failed: {e}')

    result['video_status'] = video_status

    # Determine x_format for this publish date
    try:
        pub_date = date.fromisoformat(article.get('date', str(date.today())))
    except ValueError:
        pub_date = date.today()

    x_format = get_x_format_for_date(pub_date)
    actual_shorts_count = len(media_urls['shorts']) if media_urls['shorts'] else shorts_count

    schedule = build_schedule(pub_date, shorts_count=actual_shorts_count, x_format=x_format)

    for entry in schedule:
        post_id_ghl = _schedule_post(
            publisher=publisher,
            entry=entry,
            social_posts=social_posts,
            video_result=video_result,
            media_urls=media_urls,
            account_id=account_id,
            x_format=x_format,
        )
        if post_id_ghl:
            ghl_post_ids.append(post_id_ghl)
            platform = entry['platform']
            if platform not in platforms_used:
                platforms_used.append(platform)

    result['ghl_post_ids'] = '|'.join(ghl_post_ids)
    result['platforms'] = ','.join(platforms_used)
    result['cost'] = f'${total_cost:.4f}'
    result['notes'] = f'{len(ghl_post_ids)} posts scheduled'
    print(f'  → Scheduled {len(ghl_post_ids)} posts across: {result["platforms"]}')

    return result


def show_status(abbr: str) -> None:
    """Print a formatted table of social log entries for the given client."""
    if not SOCIAL_LOG.exists():
        print(f'No social log found at {SOCIAL_LOG}')
        return

    rows = []
    with open(SOCIAL_LOG, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('abbr', '').lower() == abbr.lower():
                rows.append(row)

    if not rows:
        print(f'No social log entries for {abbr}')
        return

    print(f'\nSocial distribution log — {abbr.upper()}')
    print(f"{'Date':<12} {'Topic':<45} {'Video':<10} {'Shorts':<8} {'Platforms':<25} {'Cost':<10}")
    print('-' * 115)
    for row in rows:
        video = row.get('video_status', '')
        icon = '✓' if video == 'uploaded' else ('·' if video == 'produced' else '·')
        print(
            f"{row.get('date', ''):<12} "
            f"{row.get('topic', '')[:44]:<45} "
            f"{icon} {video:<8} "
            f"{row.get('shorts_count', '0'):<8} "
            f"{row.get('platforms', '')[:24]:<25} "
            f"{row.get('cost', ''):<10}"
        )


def _email_success(abbr: str, results: list[dict]) -> None:
    """Send success notification email."""
    lines = [f"Content repurposing complete for {abbr.upper()}\n"]
    for r in results:
        lines.append(f"  ✓ {r['topic']}")
        lines.append(f"    Video: {r['video_status']} | Shorts: {r['shorts_count']} | Platforms: {r['platforms']}")
        lines.append(f"    Posts scheduled: {len(r['ghl_post_ids'].split('|')) if r['ghl_post_ids'] else 0} | Cost: {r['cost']}")
    try:
        send_email(
            subject=f'[SEOMachine] Social repurposing complete — {abbr.upper()}',
            body='\n'.join(lines),
        )
    except Exception as e:
        print(f'  → Email failed: {e}')


def _email_failure(abbr: str, topic: str, error: str) -> None:
    """Send failure notification email."""
    body = f'Content repurposing failed for {abbr.upper()}\n\nTopic: {topic}\nError: {error}'
    try:
        send_email(
            subject=f'[SEOMachine] Social repurposing FAILED — {abbr.upper()}',
            body=body,
        )
    except Exception as e:
        print(f'  → Email failed: {e}')


def run(abbr: str, topic: str | None = None, dry_run: bool = False) -> None:
    """Main run loop: find unprocessed articles, process each, log results."""
    print(f'\n→ Content repurposer — {abbr.upper()}' + (' [dry-run]' if dry_run else ''))

    config = load_business_config(abbr)

    if topic:
        # Build a synthetic article row for a specific topic
        articles = [{'topic': topic, 'content_type': 'blog', 'date': str(date.today()),
                     'post_id': '', 'notes': ''}]
        # Try to find it in the publish log for richer metadata
        candidates = find_unprocessed_articles(abbr)
        for a in candidates:
            if a['topic'].lower() == topic.lower():
                articles = [a]
                break
    else:
        articles = find_unprocessed_articles(abbr)
        if not articles:
            print(f'  → No unprocessed articles found for {abbr.upper()}')
            return

    print(f'  → Found {len(articles)} article(s) to process')

    success_results = []
    for article in articles:
        result = _process_article(abbr, article, config, dry_run=dry_run)

        if result.get('error'):
            _email_failure(abbr, result['topic'], result['error'])
        else:
            success_results.append(result)

        # Log to social CSV regardless of outcome
        if not dry_run:
            append_social_log({
                'date': str(date.today()),
                'abbr': abbr,
                'topic': result['topic'],
                'content_type': result['content_type'],
                'video_status': result['video_status'],
                'shorts_count': result['shorts_count'],
                'platforms': result['platforms'],
                'ghl_post_ids': result['ghl_post_ids'],
                'cost': result['cost'],
                'notes': result.get('error') or result.get('notes', ''),
            })

        cost_str = result.get('cost', '$0.0000')
        status = '✗' if result.get('error') else '✓'
        print(f'  {status} {result["topic"]} — {cost_str}')

    if success_results and not dry_run:
        _email_success(abbr, success_results)


def main() -> None:
    parser = argparse.ArgumentParser(description='Content repurposer orchestrator')
    parser.add_argument('--abbr', required=True, help='Client abbreviation (e.g. gtm)')
    parser.add_argument('--topic', default=None, help='Process a specific topic only')
    parser.add_argument('--status', action='store_true', help='Show social log status table')
    parser.add_argument('--dry-run', action='store_true', help='Generate content but skip GHL scheduling')
    args = parser.parse_args()

    if args.status:
        show_status(args.abbr)
        return

    run(abbr=args.abbr, topic=args.topic, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
