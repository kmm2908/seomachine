# Content Repurposing Pipeline — Design Spec

**Date:** 2026-03-26
**Status:** Draft

---

## Context

SEO Machine currently generates blog articles and publishes them to WordPress. The content dies there — no video, no social media, no cross-platform distribution. Each blog post contains well-researched, entity-rich content that could reach a much wider audience if repurposed into video and social media formats.

This spec defines a fully automated pipeline that takes each published blog article and:
1. Creates a long-form narrated video (8-12 minutes) for YouTube
2. Extracts 3-5 short-form clips (20-45 seconds) for YouTube Shorts, TikTok, Facebook Reels, and Instagram Reels
3. Generates platform-specific social media posts for LinkedIn, Facebook, X, Instagram, and GBP
4. Publishes everything automatically via the GoHighLevel Social Planner API on a staggered weekly schedule

### Why GoHighLevel

All clients already have GoHighLevel accounts with social media channels connected. GHL's Social Planner API (`POST /social-media-posting/{locationId}/posts`) supports all target platforms including YouTube video upload, scheduling, and media handling — replacing what would otherwise be 6+ separate OAuth integrations. One API, one auth flow, one publisher module.

### Future: HeyGen Avatar

The video pipeline is designed with a clean TTS interface so that ElevenLabs voiceover can be swapped for HeyGen AI avatar videos once avatars are created for each client. No architectural changes needed — just a different video producer implementation behind the same interface.

---

## System Architecture

### Two-Stage Pipeline

```
Stage 1: Blog Pipeline (existing, unchanged)
  publish_scheduled.py → WordPress draft → log + email

Stage 2: Social Pipeline (new)
  repurpose_content.py → generates all content + video → schedules via GHL API
```

Stage 2 runs via cron ~2 hours after the blog publish window. It picks up any newly published articles from `logs/scheduled-publish-log.csv` that haven't been repurposed yet.

### New Files

```
src/social/
  repurpose_content.py      # Orchestrator CLI: reads published articles, generates all assets, schedules via GHL
  video_producer.py         # TTS + FFmpeg video composition (long-form + shorts)
  social_post_generator.py  # Claude-powered social copy + video script generation

data_sources/modules/
  ghl_publisher.py          # GoHighLevel Social Planner API client
  elevenlabs_tts.py         # ElevenLabs text-to-speech wrapper
```

### Output Structure

```
content/[abbr]/[type]/[slug]-[date]/
  [slug]-[date].html              # Existing blog article
  [slug]-banner.jpg               # Existing banner image
  social/
    video-script.md               # Full narration script with short segment markers
    social-posts.json             # All platform posts (text, hashtags, media refs)
    social-queue.json             # Scheduled publish queue with dates
  video/
    [slug]-voiceover.mp3          # ElevenLabs TTS audio
    [slug]-longform.mp4           # Composed long-form video (8-12 min)
    [slug]-thumbnail.jpg          # YouTube thumbnail
    [slug]-captions.srt           # Burned-in captions source
    shorts/
      short-1-[hook].mp4          # 20-45s clips
      short-2-[hook].mp4
      short-3-[hook].mp4
```

---

## Component 1: Content Repurposer (Orchestrator)

**File:** `src/social/repurpose_content.py`

### Trigger

Cron job, runs ~2 hours after blog publish window. Checks `logs/scheduled-publish-log.csv` for rows with status `published` that don't have a corresponding entry in `logs/social-publish-log.csv`.

Note: only `publish_scheduled.py` writes to this log. Articles published via `geo_batch_runner.py` (Google Sheets path) are tracked differently — the repurposer could also scan `content/[abbr]/` directories for HTML files with no matching social log entry as a fallback. This ensures both publishing paths feed the social pipeline.

### Flow

```
1. Find unprocesed published articles from log
2. For each article:
   a. Read HTML content from disk
   b. Extract: title, body text, FAQ questions, images, post URL, metadata
   c. Call social_post_generator.py → video script + social posts
   d. Call video_producer.py → long-form video + shorts
   e. Call publish_social.py → schedule everything via GHL
   f. Log to social-publish-log.csv
   g. Send summary email
```

### Tracking

New log file: `logs/social-publish-log.csv`
Fields: `date, abbr, topic, content_type, video_status, social_status, ghl_post_ids, cost, notes`

The repurposer marks articles as processed to prevent duplicate runs.

---

## Component 2: Social Post Generator

**File:** `src/social/social_post_generator.py`

Uses Claude API to generate all text content in a single call. Input: blog HTML + metadata. Output: structured JSON.

### Video Script Generation

Claude generates a narration script structured as scenes:

