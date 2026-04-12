# SDY Content Completion Plan (Pre-Launch)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete all SDY content on staging2 before go-live in ~21 days — pillar page, 8 additional location pages, 4 comp-alt pages, 5 topical articles, and internal-links-map updated with live staging2 URLs.

**Architecture:** All publishing targets `staging2.serendipitymassage.co.uk` via WP-CLI over SSH (SiteGround IPC bypass). Content is generated via `publish_scheduled.py` using JSON queue files in `research/sdy/`. Multi-run batches must use background agents to avoid UI timeout.

**Tech Stack:** Python 3 · `src/content/publish_scheduled.py` · `clients/sdy/` config · staging2 WP-CLI over SSH

---

## Content to Produce

| Type | Count | Status |
|---|---|---|
| Pillar page | 1 | Missing — highest priority |
| Location pages | 8 new areas | Missing |
| Comp-alt pages | 4 competitors | Missing |
| Topical articles | 5 articles | Missing |
| internal-links-map.md | update | Needs staging2 URLs |
| Sports Massage | 1 | Draft — pending client confirmation |

**Do not touch:** Sports Massage post 1000 (intentionally draft until client confirms service).

---

## Task 1 — Update `clients/sdy/internal-links-map.md` with staging2 URLs

The writer agents use this file for internal linking. It currently has no confirmed service URLs. Update it before running any new content so all generated pages link correctly.

**File:** `clients/sdy/internal-links-map.md`

- [ ] **Step 1.1 — Replace service page URLs**

Add/update the services section with confirmed staging2 slugs (URL pattern: `https://staging2.serendipitymassage.co.uk/seo-service/[slug]/`):

```
## Service Pages

- Traditional Thai Massage: https://staging2.serendipitymassage.co.uk/seo-service/traditional-thai-massage/
- Thai Oil Massage: https://staging2.serendipitymassage.co.uk/seo-service/thai-oil-massage/
- Thai Aromatherapy Massage: https://staging2.serendipitymassage.co.uk/seo-service/thai-aromatherapy-massage/
- Hot Stone Massage: https://staging2.serendipitymassage.co.uk/seo-service/hot-stone-massage/
- Thai Head Massage: https://staging2.serendipitymassage.co.uk/seo-service/thai-head-massage/
- Thai Facial Massage: https://staging2.serendipitymassage.co.uk/seo-service/thai-facial-massage/
- Thai Foot Massage: https://staging2.serendipitymassage.co.uk/seo-service/thai-foot-massage/
- Swedish Massage: https://staging2.serendipitymassage.co.uk/seo-service/swedish-massage/
- Couples Thai Massage: https://staging2.serendipitymassage.co.uk/seo-service/couples-traditional-thai-massage/
- Couples Thai Oil Massage: https://staging2.serendipitymassage.co.uk/seo-service/couples-thai-oil-massage/
- Thai Reflexology: https://staging2.serendipitymassage.co.uk/seo-service/thai-reflexology/
- Tailored Facial Treatment: https://staging2.serendipitymassage.co.uk/seo-service/tailored-facial-treatment/
- Head and Hair Oiling: https://staging2.serendipitymassage.co.uk/seo-service/head-and-hair-oiling/
- Hair Oiling Treatment: https://staging2.serendipitymassage.co.uk/seo-service/hair-oiling-treatment/
- Thai Deep Tissue Oil Massage: https://staging2.serendipitymassage.co.uk/seo-service/thai-deep-tissue-oil-massage/
- Aromatherapy Deep Tissue Oil Massage: https://staging2.serendipitymassage.co.uk/seo-service/aromatherapy-deep-tissue-oil-massage/
```

Note: Sports Massage URL omitted intentionally — service not yet confirmed.

- [ ] **Step 1.2 — Add key page URLs**

```
## Key Pages

- Homepage: https://staging2.serendipitymassage.co.uk/
- Book Now: https://serendipitymassage.co.uk/book-now/
```

