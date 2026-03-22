# SEO Guidelines — Serendipity Massage Therapy & Wellness

This document outlines SEO strategy and content requirements for all SMT content.

---

## Content Architecture

### Page Type Hierarchy

All SMT content fits into one of five page types in a hub-and-spoke structure:

```
GBP Category Pages (Pillar)
  └── Service Pages (Cluster)
        └── Location Pages (Area)
              └── Geo Pages (Postcode/Street)

Blog / Topical Articles (standalone, links into the above)
```

Each level links down to the next and back up to the one above.

### Page Type Definitions

| Page Type | H1 Target | Agent |
|-----------|-----------|-------|
| **Pillar / GBP Category** | GBP category + Glasgow (e.g. "Thai Massage Therapist Glasgow") | `pillar-page-writer.md` |
| **Service Page** | Specific service + Glasgow (e.g. "Traditional Thai Massage Glasgow") | `service-page-writer.md` |
| **Location Page** | Service + area (e.g. "Thai Massage in Finnieston, Glasgow") | `location-page-writer.md` |
| **Blog / Topical** | Topic or question keyword | `blog-post-writer.md` / `topical-writer.md` |

### Keyword Cannibalization Avoidance

Two pages must not target the same H1 keyword:

- Pillar page H1: `thai massage therapist Glasgow` (GBP category)
- Service page H1: `traditional thai massage Glasgow` (specific service)
- Pillar page H2: `Traditional Thai Massage` (no Glasgow modifier — avoids competing with service page H1)
- Location page H1: `thai massage West End Glasgow` (geo-modified — separate from city-wide pages)

---

## Content Length

| Content Type | Word Count |
|-------------|------------|
| Service page | 400–600 |
| Location page | 450+ |
| Pillar page | 700–1000 |
| Topical article | 600–1000 |
| Blog post | 600–1200 |

Quality over quantity. Every sentence should earn its place.

---

## Entity Optimisation

> **This section takes priority over keyword density rules.** When entity optimisation and keyword targets conflict, follow entity guidance.

Google recognises **entities**: specific people, places, treatments, conditions, and concepts it has mapped in its Knowledge Graph. Writing for entities means making it obvious what your page is about and how the concepts relate to each other.

A page that clearly establishes "Thai massage → muscle tension → sports recovery → Glasgow City Centre" as a cluster of related entities will outrank a page that just repeats "thai massage Glasgow" at 1.5%.

### One Primary Entity Per Page

Every page must have one clear primary entity:

- **Service page**: the treatment (e.g. *Thai massage*)
- **Location/geo page**: the area (e.g. *Finnieston, Glasgow*)
- **Blog post**: the topic or question (e.g. *deep tissue massage for back pain*)

The primary entity must appear in the URL, H1, opening sentence, and title tag.

### 3–5 Secondary Entities

Secondary entities are the related concepts that define and contextualise the primary entity. Choose them by:

1. Checking Google's Knowledge Panel for your primary entity
2. Reviewing terms that appear consistently across the top 5 ranking pages
3. Using the condition → treatment → outcome → location chain for SMT

**SMT entity clusters to draw from:**

| Category | Entities |
|----------|---------|
| Treatments | Thai massage, Swedish massage, sports massage, hot stone massage, aromatherapy massage |
| Conditions | Muscle tension, back pain, neck pain, sports injury, poor posture, stress, chronic pain |
| Outcomes | Flexibility, range of motion, recovery, relaxation, pain relief |
| People | Licensed massage therapist, sports therapist, holistic therapist, Jariya Malone |
| Location | Glasgow, City Centre, Hope Street, [specific district], [nearest subway station] |

### Describe Entities, Don't Just Name Them

Entity salience increases when you describe an entity's attributes rather than just naming it.

❌ Weak: "Thai massage helps with muscle tension."
✅ Strong: "Thai massage, a traditional technique using assisted stretching and acupressure along sen energy lines, releases deep muscle tension and improves joint mobility."

**Rule:** Every time you introduce a key entity for the first time in an article, give it one descriptive clause.

