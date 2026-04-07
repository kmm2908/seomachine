# Xagio "Agent X" System — Analysis & Replication Plan

## What Xagio Does (from the webinar + page scrape)

Xagio is a SaaS platform that automates the entire process of building, ranking, and monetising local SEO "rank and rent" websites. The founder (30 years in internet marketing) built five interconnected tools that form a pipeline:

### The 5-Tool Pipeline

**1. KillerEMD — Niche + Domain Finder**
- Input a service keyword (e.g. "water damage")
- Filters by search volume (300-800/mo), CPC ($20+), negative keywords
- Returns hundreds of keyword+city combinations
- Checks if an EMD (Exact Match Domain) is available (e.g. charlottewaterdamage.com)
- Assigns a "Kill Score" (0-100) — higher = easier to rank
- Checks domain history, existing backlinks via Wayback Machine
- Can find expired domains with pre-existing link equity

**2. Agent X — AI Website Builder**
- Takes the purchased EMD + city + niche as inputs
- Scrapes the top-ranking sites in Google for that keyword
- Clusters the keywords into logical service pages (e.g. water damage, restoration, smoke damage, cleanup)
- For each page cluster, optimises: title tag, URL, meta description, H1
- Picks the highest-volume, lowest-competition keyword per cluster as the primary target
- Generates full page content using AI, seeded by the optimisation data
- Writes JSON-LD schema for every page (LocalBusiness, WebPage, Service, FAQ)
- Injects business NAP (name, address, phone) into content and schema
- Installs a pre-designed Elementor template (165+ available)
- Entire build takes 7-15 minutes of AI processing after ~15 min setup
- Total cost: ~$6-12 in credits (~$20 all-in with domain)

**3. Trust Made Media — AI Brand Kit Generator**
- Input: business name, phone, website, colour palette, industry
- Generates: logo (3 AI options, 1 revision), ~20 branded images
- Images include: owner photo, team photo, service vehicles with branding, workspace, storefront, before/after shots, hero images
- All images have company logo + phone number overlaid
- Purpose: make the site look like a real local business (conversion optimisation)
- Uses webp format, landscape mode

**4. RingRobin — Call/Lead Tracking + CRO**
- Buys a local Twilio phone number (~$1.15)
- Installs tracking script on site (header snippet)
- Tracks: phone calls, text messages, form submissions, website traffic
- All conversion data in one dashboard (replaces StatCounter + CallRail + form plugin)
- Provides conversion rate metrics (traffic vs leads)
- Notifications via text/email on new leads
- Honeypot anti-spam on forms
- White-label reporting available

**5. Xagio Cloud — Managed Hosting + Rank Tracking**
- One-click WordPress hosting from within the dashboard ($1.40-$2.20/mo/site)
- Auto-installs WordPress + Xagio plugin
- Cloudflare DNS + SSL included
- Built-in rank tracker for all keywords
- Central dashboard managing all sites
- Credits-based billing system

### The Process (Live Demo: ~45 minutes total)

1. **Find niche** (KillerEMD, 5 min): "water damage" → Charlotte NC → Kill Score 98 → charlottewaterdamage.net available
2. **Buy domain** (NameCheap, 1 min): ~$10
3. **Launch hosting** (Xagio Cloud, 2 min): Point DNS, auto-install WordPress + Xagio plugin
4. **Set up tracking** (RingRobin, 5 min): Buy local phone number, install tracking script, create lead capture form
5. **Enter business info** (Xagio plugin, 2 min): Business name, city, state, zip, phone
6. **Pick template** (Xagio, 1 min): Choose from 165 Elementor templates
7. **Run Agent X** (15 min wait): Enter city + keyword → AI analyses top-ranking competitors → clusters keywords into pages → optimises each page → generates content → writes schema → builds pages
8. **Generate brand kit** (Trust Made Media, 10 min wait): Logo + 20 branded images
9. **Swap images + final touches** (10-15 min): Replace placeholder images with branded ones, add form embed, update map location
10. **Submit sitemap to Google** and wait

### Results Claimed