Note: booking_url stays as the live domain even during staging — the booking system is live.

- [ ] **Step 1.3 — Commit**

```bash
git add clients/sdy/internal-links-map.md
git commit -m "SDY: update internal-links-map with staging2 service URLs"
```

---

## Task 2 — Pillar Page: Thai Massage Therapist Glasgow

Single hub page targeting the primary GBP category term. 700–1000 words. Acts as the main internal linking destination for all location and service pages.

**Files:** `research/sdy/pillar-queue.json` (create), `content/sdy/pillar/` (auto-generated)

- [ ] **Step 2.1 — Create `research/sdy/pillar-queue.json`**

```json
[
  {
    "topic": "Thai Massage Therapist Glasgow",
    "content_type": "pillar",
    "status": "pending"
  }
]
```

- [ ] **Step 2.2 — Run via background agent**

Agent prompt (run_in_background: true, timeout 300000ms):
```
Run in /Volumes/Ext Data/VSC Projects/CC Dev/seomachine:
python3 src/content/publish_scheduled.py --abbr sdy --queue pillar-queue.json
Report back: topic, post ID, status, cost.
```

- [ ] **Step 2.3 — Verify**

SSH check:
```bash
ssh -i ~/.ssh/seomachine_deploy -p 18765 u2732-2mxetksmslhk@gukm1055.siteground.biz \
  "wp post list --post_type=seo_pillar --post_status=any --fields=ID,post_title \
  --path=/home/u2732-2mxetksmslhk/www/staging2.serendipitymassage.co.uk/public_html 2>/dev/null"
```

Expected: 1 post.

---

## Task 3 — Location Pages: 8 New Glasgow Areas

Target areas within reasonable distance of Hope Street that don't yet have a page. These extend the geo footprint beyond the 11 existing areas.

**Files:** `research/sdy/location-queue-2.json` (create), `content/sdy/location/` (auto-generated)

- [ ] **Step 3.1 — Create `research/sdy/location-queue-2.json`**

```json
[
  { "topic": "Anderston", "content_type": "location", "status": "pending" },
  { "topic": "Tradeston", "content_type": "location", "status": "pending" },
  { "topic": "St George's Cross", "content_type": "location", "status": "pending" },
  { "topic": "Kelvinbridge", "content_type": "location", "status": "pending" },
  { "topic": "Shawlands", "content_type": "location", "status": "pending" },
  { "topic": "Dennistoun", "content_type": "location", "status": "pending" },
  { "topic": "Hyndland", "content_type": "location", "status": "pending" },
  { "topic": "Govanhill", "content_type": "location", "status": "pending" }
]
```

- [ ] **Step 3.2 — Run 4 at a time via background agent (first batch)**

Agent prompt (run_in_background: true, 300000ms timeout per run):
```
Run these commands in sequence in /Volumes/Ext Data/VSC Projects/CC Dev/seomachine, 300000ms timeout each:
  python3 src/content/publish_scheduled.py --abbr sdy --queue location-queue-2.json  (×4)
Report back: topic, post ID, status, cost per run.
```

- [ ] **Step 3.3 — Run remaining 4 via second background agent**

Same pattern as Step 3.2 — another agent for the next 4 pending entries.

- [ ] **Step 3.4 — Verify**

```bash
ssh -i ~/.ssh/seomachine_deploy -p 18765 u2732-2mxetksmslhk@gukm1055.siteground.biz \
  "wp post list --post_type=seo_location --post_status=any --format=count \
  --path=/home/u2732-2mxetksmslhk/www/staging2.serendipitymassage.co.uk/public_html 2>/dev/null"
```

Expected: 19 (11 existing + 8 new).

---

## Task 4 — Competitor Alternative Pages: 4 New Competitors

4 Glasgow competitors without a comp-alt page yet. Jasmine Thai, Orchid, Leelawadee, and Serenity. The competitor headings in `clients/sdy/competitor-analysis.md` must match exactly.