```json
{
  "title": "Video title for YouTube",
  "description": "YouTube description with keywords and links",
  "tags": ["thai massage", "glasgow", ...],
  "thumbnail_text": "Short text for thumbnail overlay",
  "scenes": [
    {
      "scene_number": 1,
      "narration": "Full narration text for this scene",
      "visual_type": "ken_burns | slide | text_overlay | mixed",
      "visual_description": "What to show — image prompt or text content",
      "duration_hint": "15s",
      "source_image": "banner.jpg or null",
      "text_overlay": "Key point text shown on screen (optional)"
    }
  ],
  "shorts": [
    {
      "short_number": 1,
      "type": "myth_bust | faq_answer | quick_tip | surprising_fact | cta",
      "hook": "Opening line (first 3 seconds)",
      "narration": "Full short narration",
      "visual_type": "slide | text_overlay | ken_burns",
      "text_overlays": ["Line 1", "Line 2", "Line 3"],
      "duration_target": "30s",
      "source_scenes": [3, 4]
    }
  ]
}
```

The script targets 8-12 minutes for long-form based on YouTube research:
- 8+ minutes qualifies for mid-roll ads
- 7-15 minutes is the algorithm sweet spot
- Retention (70%+ watch-through) matters more than raw length

### Short Segment Extraction (AI-Driven)

Claude identifies the 3-5 best standalone moments from the article:
- Most surprising fact or statistic
- Best myth-bust angle
- Strongest FAQ answer
- A practical self-care tip (if applicable)
- CTA/booking prompt

Each short is 20-45 seconds with its own hook for the first 3 seconds.

### Social Post Generation

Same Claude call generates platform-specific posts:

```json
{
  "linkedin": {
    "text": "Professional post, 200-300 words, includes article link",
    "hashtags": ["#ThaiMassage", "#Glasgow", ...]
  },
  "facebook": {
    "text": "Conversational post, 100-150 words",
    "hashtags": ["#ThaiMassage", ...]
  },
  "x_thread": [
    {"text": "Tweet 1 — hook (280 chars max)", "media": "banner"},
    {"text": "Tweet 2 — key point", "media": null},
    {"text": "Tweet 3 — FAQ answer", "media": null},
    {"text": "Tweet 4 — CTA with link", "media": null}
  ],
  "x_standalone": [
    {"text": "Standalone tweet 1 — hook + link", "day_offset": 0},
    {"text": "Standalone tweet 2 — myth bust", "day_offset": 1},
    {"text": "Standalone tweet 3 — FAQ", "day_offset": 2},
    {"text": "Standalone tweet 4 — tip", "day_offset": 3},
    {"text": "Standalone tweet 5 — CTA", "day_offset": 4}
  ],
  "instagram": {
    "caption": "Long caption, 200-300 words with line breaks",
    "hashtags": ["#ThaiMassage", "#GlasgowMassage", ...],
    "media": "banner"
  },
  "gbp": {
    "text": "Short post, 100-150 words, local SEO focused",
    "cta_type": "BOOK",
    "cta_url": "booking_url from config",
    "media": "banner"
  }
}
```

### X Format Alternation

The generator produces BOTH thread and standalone formats. The publisher selects which to use based on even/odd ISO week number:
- Even weeks: thread format
- Odd weeks: standalone tweets staggered across the week

---

## Component 3: Video Producer

**File:** `src/social/video_producer.py`

### Dependencies

- **ElevenLabs API** — text-to-speech (voiceover audio)
- **FFmpeg** — video composition, transitions, Ken Burns effects, caption burning, short extraction
- **Pillow** — text overlay image generation, slide creation

### TTS Interface

```python
class TTSProvider:
    """Abstract interface for text-to-speech."""
    def generate(self, text: str, voice_id: str) -> Path:
        """Returns path to audio file."""

class ElevenLabsTTS(TTSProvider):
    """ElevenLabs implementation."""

class HeyGenAvatar(TTSProvider):
    """Future: HeyGen avatar video generation."""
```

Clean interface so ElevenLabs can be swapped for HeyGen later without touching the video composition pipeline.

### ElevenLabs Configuration

- **Voice selection:** Per-client `voice_id` in config.json (allows different voices per business)
- **Model:** `eleven_multilingual_v2` (natural, expressive)
- **Output format:** MP3, 44.1kHz
- **Cost:** ~$0.30 per 1,000 characters. A 1,500-word script ≈ 8,000 characters ≈ $2.40

### Long-Form Video Composition

FFmpeg composes the final video from:

1. **Slides** — Pillow-generated images with text overlays (key points, section headings)
2. **Ken Burns** — Slow pan/zoom on article images (banner, section images)
3. **Text overlay scenes** — Animated text appearing over a background gradient or image
4. **Transitions** — Cross-dissolve between scenes (0.5-1s)

