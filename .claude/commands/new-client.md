# New Client Command

Set up a new client from scratch. Creates the full folder structure, config file, and stub context documents — ready to populate.

## Usage

`/new-client`

Run with no arguments. The command guides you through setup interactively.

---

## What This Command Does

1. Asks a series of questions about the new client
2. Creates `clients/[abbr]/` folder
3. Writes `clients/[abbr]/config.json` with all answers
4. Creates 7 stub context files, each with the right structure and prompts
5. Prints a completion summary and checklist

---

## Process

### Step 1: Ask Questions

Ask the following questions one at a time. Wait for an answer before moving to the next:

1. **Business name** — full trading name (e.g. "Glasgow Thai Massage")
2. **Abbreviation** — short uppercase code used in the Sheet and file paths (e.g. "GTM"). Must be 2-6 letters, no spaces.
3. **Website URL** — full URL including https:// (e.g. "https://glasgowthaimassage.co.uk")
4. **Business address** — full street address (e.g. "Floor 3 Suite 4, Victoria Chambers, 142 West Nile Street, Glasgow G1 2RQ")
5. **Area** — the neighbourhood or district the business is in — used as the destination in transport directions (e.g. "Glasgow City Centre")
6. **Postcode** — postcode only (e.g. "G1 2RQ")
7. **Phone number** — (e.g. "0141 123 4567") — enter "skip" to leave blank
8. **Booking URL** — URL of the online booking page — enter "skip" to leave blank
9. **Core keyword prefix** — the main search phrase the site targets, without a location (e.g. "thai massage", "dog grooming", "physiotherapy")
10. **Services** — comma-separated list of treatments or services offered (e.g. "Thai massage, deep tissue massage, sports massage, hot stone massage")
11. **WordPress site URL** — the WP install URL (e.g. "https://glasgowthaimassage.co.uk") — enter "skip" to set up WordPress later
12. **WordPress username** — WP application password username — enter "skip" if skipping WordPress
13. **WordPress application password** — (e.g. "Wtg0 jK0T 3bak 7XRg Mg1P o7io") — enter "skip" if skipping WordPress

### Step 2: Confirm Before Creating

Show a summary of answers and ask: "Create client [abbreviation] with these settings? (yes/no)"

If no, restart from Step 1.

### Step 3: Create the Folder and Config

Create: `clients/[abbr_lowercase]/`

Write: `clients/[abbr_lowercase]/config.json`

```json
{
  "name": "[answer to Q1]",
  "abbreviation": "[answer to Q2 in uppercase]",
  "website": "[answer to Q3]",
  "address": "[answer to Q4]",
  "area": "[answer to Q5]",
  "postcode": "[answer to Q6]",
  "phone": "[answer to Q7, or empty string]",
  "booking_url": "[answer to Q8, or empty string]",
  "keyword_prefix": "[answer to Q9]",
  "services": ["[service 1]", "[service 2]", "..."],
  "wordpress": {
    "url": "[answer to Q11, or null]",
    "username": "[answer to Q12, or null]",
    "app_password": "[answer to Q13, or null]",
    "default_post_type": "post",
    "default_status": "draft"
  }
}
```

If WordPress was skipped, set `"wordpress": null`.

### Step 4: Create Stub Context Files

Create these 7 files in `clients/[abbr_lowercase]/`. Each file gets a template with the right structure — not blank, but not filled with placeholder content either. The headings and section prompts tell the user exactly what to write.

---

**`brand-voice.md`:**
```markdown
# [Business Name] — Brand Voice & Messaging

TODO: Fill in this document before generating content. It defines the tone and voice for all writing.

---

## Brand Overview

**Business**: [Business Name]
**Tagline**: TODO — e.g. "Expert care. Friendly service."
**Positioning**: TODO — one sentence that captures what makes this business different
**Key people**: TODO — founder/owner names, credentials, years of experience

---

## Content Perspective

This is the strategic "why" behind all content. Every piece should carry a point of view, not just information. Answer these three questions to define it:

**What we believe needs to change in the industry:**
TODO — What is the industry getting wrong? What framing, assumption, or behaviour needs to shift? (e.g. "massage is sold as a treat when it should be sold as maintenance")

**How this change benefits our audience:**
TODO — If the industry shifted, what would clients do differently? What better decisions would they make? (e.g. "they would book regularly instead of only when they're in pain")

**How [Business Name] contributes to that change:**
TODO — What about this specific business makes it part of the solution? Credentials, approach, pricing, location, team? (e.g. "we deliver genuine therapeutic technique at city-centre prices, making regular sessions realistic")

**In practice, this means:**
TODO — Translate the above into 3-4 writing instructions. What should every piece of content do or avoid as a result? (e.g. "lead with outcomes, not indulgence; always make the case for returning")

---

## Brand Voice Pillars

Define 3 voice pillars. For each one: what it means, how it sounds in writing, an example sentence, and what to avoid.

### 1. [Pillar name — e.g. Warm and Welcoming]
- **What it means**: TODO
- **How it sounds**: TODO
- **Example**: "TODO"
- **Avoid**: TODO

### 2. [Pillar name — e.g. Grounded in Expertise]
- **What it means**: TODO
- **How it sounds**: TODO
- **Example**: "TODO"
- **Avoid**: TODO

### 3. [Pillar name — e.g. Local and Specific]
- **What it means**: TODO
- **How it sounds**: TODO
- **Example**: "TODO"
- **Avoid**: TODO

---

## Writing Rules

List any client-specific rules beyond the global style guide. Examples:
- Never use the word "luxury"
- Always refer to staff as "therapists", not "masseuses"
- Use first person plural ("we") not third person ("the team")

---

## No-Go Phrases

List phrases that are off-brand and must not appear in content:
- TODO

---

## Business Name Rules

How to refer to the business in different contexts:
- **Full name**: [Business Name]
- **Short form**: TODO (e.g. "the studio", "us")
- **In keywords**: TODO (e.g. "[keyword] near [area]")
```