Note: "Glasgow Thai Massage" in the competitor file is glasgowthaimassage.co.uk (the GTM client — same owner). **Do not create a comp-alt for this.**

**Files:** `research/sdy/comp-alt-queue.json` (update — append 4 entries)

- [ ] **Step 4.1 — Append 4 entries to `research/sdy/comp-alt-queue.json`**

Open the file and add these entries (keeping existing 3 completed entries intact):

```json
{ "topic": "Jasmine Thai Massage", "content_type": "comp-alt", "status": "pending" },
{ "topic": "Orchid Wellbeing Glasgow", "content_type": "comp-alt", "status": "pending" },
{ "topic": "Leelawadee Thai Wellness Centre Glasgow", "content_type": "comp-alt", "status": "pending" },
{ "topic": "Serenity Thai Massage", "content_type": "comp-alt", "status": "pending" }
```

- [ ] **Step 4.2 — Run via background agent**

Agent prompt (run_in_background: true, 300000ms timeout per run):
```
Run these commands in sequence in /Volumes/Ext Data/VSC Projects/CC Dev/seomachine, 300000ms timeout each:
  python3 src/content/publish_scheduled.py --abbr sdy --queue comp-alt-queue.json  (×4)
Report back: topic, post ID, status, cost per run.
```

- [ ] **Step 4.3 — Verify**

```bash
ssh -i ~/.ssh/seomachine_deploy -p 18765 u2732-2mxetksmslhk@gukm1055.siteground.biz \
  "wp post list --post_type=seo_comp_alt --post_status=any --fields=ID,post_title \
  --path=/home/u2732-2mxetksmslhk/www/staging2.serendipitymassage.co.uk/public_html 2>/dev/null"
```

Expected: 7 total (3 existing + 4 new).

---

## Task 5 — Topical Articles: 5 Informational Pieces

Trust-building and FAQ-resolution content targeting the Hope Street professional/wellness audience. These complement the service pages and help convert hesitant first-timers.

**Files:** `research/sdy/topical-queue.json` (create)

- [ ] **Step 5.1 — Create `research/sdy/topical-queue.json`**

```json
[
  {
    "topic": "What to Expect at Your First Thai Massage",
    "content_type": "topical",
    "status": "pending"
  },
  {
    "topic": "Thai Massage vs Swedish Massage: Which Is Right for You",
    "content_type": "topical",
    "status": "pending"
  },
  {
    "topic": "How Thai Massage Helps Glasgow Office Workers with Desk Pain and Stress",
    "content_type": "topical",
    "status": "pending"
  },
  {
    "topic": "How Often Should You Get a Massage",
    "content_type": "topical",
    "status": "pending"
  },
  {
    "topic": "Is Thai Massage Good for Sports Recovery",
    "content_type": "topical",
    "status": "pending"
  }
]
```

- [ ] **Step 5.2 — Run via background agent**

Agent prompt (run_in_background: true, 300000ms timeout per run):
```
Run these commands in sequence in /Volumes/Ext Data/VSC Projects/CC Dev/seomachine, 300000ms timeout each:
  python3 src/content/publish_scheduled.py --abbr sdy --queue topical-queue.json  (×5)
Report back: topic, post ID, status, cost per run.
```

- [ ] **Step 5.3 — Verify**

```bash
ssh -i ~/.ssh/seomachine_deploy -p 18765 u2732-2mxetksmslhk@gukm1055.siteground.biz \
  "wp post list --post_type=seo_topical --post_status=any --fields=ID,post_title \
  --path=/home/u2732-2mxetksmslhk/www/staging2.serendipitymassage.co.uk/public_html 2>/dev/null"
```

Expected: 5 posts.

---

## Task 6 — GBP Profile Optimisation (Manual)

GBP is now approved. The profile needs to be fully optimised before go-live. This is a manual task in Google Business Profile Manager.

