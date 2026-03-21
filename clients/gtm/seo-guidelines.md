# SEO Guidelines for GTM Content

This document outlines SEO best practices and requirements for all GTM content to maximize organic search visibility and rankings.

---

## Content Architecture

### Page Type Hierarchy

All GTM content fits into one of five page types arranged in a hub-and-spoke structure:

```
GBP Category Pages (Pillar)
  └── Service Pages (Cluster)
        └── Location Pages (Area)
              └── Geo Pages (Postcode/Street)

Blog / Topical Articles (standalone, links into the above)
```

Each level links down to the next and back up to the one above. This builds topical authority and passes link equity through the site.

### Page Type Definitions

| Page Type | H1 Target | H2 Structure | H3 Structure | Agent |
|-----------|-----------|--------------|--------------|-------|
| **Pillar / GBP Category** | GBP category + Glasgow (e.g. "Thai Massage Therapist Glasgow") | Related services — variation only, not exact match of service page H1 | Use-cases / audience types within each H2 service | `pillar-page-writer.md` |
| **Service Page** | Specific service + Glasgow (e.g. "Traditional Thai Massage Glasgow") | Structural sections (What Is It, Benefits, Who It's For, What to Expect) | Sub-points within sections | `service-page-writer.md` |
| **Location Page** | Service + area (e.g. "Thai Massage in the West End, Glasgow") | Why this area, Services, Getting Here | Sub-points | `location-page-writer.md` |
| **Geo Page** | Service + postcode/street (e.g. "Thai Massage Near G2") | Area intro, Convenience, Trust | Sub-points | `geo-content-writer.md` |
| **Blog / Topical** | Topic or question keyword | Main sections | Sub-topics | `blog-post-writer.md` / `topical-writer.md` |

### Heading Hierarchy Rules

**H1**: One per page. Defines what the page ranks for. Must contain the primary target keyword.

**H2**: Supports the H1. On pillar pages, H2s are related services (using variations, not exact keyword matches from other pages). On service/geo/location pages, H2s are structural section titles.

**H3**: Sub-aspects of the H2 above — use-cases, audience types, or sub-topics. Never a separate service.

Correct H3 usage:
```
H2: Traditional Thai Massage
  H3: Thai Massage for Office Workers
  H3: Thai Massage for Sports Recovery
  H3: Thai Massage for Stress and Anxiety
```

Wrong H3 usage:
```
H2: Traditional Thai Massage
  H3: Thai Oil Massage        ← separate service, belongs in its own H2 or page
```

### Keyword Cannibalization Avoidance

Two pages must not target the same H1 keyword. The separation is:

- Pillar page H1: `thai massage therapist Glasgow` (GBP category)
- Service page H1: `traditional thai massage Glasgow` (specific service)
- Pillar page H2: `Traditional Thai Massage` (no Glasgow modifier — avoids competing with service page H1)
- Location page H1: `thai massage West End Glasgow` (geo-modified — separate from city-wide pages)

If two pages target the same H1 keyword, consolidate or redirect one.

### Outline-First Workflow

Before writing any content, confirm the structure:

```
Page type: [pillar / service / location / geo / blog]
H1: [primary keyword — exact text]
H2 sections:
  - [H2 text] → target keyword: [sub-keyword]
    - H3: [use-case or sub-topic]
    - H3: [use-case or sub-topic]
Semantic keywords: [list from target-keywords.md]
Secondary entities: [3-5 from entity cluster]
```

Confirm the outline before generating full content.

---

## Content Length Requirements

### Target Word Counts
- **Standard Blog Post**: 1,500-3,000 words (target: 2,000-2,500)
- **Pillar Content / Comprehensive Guides**: 3,000-5,000 words maximum
- **How-To Guides**: 1,500-2,500 words
- **News / Updates**: 800-1,200 words (exception to standard)

### Important Length Guidelines
- **Maximum for most articles**: 3,000 words
- **Maximum for pillar content**: 5,000 words
- If a topic requires more than the maximum, break it into a series of related articles
- Aim for the lower end of ranges when possible—concise, focused content often performs better

### Why Length Matters
- Longer content typically ranks higher in search results
- More words = more opportunities for keyword integration and topic coverage
- Comprehensive content earns more backlinks and engagement
- Depth signals expertise and authority to search engines

### Quality Over Quantity
- Don't add fluff just to hit word counts
- Every section should provide genuine value
- Better to have 2,000 valuable words than 3,000 padded words
- **Stay within the maximum word counts**—overly long articles hurt user experience

## Keyword Optimization

> **Note:** Keywords are a starting point for research, not the primary writing target. Entity optimisation (see next section) overrules keyword density rules. If following entity guidelines creates natural, varied writing that falls below the density targets below, that is correct — do not force keywords to hit a number.

### Keyword Research Requirements
Before writing any article:
1. Identify primary target keyword
2. Research search volume and difficulty
3. Analyze top 10 ranking competitors
4. Identify 3-5 secondary/related keywords
5. Identify 3–5 secondary entities (related concepts, conditions, outcomes — see Entity Optimisation section)

### Keyword Density Guidelines
- **Primary Keyword**: 1–1.5% density as a rough guide — prioritise natural integration over hitting a number. In a 2,000-word article that equates to roughly 20–30 uses, but exact match should vary across entity variations.
  - Natural integration is critical — never force keywords
- **Secondary Keywords**: 0.5-1% density each
- **Secondary entities**: Use naturally throughout — see Entity Optimisation section

### Critical Keyword Placement
Primary keyword MUST appear in:
- [ ] H1 headline (preferably near the beginning)
- [ ] First 100 words of article
- [ ] At least 2-3 H2 subheadings
- [ ] Last paragraph / conclusion
- [ ] Meta title (within first 60 characters)
- [ ] Meta description
- [ ] URL slug

### Keyword Integration Best Practices
- **Natural language first**: Write for humans, optimize for search engines
- **Use variations**: Don't repeat exact phrase robotically
  - Example: "podcast hosting" → "hosting your podcast" → "podcast host"
- **Question formats**: Include conversational variations
  - "How to start a podcast" vs "starting a podcast"
- **Semantic keywords**: Use related terms to support topical authority
  - For "podcast editing": include "audio editing", "post-production", "editing workflow"

### Keyword Stuffing (Avoid)
❌ "Podcast hosting is important. Podcast hosting helps podcasters. Our podcast hosting platform offers podcast hosting services for podcast hosting needs."

✅ "Podcast hosting is important for creators who want to distribute their show to major platforms. A reliable host ensures your episodes are accessible wherever listeners discover new content."

## Entity Optimisation

> **This section takes priority over keyword density rules.** When entity optimisation and keyword targets conflict, follow entity guidance.

Google no longer matches keywords as strings — it recognises **entities**: specific people, places, treatments, conditions, and concepts it has mapped in its Knowledge Graph. Writing for entities means making it obvious *what your page is about* and *how the concepts in it relate to each other*.

A page that clearly establishes "Thai massage → muscle tension → sports recovery → Glasgow City Centre" as a cluster of related entities will outrank a page that just repeats "thai massage Glasgow" at 1.5%. Entity clarity is the stronger signal.

### One Primary Entity Per Page

Every page must have one clear primary entity — the single concept the page exists to explain or promote.

- **Service page**: the treatment (e.g. *Thai massage*)
- **Location/geo page**: the area (e.g. *Finnieston, Glasgow*)
- **Blog post**: the topic or question (e.g. *deep tissue massage for back pain*)

The primary entity must appear in the URL, H1, opening sentence, and title tag.

### 3–5 Secondary Entities

Secondary entities are the related concepts that define, contextualise, and surround the primary entity. Choose them by:

1. Checking Google's Knowledge Panel (right sidebar) for your primary entity
2. Reviewing which terms appear consistently across the top 5 ranking pages for your target keyword
3. Thinking about the condition → treatment → outcome → location chain relevant to GTM

**GTM entity clusters to draw from:**

| Category | Entities |
|----------|---------|
| Treatments | Thai massage, deep tissue massage, sports massage, Swedish massage, hot stone massage |
| Conditions | Muscle tension, back pain, neck pain, sports injury, poor posture, stress, chronic pain |
| Outcomes | Flexibility, range of motion, recovery, relaxation, pain relief |
| People | Licensed massage therapist, sports therapist, holistic therapist |
| Location | Glasgow, City Centre, [specific district], [nearest subway station] |

### Describe Entities, Don't Just Name Them

Entity salience — how prominently Google scores an entity in your content — increases when you *describe an entity's attributes* rather than just naming it. Google's NLP reads the descriptor and the entity together.

❌ Weak: "Thai massage helps with muscle tension."
✅ Strong: "Thai massage, a traditional technique using assisted stretching and acupressure along sen energy lines, releases deep muscle tension and improves joint mobility."

The second version gives Google attributes (stretching, acupressure, energy lines) that confirm what Thai massage is and links it to secondary entities (muscle tension, joint mobility).

**Rule:** Every time you introduce a key entity for the first time in an article, give it one descriptive clause.

### Entity Co-occurrence

When two entities appear near each other more often than chance across the web, Google recognises them as semantically linked. Your content reinforces these links by placing related entities close together.

Useful co-occurrence patterns for GTM:

- **Condition + treatment**: "neck pain" near "deep tissue massage"
- **Treatment + outcome**: "Thai massage" near "flexibility" and "range of motion"
- **Location + service**: "Finnieston" near "massage therapist"
- **Credential + service**: "licensed therapist" near "sports massage"

Write sentences that naturally bring related entities into proximity — don't scatter them across disconnected sections.

**Example:** "For Glasgow office workers dealing with neck pain and shoulder tension from desk work, a weekly deep tissue massage session can restore range of motion and reduce chronic discomfort."

Entities in that sentence: Glasgow, office workers, neck pain, shoulder tension, desk work, deep tissue massage, range of motion, chronic discomfort. All relevant, all co-located.

### Entity Research Before You Write

Add this to your pre-writing research (in addition to keyword research):

1. **Google Knowledge Panel** — search your primary entity and study the panel. What attributes does Google already show? What related entities appear?
2. **"People also ask"** — these questions reveal which secondary entities Google associates with your topic
3. **Top 5 competitor pages** — what concepts do they all mention? Those are your validated secondary entities
4. *(Optional)* **Google's Natural Language API demo** (cloud.google.com/natural-language) — paste your draft and see which entities it recognises and their salience scores

### Schema Markup for GTM

Schema markup formally declares entities to Google. For GTM, the priority schemas are:

**LocalBusiness** (site-wide, in page template):
- Declares GTM as a recognisable local business entity
- Include: name, address, telephone, url, geo coordinates, opening hours

**Service** (on each service page):
- Declares each treatment as a named service entity
- Link it to the LocalBusiness as the provider

**Person** (therapist profile/about page):
- Declares the therapist(s) as credentialed individuals
- Include: name, jobTitle, hasCredential — supports E-E-A-T

**FAQPage** (where FAQs appear):
- Each Q&A defines and expands an entity — ideal for featured snippets

All schema should use JSON-LD format. Test at schema.org/validator before publishing.

### Local Entity Signals

For local SEO, entity signals extend beyond the website:

- **NAP consistency**: Business name, address, and phone number must be identical across the GTM website, Google Business Profile, Yelp, and any local directories. Inconsistencies fragment the entity in Google's model.
- **Google Business Profile**: Select accurate primary and secondary categories. Fill in all attributes (booking link, specialities, languages). Write a description that naturally uses service and condition entities.
- **Reviews**: Encourage clients to mention specific treatments and results. Google extracts entities from review text to build the business's service profile.

### Entity Pre-Writing Checklist

Before writing any GTM article, identify:

- [ ] Primary entity (one concept this page is fundamentally about)
- [ ] 3–5 secondary entities (related treatments, conditions, outcomes, location)
- [ ] 2–3 entity co-occurrence pairs to work into the copy
- [ ] Schema type for this page (Service / FAQPage / Article / LocalBusiness)

---

## Content Structure Requirements

### Heading Hierarchy

#### H1 (Title)
- **Only one H1 per article**
- Include primary keyword naturally
- 60 characters or less (for SERP display)
- Compelling and benefit-focused
- Should answer: "What will I learn/gain from this?"

#### H2 (Main Sections)
- **4-7 H2 sections** for standard articles
- At least **2-3 should include keyword variations**
- Descriptive and keyword-rich
- Logical progression through topic
- Can be standalone (readers should understand flow from H2s alone)

#### H3 (Subsections)
- Nested under H2s (never skip from H2 to H4)
- Break complex sections into digestible chunks
- Include keywords where natural
- More specific than H2s

### Article Structure Template

```markdown
# [H1: Compelling Title with Primary Keyword]

## Introduction (150-250 words)
- Hook: Attention-grabbing opening
- Problem: What challenge does this address?
- Promise: What will reader learn/achieve?
- Keyword in first 100 words

## [H2: Main Section 1 - Include Keyword Variation]
### [H3: Subsection if needed]
- Content depth
- Examples
- Data/statistics

## [H2: Main Section 2]
### [H3: Subsection if needed]
- Content depth
- Examples
- Data/statistics

## [H2: Main Section 3 - Include Keyword Variation]
### [H3: Subsection if needed]
- Content depth
- Examples
- Data/statistics

## [H2: Main Section 4]
[Continue with 4-7 total H2 sections]

## Conclusion (150-250 words)
- Recap key points (3-5 takeaways)
- Include keyword
- Clear call-to-action
- Next steps for reader
```

## Meta Elements

### Meta Title
**Requirements**:
- **Length**: 50-60 characters (including "| GTM" if used)
- **Primary keyword**: Must be included
- **Compelling**: Should encourage clicks from SERP
- **Unique**: Different from all other GTM page titles
- **Accurate**: Must match page content

**Format Options**:
- `[Primary Keyword]: [Benefit/Promise]`
- `How to [Goal] | [Qualifier]`
- `[Number] Ways to [Achieve Benefit]`
- `[Topic] Guide for [Audience] | GTM`

**Examples**:
- ✅ "How to Start a Podcast in 2025: Complete Guide"
- ✅ "12 Proven Podcast Growth Strategies | GTM"
- ❌ "Podcast Tips and Tricks" (too vague, no keyword)
- ❌ "The Ultimate Comprehensive Guide to Everything About Starting Your First Podcast Successfully" (too long)

### Meta Description
**Requirements**:
- **Length**: 150-160 characters
- **Primary keyword**: Include naturally
- **Value proposition**: Clear benefit to reader
- **Call-to-action**: Action phrase (Learn, Discover, Find out, Get, etc.)
- **Complete**: Must not cut off mid-sentence
- **Compelling**: Should drive clicks from SERP

**Formula**:
```
[Problem/Question]? [Solution/Benefit]. [Unique angle]. [CTA].
```

**Examples**:
- ✅ "Learn how to start a podcast with our step-by-step guide. Everything from equipment to launch strategy. Perfect for beginners. Start your show today." (159 chars)
- ✅ "Discover 12 proven podcast growth strategies that top creators use. Increase downloads, engagement, and audience loyalty. Actionable tips inside." (155 chars)
- ❌ "This is a blog post about podcasting where we discuss many podcast-related topics." (vague, no value prop, no CTA)

### URL Slug
**Requirements**:
- Include primary keyword
- Lowercase letters only
- Hyphens between words (not underscores)
- Short and descriptive (3-5 words ideal)
- No stop words unless necessary (a, the, and, of, etc.)

**Format**: `/blog/[primary-keyword-phrase]`

**Examples**:
- ✅ `/blog/start-podcast-guide`
- ✅ `/blog/podcast-growth-strategies`
- ✅ `/blog/podcast-editing-software`
- ❌ `/blog/how-to-start-a-podcast-in-2025-the-complete-guide` (too long)
- ❌ `/blog/post-12345` (no keywords)

## Internal Linking Strategy

### Requirements
- **Minimum**: 3 internal links per article
- **Optimal**: 4-5 internal links
- **Maximum**: 7 internal links (unless 3,000+ word article)

### Link Types to Include

#### 1. Pillar Content (1-2 links)
- Link to main comprehensive guides on related topics
- Builds topic cluster authority
- Usually 2,000+ word cornerstone content

#### 2. Related Blog Posts (2-3 links)
- Link to articles on related subtopics
- Creates content web
- Helps readers explore topics comprehensively

#### 3. Product/Feature Pages (0-1 link)
- Only when contextually relevant
- Natural mention of how GTM solves problem
- Never forced or overly promotional

#### 4. Resource Pages (0-1 link)
- Templates, tools, checklists
- When mentioned as solutions in content
- Provides additional value to reader

### Internal Linking Best Practices

**Anchor Text**:
- ✅ Descriptive and keyword-rich: "our complete guide to podcast analytics"
- ✅ Natural in sentence flow: "Learn more about podcast SEO strategies"
- ❌ Generic: "click here" or "read more"
- ❌ Exact match repeatedly: Always using same anchor text for same page

**Placement**:
- Within body paragraphs (most valuable)
- Natural context that adds value to reader
- Never more than 2 links per paragraph
- Distributed throughout article, not clustered

**Reference**:
- Always check @context/internal-links-map.md for priority linking targets
- Ensure links are current and functional
- Link to most relevant, up-to-date content

## External Linking Strategy

### Requirements
- **Minimum**: 2 external links per article
- **Optimal**: 3-4 external authority links
- Purpose: Add credibility, provide sources, support claims

### What to Link Externally
- **Statistics and data sources**: Always cite where numbers come from
- **Research and studies**: Link to original research
- **Tools and resources**: When recommending specific tools
- **Industry authorities**: Expert opinions or industry publications

### External Link Quality Standards
- **Authority**: Link to credible, well-known sources
  - ✅ Industry publications (Podcast Host, Podnews, etc.)
  - ✅ Research institutions and studies
  - ✅ Established media outlets
  - ❌ Random blogs with no authority
  - ❌ Spammy or low-quality sites

- **Relevance**: Links must directly support content claims
- **Freshness**: Prefer recent sources (within 1-2 years for data)
- **Functionality**: All links must work (no broken links)

### External Link Attributes
- Most external links: No special attributes needed
- Sponsored/affiliate links: Use `rel="sponsored"` or `rel="nofollow"`
- User-generated content: Use `rel="nofollow"`

## Readability Optimization

### Target Reading Level
- **Goal**: 8th-10th grade reading level (Flesch-Kincaid)
- Makes content accessible to wider audience
- Easier to scan and understand quickly

### Sentence Structure
- **Average length**: 15-20 words per sentence
- **Maximum**: 25 words (break longer sentences into two)
- **Variety**: Mix short punchy sentences with longer explanatory ones
- **Active voice**: Preferred over passive voice (80%+ active)

### Paragraph Structure
- **Length**: 2-4 sentences per paragraph
- **One idea**: Focus each paragraph on single point
- **White space**: No walls of text
- **Mobile-friendly**: Short paragraphs scan better on phones

### Formatting for Scannability
- **Subheadings**: Every 300-400 words
- **Lists**: Use bullets/numbers for sequential or multiple items
- **Bold**: Emphasize key concepts or takeaways
- **Short paragraphs**: Easier to digest
- **White space**: Makes content less intimidating

### Transition Words
Use transition words to improve flow (target: one per paragraph):
- Addition: Additionally, Furthermore, Moreover
- Contrast: However, On the other hand, Nevertheless
- Cause/Effect: Therefore, Consequently, As a result
- Example: For instance, For example, Specifically
- Time: First, Next, Finally

## Content Quality Standards

### Expertise, Authoritativeness, Trustworthiness (E-A-T)

#### Expertise
- Provide accurate, detailed information on podcasting topics
- Back claims with data and examples
- Demonstrate deep understanding of podcast creator needs
- Include actionable, practical advice

#### Authoritativeness
- Cite credible sources
- Reference industry data and trends
- Include expert quotes when relevant
- Leverage GTM's position as hosting platform

#### Trustworthiness
- Be transparent and honest
- Acknowledge limitations or challenges
- Don't overpromise results
- Cite sources for all statistics and claims
- Update outdated content regularly

### Content Originality
- **Never plagiarize**: All content must be original
- **Add unique value**: What perspective or insight do we add?
- **Fresh examples**: Use current, relevant examples
- **Updated data**: Use most recent statistics available
- **Unique angle**: Differentiate from competitor content

### Factual Accuracy
- **Verify statistics**: Check all numbers and data points
- **Current information**: Ensure practices/processes are up-to-date
- **Technical accuracy**: Podcasting terminology and processes must be correct
- **GTM features**: Ensure product references are accurate

## Image Optimization

### Image Requirements
- **Relevant**: Images should support content points
- **High-quality**: Professional appearance
- **Optimized**: Compressed for fast loading
- **Mobile-friendly**: Visible and useful on small screens

### Image SEO
**File Names**:
- Descriptive and keyword-rich
- ✅ `podcast-editing-software-interface.jpg`
- ❌ `IMG_12345.jpg`

**Alt Text**:
- Describe what image shows (accessibility + SEO)
- Include keywords naturally where relevant
- 125 characters or less
- ✅ "Podcast editing software interface showing waveform and timeline"
- ❌ "Image"

**Placement**:
- Break up long text sections
- Illustrate concepts being discussed
- After explaining concept, not before

## Featured Snippet Optimization

Featured snippets appear at position 0 in Google search results. Optimize for them when possible.

### Question-Based Snippets
- Include question as H2 heading
- Answer concisely in 40-60 words immediately after
- Use clear, direct language

**Example**:
```markdown
## What is Podcast Hosting?

Podcast hosting is a service that stores your audio files and generates an RSS feed that distributes your episodes to podcast platforms like Apple Podcasts, Spotify, and Google Podcasts. Without a host, listeners can't discover or access your show on their favorite apps.
```

### List-Based Snippets
- Use numbered or bulleted lists
- Keep items concise (1-2 sentences each)
- Include 5-8 items typically

### Table-Based Snippets
- Use HTML tables or markdown tables
- Comparison charts, pricing, specifications
- Clear headers and organized data

### Definition Snippets
- Define term in first sentence after heading
- 40-60 word clear, concise definition
- Expand with additional detail after

## Mobile Optimization

### Mobile-First Considerations
- **Short paragraphs**: 2-3 sentences max
- **Scannable**: Heavy use of subheadings and lists
- **Large fonts**: Readable without zooming
- **Tap-friendly links**: Adequate spacing
- **Fast loading**: Optimized images

## Content Refresh Strategy

### When to Update Content
- Article is 12+ months old
- Statistics or data are outdated
- Processes or best practices have changed
- Competitor content has surpassed ours
- Rankings have declined
- New relevant information available

### What to Update
- Publication date or "Last Updated" date
- Statistics with current data
- Screenshots with current versions
- Examples with recent case studies
- SEO elements (keyword focus may have shifted)
- Internal links to newer content

## SEO Checklist for Every Article

Before publishing, verify:

### Content
- [ ] 2,000+ words (or appropriate for content type)
- [ ] Primary keyword identified
- [ ] Keyword density 1-2%
- [ ] 3-5 secondary keywords included
- [ ] LSI keywords naturally integrated
- [ ] Provides unique value vs. competitors
- [ ] Factually accurate and current

### Structure
- [ ] One H1 with primary keyword
- [ ] 4-7 H2 sections
- [ ] 2-3 H2s include keyword variations
- [ ] Proper H1>H2>H3 hierarchy
- [ ] Keyword in first 100 words
- [ ] Keyword in conclusion

### Meta Elements
- [ ] Meta title 50-60 characters with keyword
- [ ] Meta description 150-160 characters with keyword & CTA
- [ ] URL slug includes primary keyword
- [ ] All meta elements are unique

### Links
- [ ] 3-5 internal links included
- [ ] Internal links use descriptive anchor text
- [ ] 2-3 external authority links
- [ ] All links functional (no broken links)
- [ ] Links add value to reader

### Readability
- [ ] 8th-10th grade reading level
- [ ] Average sentence length 15-20 words
- [ ] Paragraphs 2-4 sentences
- [ ] Subheadings every 300-400 words
- [ ] Lists used for scannability
- [ ] Active voice predominantly

### Images
- [ ] Relevant images included
- [ ] Descriptive file names
- [ ] Alt text with keywords
- [ ] Images optimized for web

### Quality
- [ ] No spelling or grammar errors
- [ ] Factually accurate
- [ ] Sources cited
- [ ] Brand voice maintained
- [ ] Provides actionable value
- [ ] Clear call-to-action

## SEO Tools & Resources

### Recommended Tools
- **Keyword Research**: Ahrefs, SEMrush, Google Keyword Planner
- **Content Analysis**: Clearscope, Surfer SEO, MarketMuse
- **Readability**: Hemingway Editor, Grammarly
- **Technical SEO**: Screaming Frog, Google Search Console
- **Rank Tracking**: Ahrefs, SEMrush, Google Search Console

### Reference Resources
- Google's Search Quality Evaluator Guidelines
- Moz Beginner's Guide to SEO
- Backlinko Blog (Brian Dean)
- Search Engine Journal
- Ahrefs Blog

---

**Remember**: SEO serves the user, not the algorithm. Never sacrifice content quality, accuracy, or helpfulness for keyword optimization. The best SEO is great content that genuinely helps podcast creators succeed.
