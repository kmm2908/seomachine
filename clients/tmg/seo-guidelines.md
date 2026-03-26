# SEO Guidelines — Thai Massage Greenock

This document outlines SEO strategy and content requirements for all TMG content.

---

## Content Architecture

### Page Type Hierarchy

All TMG content fits into one of five page types in a hub-and-spoke structure:

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
| **Pillar / GBP Category** | GBP category + Greenock (e.g. "Thai Massage Therapist Greenock") | `pillar-page-writer.md` |
| **Service Page** | Specific service + Greenock (e.g. "Traditional Thai Massage Greenock") | `service-page-writer.md` |
| **Location Page** | Service + area (e.g. "Thai Massage in Gourock") | `location-page-writer.md` |
| **Blog / Topical** | Topic or question keyword | `blog-post-writer.md` / `topical-writer.md` |

### Keyword Cannibalization Avoidance

Two pages must not target the same H1 keyword:

- Pillar page H1: `thai massage therapist Greenock` (GBP category)
- Service page H1: `traditional thai massage Greenock` (specific service)
- Pillar page H2: `Traditional Thai Massage` (no Greenock modifier)
- Location page H1: `thai massage Gourock` (geo-modified)

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

### One Primary Entity Per Page

Every page must have one clear primary entity:

- **Service page**: the treatment (e.g. *Thai massage*)
- **Location/geo page**: the area (e.g. *Gourock*)
- **Blog post**: the topic or question (e.g. *deep tissue massage for back pain*)

The primary entity must appear in the URL, H1, opening sentence, and title tag.

### 3–5 Secondary Entities

**TMG entity clusters to draw from:**

| Category | Entities |
|----------|---------|
| Treatments | Thai massage, Thai oil massage, aromatherapy massage, sports massage, facial massage, foot massage |
| Conditions | Muscle tension, back pain, neck pain, sports injury, poor posture, stress, chronic pain |
| Outcomes | Flexibility, range of motion, recovery, relaxation, pain relief |
| People | Certified massage therapist, Wat Po trained, Jariya Malone |
| Location | Greenock, Inverclyde, Gourock, Port Glasgow, Kilmacolm, Dunoon, South Street |

### Describe Entities, Don't Just Name Them

❌ Weak: "Thai massage helps with muscle tension."
✅ Strong: "Thai massage, a traditional technique using assisted stretching and acupressure along sen energy lines, releases deep muscle tension and improves joint mobility."

### Entity Co-occurrence

Place related entities close together:

- **Condition + treatment**: "neck pain" near "deep tissue massage"
- **Treatment + outcome**: "Thai massage" near "flexibility" and "range of motion"
- **Location + service**: "South Street" near "massage therapist"
- **Credential + service**: "Wat Po trained" near service name

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
- Do not link to the booking page in body content

---

## Schema Markup

All 5 content writers output a `<!-- SCHEMA -->` block with JSON-LD `@graph` containing:
- Primary type (`Article`, `BlogPosting`, `Service`, or `WebPage`)
- `FAQPage`
- `LocalBusiness` (TMG's NAP details)

### Local Entity Signals

- **NAP consistency**: Business name, address, and phone must be identical across website, Google Business Profile, and all directories.
- **Google Business Profile**: Accurate categories. Booking link. Service descriptions using entity language.
- **Reviews**: Encourage clients to mention specific treatments and results.

---

## Content Quality Standards

### E-E-A-T for TMG

- **Expertise**: Accurate, detailed information on massage treatments and conditions
- **Authoritativeness**: Reference Jariya's Wat Po training as a credibility signal
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
- [ ] Thai Massage Greenock brand voice maintained
- [ ] Clear call-to-action