- [ ] **Step 6.1 — Services:** Add all confirmed services with names matching the service pages. Include short description and price range per service. Do NOT add Sports Massage until confirmed.

Services to add:
Traditional Thai Massage · Thai Oil Massage · Thai Aromatherapy Massage · Hot Stone Massage ·
Thai Head Massage · Thai Facial Massage · Thai Foot Massage · Swedish Massage ·
Couples Thai Massage · Couples Thai Oil Massage · Thai Reflexology ·
Tailored Facial Treatment · Head and Hair Oiling · Hair Oiling Treatment ·
Thai Deep Tissue Oil Massage · Aromatherapy Deep Tissue Oil Massage

- [ ] **Step 6.2 — Business description:** Use the canonical description from config:
> "Serendipity Massage Therapy & Wellness is a holistic massage and wellness studio offering therapeutic massage, relaxation treatments, and wellbeing services."
Expand to ~250 words covering USPs, location (Hope Street, City Centre), booking link.

- [ ] **Step 6.3 — Photos:** Upload minimum 10 photos — interior (treatment room, reception), exterior (building entrance, Central Chambers), treatment in progress. Keyword-rich filenames before upload.

- [ ] **Step 6.4 — Attributes:** Set: Women-led, accepts online bookings, wheelchair accessible (confirm), Wi-Fi available (confirm).

- [ ] **Step 6.5 — Opening hours:** Set accurate hours. Add special hours for public holidays.

- [ ] **Step 6.6 — Booking link:** Add `https://serendipitymassage.co.uk/book-now/` as the appointment URL.

---

## Task 7 — Final Pre-Launch Audit

Run before confirming go-live.

- [ ] **Step 7.1 — Count all content types on staging2**

```bash
WP="/home/u2732-2mxetksmslhk/www/staging2.serendipitymassage.co.uk/public_html"
ssh -i ~/.ssh/seomachine_deploy -p 18765 u2732-2mxetksmslhk@gukm1055.siteground.biz \
  "for t in seo_service seo_location seo_problem seo_comp_alt seo_pillar seo_topical post; do
    count=\$(wp post list --post_type=\$t --post_status=any --format=count --path=$WP 2>/dev/null)
    echo \"\$t: \$count\"
  done"
```

Expected final counts:
- seo_service: 17 (16 published + Sports Massage draft)
- seo_location: 19
- seo_problem: 13
- seo_comp_alt: 7
- seo_pillar: 1
- seo_topical: 5
- post (blog): 0+ (blog subdomain not needed for SDY main site)

- [ ] **Step 7.2 — Review quality-flagged posts**

These need manual edits in staging2 wp-admin before go-live (titles have ★★★★★):
- Post 1997: Aromatherapy Deep Tissue Oil Massage — readability too dense, lighten language
- Post 1164: Cowcaddens — readability issue
- Post 1149: Injury Rehabilitation — readability
- Post 1154: Injury Prevention — readability + paragraphs
- Post 1159: Diabetic Neuropathy — readability

- [ ] **Step 7.3 — Confirm go-live with user**

Swap `clients/sdy/config.json`:
- Copy `wordpress_live` block values into `wordpress` block
- Update `ssh.wp_path` to: `/home/u2732-2mxetksmslhk/www/serendipitymassage.co.uk/public_html`

**Do not do this until user explicitly confirms the site is ready to go live.**

---

## Execution Order

Tasks 1 and 2 must complete before 3, 4, 5 (internal links + pillar need to exist first).
Tasks 3, 4, 5 can run in parallel as separate background agents once Task 2 is done.
Task 6 is manual and can happen any time.
Task 7 is final gate before go-live.

## Cost Estimate

| Task | Runs | Est. cost |
|---|---|---|
| Pillar (×1) | 1 | ~$0.65 |
| Locations (×8) | 8 | ~$5.50 |
| Comp-alt (×4) | 4 | ~$2.80 |
| Topical (×5) | 5 | ~$3.75 |
| **Total** | 18 | **~$12.70** |