Scene composition per the script:
```
Scene 1: Ken Burns on banner image + title text overlay (intro)
Scene 2: Slide with key point + narration
Scene 3: Ken Burns on section image + narration
Scene 4: Text overlay animation (surprising fact)
Scene 5: Slide with comparison/list
...
Scene N: CTA slide with booking URL + business branding
```

**Video specs:**
- Resolution: 1920x1080 (16:9) for long-form
- Frame rate: 30fps
- Codec: H.264 (MP4)
- Audio: AAC 128kbps
- Target file size: <500MB (GHL upload limit)

### Shorts Composition

For each tagged short segment:
- Resolution: 1080x1920 (9:16 vertical)
- Duration: 20-45 seconds
- Captions: burned in (large, sans-serif, bottom-third safe zone)
- Hook text: first 3 seconds, large bold text overlay
- Background: extracted from relevant scene (image or gradient)
- CTA: final 3-5 seconds with booking URL or channel subscribe

### Caption Generation

ElevenLabs returns word-level timestamps. These drive:
- SRT file generation for long-form (YouTube auto-captions as backup)
- Burned-in captions for shorts (mandatory — 12-15% higher completion rate)

### Thumbnail Generation

Pillow generates a YouTube thumbnail:
- 1280x720px
- Article banner image as background (with slight blur/darken)
- Large bold title text (2-3 words max)
- Business logo overlay (from `schema.logo_url` in config)
- High contrast, readable at small size

---

## Component 4: GoHighLevel Publisher

**File:** `data_sources/modules/ghl_publisher.py`

### Authentication

OAuth 2.0 with auto-refresh:
- Access token expires in ~24 hours
- Refresh token is single-use (new one issued on each refresh)
- Token storage: `clients/[abbr]/ghl-tokens.json` (gitignored)
- Initial auth: one-time OAuth flow per client (manual step during onboarding)

### Client Config Extension

```json
{
  "ghl": {
    "location_id": "abc123",
    "accounts": {
      "youtube": "account_id_1",
      "facebook": "account_id_2",
      "instagram": "account_id_3",
      "linkedin": "account_id_4",
      "x": "account_id_5",
      "tiktok": "account_id_6",
      "gbp": "account_id_7"
    }
  }
}
```

Account IDs retrieved via `GET /social-media-posting/{locationId}/oauth/accounts`.

### Publishing Flow

```python
class GHLPublisher:
    def __init__(self, location_id: str, tokens_path: Path):
        """Load OAuth tokens, auto-refresh if expired."""

    def upload_media(self, file_path: Path) -> str:
        """Upload image/video to GHL media storage. Returns hosted URL."""

    def create_post(self, account_id: str, text: str,
                    media_urls: list[str] = None,
                    scheduled_at: str = None,
                    platform_details: dict = None) -> str:
        """Create/schedule a post. Returns GHL post ID."""

    def schedule_youtube_video(self, account_id: str, video_path: Path,
                                title: str, description: str,
                                tags: list[str], thumbnail_path: Path,
                                scheduled_at: str) -> str:
        """Upload and schedule a YouTube video."""

    def schedule_youtube_short(self, account_id: str, video_path: Path,
                                title: str, description: str,
                                scheduled_at: str) -> str:
        """Upload and schedule a YouTube Short."""
```

### Scheduling Strategy

All posts created in one batch with `scheduledAt` timestamps. GHL handles the actual publishing at the scheduled time. Default weekly spread:

| Day Offset | Content Published |
|---|---|
| +1 (Tue) | YouTube long-form video |
| +2 (Wed) | Short 1 (YT + TikTok + FB Reel + IG Reel) + LinkedIn post + Facebook post + GBP post |
| +3 (Thu) | Short 2 (YT + TikTok + FB Reel + IG Reel) + X posts (thread or standalone batch) |
| +4 (Fri) | Short 3 (YT + TikTok + FB Reel + IG Reel) + Instagram post |
| +5-6 (Sat-Sun) | Remaining shorts (if >3 generated) |

Day 0 = blog publish day (Monday by default).

**Future enhancement:** Per-client schedule override via `config.json` `"social.schedule"` block.

### GBP Posts

Each article generates a GBP post:
- Short text (100-150 words), locally focused
- Banner image attached
- CTA button: "BOOK" linking to `booking_url` from client config
- Posted on Day +2 alongside other social content
- Limit: 100 posts/day (well within our usage)

---

## Component 5: CLI & Automation

**File:** `src/social/repurpose_content.py` (same orchestrator from Component 1)

### CLI Interface