| Site | Niche/City | Registered | First Page | #1 Position | Links |
|------|-----------|-----------|-----------|------------|-------|
| Pool Builders Davie | Pool building, FL | Feb 26, 2026 | 10 days | #2 (30 days) | Zero |
| Scottsdale General Contractors | General contracting, AZ | Jan 23, 2026 | Jan 25 (#4) | #1 | Zero |
| Commercial Plumber Austin | Plumbing, TX | Jan 2, 2026 | Jan 6 (#10) | #1 (Feb) | Zero |
| ARM Pest Control | Pest control | Jan 26, 2026 | Feb 15 (#5) | #4 | Pre-existing |
| Pool Resurfacing Phoenix | Pool resurfacing, AZ | 2015 | - | #1 (10 years) | - |
| Student (Carolyn) — Mold removal | Mold, unknown city | ~3 weeks prior | 3 weeks | #3 and #6 | Zero |

### What They Explicitly Don't Do
- No Google Business Profile / GMB
- No citations
- No social signals
- No CTR manipulation
- No content optimisation tools (Surfer SEO etc.)
- No geotagging images
- No regular content refresh needed
- No backlinks initially (sometimes add a few if needed)

### What They Say You DO Need
1. A good EMD (exact match domain) — or at least a strong domain
2. A profitable niche with a weakness on Google page 1
3. A well-optimised site (content, schema, structure)
4. Time (hours to 30 days)
5. Optionally: a few backlinks if the above isn't enough

---

## How We Could Replicate This

### What Xagio Actually Automates (the technical breakdown)

| Component | What it does | Open-source / free alternative |
|-----------|-------------|-------------------------------|
| KillerEMD | Keyword research + domain availability + competition analysis | Google Keyword Planner API + domain WHOIS API + custom scoring |
| Agent X | Competitor analysis → keyword clustering → on-page optimisation → AI content → schema generation → WordPress page creation | Python scraper + Claude/GPT API + WordPress REST API + Elementor templates |
| Trust Made Media | AI logo + branded image generation | DALL-E/Midjourney API + Pillow for overlays |
| RingRobin | Call tracking + form builder + analytics | Twilio API + custom form + Plausible/Umami analytics |
| Xagio Cloud | Managed WordPress hosting | Any VPS (Hetzner, DigitalOcean) + WordOps/RunCloud |

### Realistic Replication Plan

**Phase 1: Niche Research Tool (KillerEMD equivalent)**
- Google Ads API for keyword volume + CPC data
- Domain availability check via WHOIS/registrar API
- Competition scoring: scrape Google SERP, analyse DA/DR of top 10 results
- EMD matching: combine keyword + city → check .com/.net/.org availability
- Output: ranked list of opportunities with profitability + difficulty scores

**Phase 2: AI Website Builder (Agent X equivalent)**
- Scrape top 5-10 Google results for target keyword
- Extract: page titles, H1s, content topics, schema types, internal link structure
- Cluster keywords using NLP (semantic similarity)
- Generate optimised title/URL/description/H1 per page using Claude API
- Generate full page content using Claude API with optimisation context
- Generate JSON-LD schema per page
- Push to WordPress via REST API (or WP-CLI)
- Apply Elementor template programmatically

**Phase 3: Brand Kit Generator (Trust Made Media equivalent)**
- Generate logo options via DALL-E/Flux API
- Generate branded images (vehicles, team, workspace) via image generation API
- Overlay logo + phone number using Pillow/ImageMagick
- Output webp images sized for hero, about page, service pages

**Phase 4: Lead Tracking (RingRobin equivalent)**
- Twilio for phone numbers + call tracking
- Simple form builder (or use existing like Gravity Forms)
- Lightweight analytics (Plausible or custom)
- Dashboard showing: traffic, calls, forms, conversion rate

**Phase 5: Hosting Orchestration**
- API-driven VPS provisioning (Hetzner Cloud API is cheapest)
- WordOps or RunCloud for WordPress management
- Cloudflare API for DNS + SSL
- Central dashboard for all sites

### Cost Comparison

| | Xagio (Agency plan) | DIY Build |
|---|---|---|
| Monthly cost | $166/mo ($1,997/yr) | ~$20-50/mo (APIs + hosting) |
| Per-site cost | ~$5-12 | ~$2-5 (API calls + hosting) |
| Per-site hosting | $1.40-2.20/mo | $1-2/mo (shared VPS) |
| Time per site | ~45 min | ~30-60 min once automated |

### What Would Make This Project Worthwhile

Building this yourself makes sense if:
1. You plan to build 50+ sites (volume justifies the dev time)
2. You want full control over the AI prompts and optimisation logic
3. You want to avoid the $2K/year Xagio subscription
4. You want to white-label or sell the service yourself

It does NOT make sense if:
- You just want to build 5-10 sites (just buy Xagio)
- You don't want to maintain the tooling

### Suggested MVP (Minimum Viable Product)

Focus on the highest-value automation first:

1. **Keyword research + EMD finder** — Python script using Google Ads API + WHOIS
2. **Agent X clone** — Python script that takes a keyword + city, scrapes competitors, generates optimised content via Claude API, pushes to WordPress
3. **Schema generator** — Auto-generate LocalBusiness + Service schema from business info + page content

Skip for now: Trust Made Media (just use Canva/AI image gen manually), RingRobin (use CallRail or Google Voice), hosting (use any existing host).

This MVP would automate the 80% that matters — the research, content, and optimisation — while you handle images and tracking manually.
