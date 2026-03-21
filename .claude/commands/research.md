# Research Command

Conduct comprehensive SEO research and entity mapping before writing new content. Produces a research brief saved to `research/`.

## Usage
`/research [topic]`

## What This Command Does
1. Identifies the primary entity and maps secondary entities
2. Performs keyword research to find how people search for this entity
3. Analyses top-ranking competitor content
4. Identifies content gaps and opportunities
5. Creates a detailed research brief for writing

---

## Process

### Step 0: Social Research (do this before everything else)

Search Reddit and YouTube to capture what real users actually say — pain points, questions, and language patterns that SEO content never covers.

**Reddit searches** (run all 5):
- `site:reddit.com [topic]`
- `site:reddit.com [topic] help OR advice`
- `site:reddit.com [topic] experience OR review`
- `site:reddit.com [topic] recommend OR worth it`
- `site:reddit.com [topic] problem OR issue`

**YouTube searches** (run 2–3):
- `site:youtube.com [topic] guide`
- `site:youtube.com [topic] review 2024 OR 2025`

From results, extract and record:
- **Pain points**: What frustrations or problems come up repeatedly?
- **Real questions**: Questions people actually ask (not keyword-optimised)
- **User language**: Exact phrases and terminology real people use
- **Story seeds**: Specific scenarios or outcomes worth referencing
- **Content gaps**: What topics are underexplored or poorly answered in existing content?

---

### Step 1: Entity Mapping (do this first)

Before keyword research, establish the entity structure:

- **Primary entity**: The single concept this page is fundamentally about (one treatment, one location, one question)
- **Entity type**: Is it a Service, Place, Concept, Person, or Organisation?
- **Knowledge Panel check**: Search the primary entity on Google. What attributes does the Knowledge Panel show? What related entities appear in the panel?
- **People Also Ask**: Note which questions appear — these reveal the secondary entities Google associates with this topic
- **Secondary entities (3–5)**: Draw from the condition → treatment → outcome → location chain. Cross-reference with @clients/gtm/seo-guidelines.md entity clusters table
- **Co-occurrence pairs**: Identify 2–3 entity pairs to work into the copy naturally

### Step 2: Keyword Research

Keywords are how people search for the entity — not the writing target itself:

- **Primary keyword**: The most common search phrase for this entity
- **Search volume & difficulty**: Estimated monthly searches and competition level
- **Keyword variations**: Semantic variations and long-tail opportunities
- **Search intent**: Informational, navigational, commercial, or transactional
- **Related questions**: People Also Ask, forums — these often match secondary entities
- **Topic cluster fit**: How this piece fits into the GTM content cluster

### Step 3: Competitive Analysis

- **Top 10 SERP review**: Analyse the top 10 ranking pages for the target keyword
- **Common entities**: What concepts/entities do all top pages mention? These are required secondary entities
- **Content length**: Word count of top performers (benchmark target)
- **Content gaps**: What's missing from competitor coverage?
- **Featured snippets**: Is there a snippet opportunity? What format (paragraph, list, table)?
- **Unique angle**: What perspective or insight is underexplored?

### Step 4: GTM Context Integration

- **Brand alignment**: Check @clients/gtm/brand-voice.md for messaging and tone fit
- **Internal links**: Review @clients/gtm/internal-links-map.md for related pages to link
- **Target keywords**: Cross-reference with @clients/gtm/target-keywords.md priority list
- **SEO guidelines**: Confirm research aligns with @clients/gtm/seo-guidelines.md
- **Services**: Check @clients/gtm/features.md — are any services relevant to this topic?
- **Competitors**: Check @clients/gtm/competitor-analysis.md for any competitor intel on this topic

### Step 5: Content Planning

- **Recommended structure**: Outline H1, H2, and H3 headings based on research
- **Word count target**: Based on top 10 SERP averages
- **Entity placement plan**: Where each secondary entity fits naturally in the structure
- **Supporting evidence**: Statistics, studies, or data to include
- **Visual opportunities**: Images, diagrams, or screenshots needed
- **Internal links**: 3–5 GTM pages to link to (from internal-links-map.md)
- **External authority**: 2–3 authoritative external sources to cite

