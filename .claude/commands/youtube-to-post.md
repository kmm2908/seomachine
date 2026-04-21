# /youtube-to-post [YouTube URL]

Convert a YouTube video into a GTB Yoga & Stretching blog post and queue it for publishing.

## Usage
`/youtube-to-post https://youtube.com/watch?v=...`

## Steps

### 1 — Ingest the video

Use the `ingest-youtube` skill to extract transcript, key points, and a summary from the URL.

If the video has no auto-generated captions, note that and ask the user to provide an alternative.

### 2 — Write the blog post

Use the transcript as primary source material. Write for GTB (Glasgow Thai Massage blog):

- Load `clients/gtb/brand-voice.md` and `clients/gtb/seo-guidelines.md`
- Load `clients/gtb/internal-links-map.md` for internal link opportunities
- Word count: 600–1000 words
- Frame for a Glasgow audience interested in wellness — how does this yoga/stretching technique complement Thai massage or improve daily life?
- Structure: hook → benefit-led sections (H2s) → FAQ accordion → schema block
- Include 2–3 internal links to GTM service or location pages
- Include at least 2 booking CTAs linking to `https://glasgowthaimassage.co.uk/booking/`
- Save to: `content/gtb/blog/[slug]-[YYYY-MM-DD]/[slug]-[YYYY-MM-DD].html`

Credit the source video naturally in the post (e.g. "As demonstrated by [channel name]...") but do not embed it — the post stands alone as written content.

### 3 — Quality check

Verify before queuing:
- Opening paragraph has a hook (problem, question, or surprising fact)
- ≥2 CTAs in body text (not counting FAQ section)
- No body paragraph longer than 3 sentences
- Flesch reading ease ≥55 (run: `python3 -c "import textstat; ..."` if needed)

Fix any failures before proceeding.

### 4 — Add to queue

Append to `research/gtb/yoga-stretching-queue.json`:

```json
{
  "topic": "[Post Title]",
  "content_type": "blog",
  "status": "pending",
  "wp_category": "Yoga & Stretching",
  "cadence": 7,
  "source_file": "content/gtb/blog/[slug]-[date]/[slug]-[date].html"
}
```

Validate JSON is well-formed after appending.

### 5 — Confirm

```
✓ Post written: [title]
  File: content/gtb/blog/[slug]-[date]/[slug]-[date].html
  Words: N | Quality: hook ✓ | CTAs ✓ | paragraphs ✓
  Added to yoga-stretching-queue.json — will publish Friday cron
```