---

**`seo-guidelines.md`:**
```markdown
# SEO Guidelines — [Business Name]

TODO: Fill in this document to guide keyword and entity strategy for all content.

---

## Content Architecture

Describe the hub-and-spoke page structure for this site. Example:

```
Pillar Pages (GBP categories)
  └── Service Pages
        └── Location Pages (area-level)
              └── Geo Pages (street/postcode-level)
Blog / Topical Articles (link into the above)
```

---

## Primary Entity

- **Entity name**: TODO — the main thing the business is known for (e.g. "Thai massage Glasgow")
- **Entity type**: Service / Place / Person / Organisation
- **Knowledge Panel**: TODO — does this business have a Google Knowledge Panel? Y/N

---

## Entity Cluster

List the key entities that co-occur with this business in content. Include treatments, conditions, outcomes, people, and locations.

| Category | Entities |
|----------|---------|
| Treatments | TODO — e.g. Thai massage, deep tissue massage, sports massage |
| Conditions | TODO — e.g. back pain, neck tension, muscle soreness |
| Outcomes | TODO — e.g. relaxation, mobility, pain relief |
| People | TODO — e.g. founder name, key staff |
| Locations | TODO — e.g. Glasgow City Centre, West End, Merchant City |

---

## Keyword Strategy

### Primary keywords
TODO — list 3-5 core keywords with approximate search intent (transactional / informational / local)

### Long-tail targets
TODO — list 5-10 long-tail variations to target across the content cluster

### Keywords to avoid
TODO — any terms that are off-strategy or too competitive

---

## Schema Priorities

Which schema types to apply to this site's content:
- TODO — e.g. LocalBusiness, Service, FAQPage, BreadcrumbList
```

---

**`internal-links-map.md`:**
```markdown
# [Business Name] — Internal Links Map

TODO: Populate with key pages from the website. Reference this when writing content to pick correct anchor text and URLs.

---

## Core Pages

### Homepage
- **URL**: TODO
- **When to link**: When referencing the business broadly
- **Anchor text examples**: "[Business Name]", "our [area] studio"

### About Page
- **URL**: TODO
- **When to link**: When mentioning founders, credentials, or the business story
- **Anchor text examples**: "about us", "meet our team"

### Contact / Find Us
- **URL**: TODO
- **When to link**: When mentioning location, directions, or enquiries
- **Anchor text examples**: "contact us", "find us at [address]"

---

## Service Pages

TODO: Add one entry per service page. Format:

### [Service Name]
- **URL**: TODO
- **When to link**: TODO
- **Anchor text examples**: TODO

---

## Location Pages

TODO: Add one entry per location landing page as they're created. Format:

### [Area Name]
- **URL**: TODO
- **When to link**: TODO
- **Anchor text examples**: TODO
```

---

**`features.md`:**
```markdown
# [Business Name] — Services & Features

TODO: Document all services offered, pricing if public, and key differentiators. Reference this when writing service pages and content body copy.

---

## Services Offered

TODO: List each service with a brief description.

### [Service 1]
- **Description**: TODO — 1-2 sentence description
- **Duration**: TODO — e.g. 30 / 60 / 90 minutes
- **Price**: TODO — or leave blank if not public
- **Who it's for**: TODO — target audience or use case

### [Service 2]
- **Description**: TODO
- **Duration**: TODO
- **Price**: TODO
- **Who it's for**: TODO

---

## Key Differentiators

What makes this business different from competitors? List 3-5 specific, provable claims:

1. TODO — e.g. "Only studio in Glasgow trained at Wat Pho"
2. TODO
3. TODO

---

## Facilities & Practical Info

- **Parking**: TODO — any nearby parking options
- **Accessibility**: TODO — step-free access, lift, etc.
- **Hours**: TODO — opening times
- **Booking**: TODO — how clients book (online, phone, walk-in)
```