### Step 6: Hook Development

- **Opening angle**: Compelling way to open — question, statistic, or relatable scenario
- **Value proposition**: Clear benefit reader will get
- **Contrarian or unexpected angle**: Any surprising perspective to explore

---

## Output

Save to `research/brief-[topic-slug]-[YYYY-MM-DD].md` with these sections:

### 0. Social Research
- **Pain points**: [real frustrations from Reddit/YouTube]
- **User language**: [exact phrases real people use — use these in the copy]
- **Real questions**: [questions people actually ask, not keyword-optimised]
- **Story seeds**: [specific scenarios or outcomes worth weaving in]
- **Content gaps**: [topics underexplored in existing results]

### 1. Entity Map
- **Primary entity**: [entity name] — [entity type: Service/Place/Concept/etc.]
- **Secondary entities**: [list of 3–5 with category: treatment / condition / outcome / location / person]
- **Co-occurrence pairs**: [2–3 pairs to place near each other in copy]
- **Schema type**: [Service / FAQPage / Article / LocalBusiness]
- **Knowledge Panel attributes found**: [key attributes Google already knows]

### 2. SEO Foundation
- **Primary keyword**: [keyword] (volume, difficulty)
- **Secondary keywords**: 3–5 related keyword variations
- **Search intent**: [informational / commercial / transactional]
- **Target word count**: Minimum words needed to compete
- **Featured snippet opportunity**: Yes/No, format (paragraph, list, table)

### 3. Competitive Landscape
- **Top 3 competitor articles**: URLs and key takeaways from each
- **Required entities**: Concepts all top pages mention (must cover)
- **Content gaps**: Opportunities competitors miss
- **Differentiation strategy**: How GTM can stand out

### 4. Recommended Outline
```
H1: [Title — includes primary entity/keyword, under 60 chars]

Introduction
- Hook (question, stat, or scenario)
- Problem/condition this addresses
- Promise — what reader will learn

H2: [Main section 1 — secondary entity or co-occurrence angle]
H3: [Subsection if needed]

H2: [Main section 2]
...

Conclusion
- Key takeaways
- Soft CTA to book
```

### 5. Section Plan

Build a per-section writing plan using the research. For each H2 section:

| # | Type | Heading | Words | CTA | Hook |
|---|------|---------|-------|-----|------|
| 1 | intro | [H2 text] | 200 | soft | [hook idea from social research] |
| 2 | [type] | [H2 text] | [target] | — | [hook idea] |
| … | … | … | … | … | … |

**Section types**: `intro`, `body_explanation`, `body_how_to`, `body_list`, `body_comparison`, `faq`, `conclusion`

**Word targets by type**: intro 200 | explanation 300 | how-to 350 | list/comparison 400 | faq 250 | conclusion 200

**CTA distribution**: soft CTA in section 2, medium CTA at midpoint, strong CTA in conclusion

**Hook ideas**: draw from social research pain points and user language (Step 0) — not generic openings

### 6. Supporting Elements
- **Statistics to include**: 3–5 relevant data points with sources
- **Expert sources**: Potential references or quotes
- **Visual suggestions**: Screenshots, diagrams, or graphics needed

### 7. Internal Linking Plan
- **Pillar page**: Main GTM page to link to
- **Related articles**: 2–4 relevant blog posts to link
- **Service pages**: GTM service pages to mention naturally

### 8. Meta Elements Draft
- **Meta title**: Draft (50–60 characters, primary entity/keyword included)
- **Meta description**: Draft (150–160 characters, keyword + CTA)
- **URL slug**: Recommended URL

---

## Next Steps

The research brief feeds directly into:
1. `/write [topic]` — the brief is the foundation for the article
2. Reference during writing to stay on entity focus
3. Checklist to ensure all competitive gaps are addressed
