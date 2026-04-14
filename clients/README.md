# Client Config Files

Each client lives in a single folder under `clients/`. The folder contains the machine-readable config (`config.json`) and all context files. To add a new client, run `/new-client`.

```
clients/
  gtm/                  ← one folder per client
    config.json         ← machine-readable config (name, address, WP creds, services)
    brand-voice.md      ← tone, messaging pillars, client-specific writing rules
    seo-guidelines.md   ← keyword strategy, entity optimisation rules
    internal-links-map.md
    features.md
    competitor-analysis.md
    target-keywords.md
    writing-examples.md
  README.md
```

---

## JSON Schema (`config.json`)

```json
{
  "name": "Business display name",
  "abbreviation": "ABC",
  "address": "Full street address",
  "area": "Area name used in transport directions e.g. Bath Street, City Centre",
  "postcode": "G2 4JR",
  "phone": "0141 XXX XXXX",
  "booking_url": "https://example.com/book",
  "website": "https://example.com",
  "services": ["service 1", "service 2"],
  "keyword_prefix": "the core search keyword e.g. thai massage",
  "niche": "slug identifying the client's market niche e.g. thai-massage, massage-therapy",
  "ai_visibility": {
    "canonical_description": "One or two sentences used verbatim or near-verbatim when introducing the business in blog/topical content.",
    "brand_associations": ["brand-problem phrase 1", "brand-problem phrase 2"],
    "positioning_note": "Plain-English tone guidance — what to emphasise and what to avoid."
  },
  "gbp_location_id": "123456789012345678",
  "wordpress": {
    "url": "https://example.com",
    "username": "wp-username",
    "app_password": "xxxx xxxx xxxx xxxx xxxx xxxx",
    "default_post_type": "post",
    "default_status": "draft"
  }
}
```

### Key fields

- **area** — Used as the transport destination in geo and location content. Transport directions go FROM the target location TO this area.
- **keyword_prefix** — Combined with location/area names to form keyword phrases e.g. "thai massage Finnieston".
- **abbreviation** — Must match exactly (case-insensitive) what is in Column D of the Google Sheet.
- **wordpress.app_password** — WordPress Application Password generated in WP Admin → Users → Profile → Application Passwords. Never the login password.
- **ai_visibility** — Optional. Injected as `## AI Brand Positioning` in system prompts for `blog` and `topical` content types. Implements the consistent-phrasing strategy from `context/ai-brand-visibility.md`. All three sub-fields are optional; omit the block entirely to disable.
- **gbp_location_id** — Optional. Numeric Google Business Profile location ID (e.g. `"123456789012345678"`). Enables `data_sources/modules/google_business_profile.py` to fetch live business info, hours, reviews, and attributes from the GBP API. Requires the "My Business Business Information API" and "My Business Reviews API" enabled in Google Cloud, plus a service account with Manager access to the location (added via business.google.com → Settings → Managers). Credentials path set via `GBP_CREDENTIALS_PATH` in `.env`. Omit this field if GBP sync is not needed.

---

## Context Files

Each `clients/[abbr]/` folder contains client-specific context loaded by the batch runner:

| File | Purpose |
|------|---------|
| `brand-voice.md` | Tone, messaging pillars, writing rules specific to this client |
| `seo-guidelines.md` | Keyword strategy and SEO rules for this client's site |
| `internal-links-map.md` | Key pages and URLs for internal linking |
| `features.md` | Services and features to reference |
| `competitor-analysis.md` | Competitive landscape |
| `target-keywords.md` | Priority keywords and clusters |
| `writing-examples.md` | Example content to guide tone and style |

Global context files (not client-specific) stay in `context/`:
- `context/style-guide.md` — Grammar, formatting, universal writing rules
- `context/cro-best-practices.md` — Conversion optimisation principles

---

## Secondary Blog Sites

Some clients have a secondary blog site alongside their main site — either as a subdomain (`blog.example.com`) or a completely separate domain (`exampleblog.com`). The SEO Machine plugin handles these differently to prevent accidental content duplication.

### How it works

Setting the `seo_hub_source` WordPress option on the secondary blog site activates **lite mode**:

```bash
wp option update seo_hub_source "https://main-site-url.com"
```

In lite mode, the plugin:
- **Suppresses** all CPT registration (`seo_service`, `seo_location`, `seo_pillar`, `seo_comp_alt`, `seo_problem`, `seo_blog`) — these post types will not appear in wp-admin
- **Keeps** the `[seo_hub]` shortcode, SEO meta output, Open Graph tags, JSON-LD schema, and the SEO Machine metabox on standard `post` type

### Available content types

Secondary blog sites support `blog` content type only (standard WordPress `post` type). The batch runner and scheduled publisher will generate and publish blog posts as normal.

Service, location, pillar, comp-alt, and problem pages are **not published to the secondary blog site**. They live on the main site and surface on the blog via the `[seo_hub]` shortcode.

### Hub shortcode

Place `[seo_hub type="location"]` in an Elementor Shortcode widget to display a live list of location pages from the main site. Works for all types: `location`, `service`, `pillar`, `topical`, `comp_alt`, `problem`. Results are cached for 12 hours.

Cache bust if needed:
```bash
wp transient delete seo_hub_cache_location
```

### Existing secondary blog clients

| Client | Abbr | Main site | seo_hub_source set? |
|--------|------|-----------|---------------------|
| Glasgow Thai Massage Blog | GTB | glasgowthaimassage.co.uk | ✓ (set in session 14) |
| Thai Massage Greenock Blog | TMB | thaimassagegreenock.co.uk | pending onboarding |

---

## Adding a New Client

Run `/new-client` — it asks questions and creates the full folder structure automatically.

To set up manually:
1. Create `clients/[abbreviation-lowercase]/` folder
2. Add `config.json` using the schema above
3. Add the 7 context files (copy from an existing client and customise)
4. Add the abbreviation as a dropdown option in Column D of the Google Sheet
5. Test with one row before bulk-running: `python3 geo_batch_runner.py A2:E3`