### Entity Co-occurrence

Place related entities close together in your copy:

- **Condition + treatment**: "neck pain" near "deep tissue massage"
- **Treatment + outcome**: "Thai massage" near "flexibility" and "range of motion"
- **Location + service**: "Hope Street" near "massage therapist"
- **Credential + service**: "signature technique" or "trained therapist" near service name

**Example:** "For Glasgow office workers dealing with neck pain and shoulder tension from desk work, a regular deep tissue massage session at Serendipity can restore range of motion and reduce chronic discomfort."

### Entity Pre-Writing Checklist

Before writing any SMT article:

- [ ] Primary entity (one concept this page is fundamentally about)
- [ ] 3–5 secondary entities (related treatments, conditions, outcomes, location)
- [ ] 2–3 entity co-occurrence pairs to work into the copy
- [ ] Schema type for this page (Service / FAQPage / Article / LocalBusiness)

---

## Keyword Placement

Primary keyword MUST appear in:
- [ ] H1 headline (preferably near the beginning)
- [ ] First 100 words
- [ ] At least 2 H2 subheadings
- [ ] Last paragraph
- [ ] Meta title (within first 60 characters)
- [ ] Meta description
- [ ] URL slug

Keyword density is a rough guide only. Natural integration always takes priority over hitting a number.

---

## Meta Elements

### Meta Title
- 50–60 characters including business name if used
- Primary keyword included
- Unique per page

### Meta Description
- 150–160 characters
- Primary keyword included naturally
- Clear value proposition and call-to-action

### URL Slug
- Lowercase, hyphens only
- Include primary keyword
- 3–5 words ideal

---

## Internal Linking

- **3–5 internal links per article**
- Use descriptive, keyword-rich anchor text
- Link to specific service pages over the homepage
- Check `internal-links-map.md` for confirmed URLs before linking
- Do not link to the booking page in body content — the page template handles CTAs

---

## Schema Markup

All 5 content writers output a `<!-- SCHEMA -->` block with JSON-LD `@graph` containing:
- Primary type (`Article`, `BlogPosting`, `Service`, or `WebPage`)
- `FAQPage`
- `LocalBusiness` (Serendipity's NAP details)

Schema is generated automatically by the content agents. Test at schema.org/validator before publishing.

### Local Entity Signals

- **NAP consistency**: Business name, address, and phone must be identical across website, Google Business Profile, and all directories.
- **Google Business Profile**: Accurate categories. Booking link. Service descriptions using entity language.
- **Reviews**: Encourage clients to mention specific treatments and results.

---

## Content Quality Standards

### E-E-A-T for SMT

- **Expertise**: Accurate, detailed information on massage treatments and conditions
- **Authoritativeness**: Reference Jariya Malone's signature technique development as a credibility signal
- **Trustworthiness**: No invented claims. No outcomes that aren't supported by standard massage therapy evidence

### Readability Targets
- Flesch reading ease: 60+ (aim for 70+)
- Average sentence length: 15–20 words
- Paragraphs: 2–4 sentences
- Active voice: 80%+

---

## SEO Checklist (Per Article)

### Content
- [ ] Correct content type and word count range
- [ ] Primary keyword identified
- [ ] 3–5 secondary entities identified
- [ ] Entity co-occurrence pairs included
- [ ] Provides unique value vs competitors

### Structure
- [ ] One H1 with primary keyword
- [ ] 4–7 H2 sections
- [ ] 2–3 H2s include keyword variations
- [ ] Keyword in first 100 words and conclusion

### Meta
- [ ] Meta title 50–60 chars with keyword
- [ ] Meta description 150–160 chars with keyword and CTA
- [ ] URL slug includes primary keyword

### Links
- [ ] 3–5 internal links with descriptive anchor text
- [ ] All URLs verified against internal-links-map.md

### Quality
- [ ] No hyphens as sentence connectors
- [ ] Business name appears near keyword phrases
- [ ] Serendipity brand voice maintained
- [ ] Clear call-to-action
