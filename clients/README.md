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

## Adding a New Client

Run `/new-client` — it asks questions and creates the full folder structure automatically.

To set up manually:
1. Create `clients/[abbreviation-lowercase]/` folder
2. Add `config.json` using the schema above
3. Add the 7 context files (copy from an existing client and customise)
4. Add the abbreviation as a dropdown option in Column D of the Google Sheet
5. Test with one row before bulk-running: `python3 geo_batch_runner.py A2:E3`