---

**`competitor-analysis.md`:**
```markdown
# [Business Name] — Competitor Analysis

TODO: Research and document the main competitors. Reference this when writing content to identify gaps and positioning angles.

---

## Primary Competitors

### Competitor 1
- **Name**: TODO
- **Website**: TODO
- **Strengths**: TODO — what are they doing well?
- **Weaknesses**: TODO — where do they fall short?
- **Keywords they rank for**: TODO

### Competitor 2
- **Name**: TODO
- **Website**: TODO
- **Strengths**: TODO
- **Weaknesses**: TODO
- **Keywords they rank for**: TODO

---

## Content Gaps

TODO: Keywords or topics the competitors aren't covering well that we can target:
- TODO
- TODO

---

## Positioning vs. Competitors

TODO: In one paragraph, how does [Business Name] differentiate itself from the above?
```

---

**`target-keywords.md`:**
```markdown
# [Business Name] — Target Keywords

TODO: Populate with priority keywords before generating content. Run /research or /research-serp to build this list.

---

## Tier 1 — Primary targets (highest priority)

| Keyword | Monthly Searches (est.) | Difficulty | Intent | Target page type |
|---------|------------------------|------------|--------|-----------------|
| TODO    | TODO                   | TODO       | TODO   | TODO            |

---

## Tier 2 — Secondary targets

| Keyword | Monthly Searches (est.) | Difficulty | Intent | Target page type |
|---------|------------------------|------------|--------|-----------------|
| TODO    | TODO                   | TODO       | TODO   | TODO            |

---

## Tier 3 — Long-tail / geo targets

| Keyword | Monthly Searches (est.) | Difficulty | Intent | Target page type |
|---------|------------------------|------------|--------|-----------------|
| TODO    | TODO                   | TODO       | TODO   | TODO            |

---

## Keywords to Avoid

TODO: Terms that are out of scope, too competitive, or off-brand for this site.
```

---

**`writing-examples.md`:**
```markdown
# [Business Name] — Writing Examples

TODO: Add 2-3 examples of good writing that captures the right voice for this client. These guide the agents when writing content.

These can be: existing page copy from the site, a paragraph you've written yourself, or an excerpt from a competitor page that has the right tone.

---

## Example 1 — [Label, e.g. "Homepage intro"]

Source: TODO (URL or "written for this project")

```
TODO: Paste the example text here.
```

**What's good about this**: TODO — note what the agents should learn from it (tone, structure, word choices)

---

## Example 2 — [Label]

Source: TODO

```
TODO
```

**What's good about this**: TODO

---

## Example 3 — [Label, optional]

Source: TODO

```
TODO
```

**What's good about this**: TODO
```

---

### Step 5: Run Competitor Research

Once `config.json` and `target-keywords.md` are created, automatically run:

```bash
python3 src/research_competitors.py --abbr [abbr]
```

This fetches the top 10 map pack + top 10 organic results for the client's primary keyword, scrapes each competitor site, and writes a fully populated `clients/[abbr]/competitor-analysis.md`. No manual research needed.

If the script fails (e.g. DataForSEO quota), note it in the completion summary — the user can run it manually later.

### Step 6: Print Completion Summary

```
✓ Client created: [ABBREVIATION]
  Folder: clients/[abbr]/

Files created:
  ✓ config.json          — machine config (name, address, services, WP credentials)
  ✓ brand-voice.md       — TODO: fill in voice pillars and writing rules
  ✓ seo-guidelines.md    — TODO: fill in entity cluster and keyword strategy
  ✓ internal-links-map.md — TODO: add URLs for all key pages
  ✓ features.md          — TODO: document all services and differentiators
  ✓ competitor-analysis.md — auto-populated by research_competitors.py
  ✓ target-keywords.md   — TODO: populate with priority keywords
  ✓ writing-examples.md  — TODO: add 2-3 examples of on-brand writing

Next steps:
  1. Fill in the TODO sections in the remaining context files
  2. Add [ABBREVIATION] rows to the Google Sheet to start generating content
  3. Run /research [topic] to start building keyword strategy
  4. Run python3 src/geo_batch_runner.py to generate content when ready

Output will be saved to: content/[abbr]/
```

---

## Notes

- The `config.json` is the only file the batch runner reads programmatically. The 7 markdown files are read by Claude as context.
- WordPress credentials can be added to `config.json` later by editing the file directly.
- Global writing rules (grammar, formatting) live in `context/style-guide.md` and apply to all clients — no need to repeat them per client.