```bash
# Process all unrepurposed published articles
python3 src/social/repurpose_content.py --abbr gtm

# Process specific article
python3 src/social/repurpose_content.py --abbr gtm --topic "Thai Massage Benefits"

# Check status of social publishing
python3 src/social/repurpose_content.py --abbr gtm --status

# Dry run (generate content, skip GHL publishing)
python3 src/social/repurpose_content.py --abbr gtm --dry-run
```

### Cron Setup

```bash
# Blog publishes Monday 09:00
0 9 * * 1 cd /path/to/seomachine && python3 src/content/publish_scheduled.py --abbr gtm

# Social repurposing runs Monday 11:00 (2hr delay)
0 11 * * 1 cd /path/to/seomachine && python3 src/social/repurpose_content.py --abbr gtm
```

All social posts are scheduled via GHL at creation time — no daily cron needed for drip-feeding. One run creates + schedules everything for the week.

### Email Notification

After successful repurposing:
- Subject: `[GTM] Social content scheduled: Thai Massage Benefits`
- Body: video duration, number of shorts, platforms scheduled, total cost, GHL post IDs

### Logging

`logs/social-publish-log.csv`:
```
date,abbr,topic,content_type,video_status,shorts_count,platforms,ghl_post_ids,cost,notes
2026-03-26,gtm,Thai Massage Benefits,blog,uploaded,4,"yt,fb,ig,li,x,tt,gbp","id1|id2|id3",$3.20,7 posts scheduled
```

---

## Environment Variables

New entries for `.env`:

```bash
# ElevenLabs TTS
ELEVENLABS_API_KEY=sk-...

# GoHighLevel OAuth
GHL_CLIENT_ID=...
GHL_CLIENT_SECRET=...
```

Per-client tokens stored in `clients/[abbr]/ghl-tokens.json` (gitignored via pattern).

---

## Cost Estimates Per Article

| Component | Cost |
|---|---|
| Blog generation (existing) | ~$0.40 |
| Social post generation (Claude) | ~$0.05 |
| Video script generation (Claude) | ~$0.10 |
| ElevenLabs TTS (~8,000 chars) | ~$2.40 |
| Total per article | ~$2.95 |

FFmpeg and Pillow are free. GHL API is included in existing subscription. No per-post charges for social publishing.

---

## Dependencies

### New Python packages

```
elevenlabs          # ElevenLabs Python SDK
ffmpeg-python       # FFmpeg wrapper (requires ffmpeg binary installed)
Pillow              # Already in requirements.txt
requests            # Already in requirements.txt
```

### System dependencies

```bash
brew install ffmpeg  # Required for video composition
```

---

## Onboarding Steps Per Client

1. **ElevenLabs:** Choose a voice, note the `voice_id`, add to client config
2. **GoHighLevel:** Run one-time OAuth flow to get initial tokens, save to `clients/[abbr]/ghl-tokens.json`
3. **GHL account IDs:** Query `GET /social-media-posting/{locationId}/oauth/accounts` to get platform account IDs, add to client config under `ghl.accounts`
4. **Set up cron:** Add social repurposing cron job 2 hours after blog publish cron

---

## Verification Plan

### Unit testing
- Social post generator: mock Claude API, verify output JSON structure
- Video producer: mock ElevenLabs, verify FFmpeg command construction
- GHL publisher: mock API responses, verify scheduling logic
- Week alternation: verify even/odd week toggles X format correctly

### Integration testing
- Generate social content for a real published article (dry run)
- Compose a test video from a short script (30s)
- Upload a test image to GHL media storage
- Create and immediately delete a test GHL post

### End-to-end testing
- Full pipeline: published article → video + social → GHL scheduled posts
- Verify posts appear in GHL Social Planner calendar
- Verify YouTube video uploads correctly
- Verify shorts are correct aspect ratio (9:16) and duration (20-45s)
- Check burned-in captions are readable

---

## Scope Boundaries

### In scope
- Long-form video (slides + Ken Burns + text overlays + voiceover)
- YouTube Shorts extraction (3-5 per article)
- Cross-posting shorts to TikTok, Facebook Reels, Instagram Reels
- Social text posts: LinkedIn, Facebook, X (thread + standalone alternating), Instagram, GBP
- GHL API integration for all publishing
- Automated scheduling with staggered weekly spread
- ElevenLabs TTS with per-client voice selection

### Out of scope (future)
- HeyGen AI avatar videos (swap in when avatars are ready)
- Per-client custom schedule in config.json (default schedule only for now)
- Pinterest, Threads, Bluesky (GHL supports them — can add later)
- Analytics/performance tracking from social platforms
- A/B test result analysis (manual review of thread vs standalone performance)
- Stock video clip integration (images/slides only for now)
- Live demo/treatment footage integration
