# Research SERP Command

Deep SERP analysis for a specific keyword to understand what Google wants to see — content format, length, entities, and structure.

## Usage
`/research-serp "keyword phrase"`

## What This Command Does

Analyses the top 10 ranking results for a keyword to provide:
- Entity patterns — which concepts appear across all top pages
- Content type and structure (listicle, how-to, guide, etc.)
- Average word count and recommended length
- SERP features present (featured snippet, PAA, video, etc.)
- Search intent
- Competitive difficulty

---

## Process

### Step 1: Run the SERP analysis script

```bash
python3 research_serp_analysis.py "your target keyword"
```

This fetches the top 20 organic results from DataForSEO, analyses content patterns in the top 10, and generates a base report at `research/serp-analysis-[keyword].md`.

### Step 2: Entity extraction from top results (Claude does this)

After the script runs, review the top 5 ranking pages and extract:

- **Primary entity**: What single concept is every top page fundamentally about?
- **Common secondary entities**: Which concepts appear on 3 or more of the top 5 pages? These are required secondary entities for any page targeting this keyword.
- **Entity co-occurrence patterns**: Which entities appear near each other consistently?
- **Knowledge Panel check**: Search the primary entity — what attributes does Google show? These are the attributes your page should describe.
- **People Also Ask**: List the PAA questions. Each question reveals a secondary entity or attribute Google associates with this keyword.

---

## Output

The report includes:

### Entity Map for This SERP
- **Primary entity**: [entity name and type]
- **Required secondary entities**: Concepts appearing in 3+ of the top 5 pages
- **PAA entities**: Secondary entities revealed by People Also Ask questions
- **Recommended co-occurrence pairs**: Entity pairs to place near each other in copy
- **Schema type**: Recommended schema for a page targeting this keyword

### Content Requirements
- Recommended word count (top 10 average + 10%)
- Dominant content type (listicle, how-to, guide, definition, etc.)
- Content type distribution across top 10

### SERP Features
- Featured snippet opportunity and format
- People Also Ask questions (top 5)
- Video/image requirements
- Other SERP features present

### Content Brief
- Target specifications (word count, type, tone)
- Must-have elements (entities and topics that cannot be omitted)
- Recommended structure
- Freshness requirements

### Competitive Analysis
- Domain authority mix
- Difficulty assessment
- Timeframe expectations

---

## Integration

After running `/research-serp`:
- Use the entity map to inform `/research [topic]` entity planning
- Use `/write [keyword]` with the brief as foundation
- Ensure the entity list from Step 2 is included in the research brief

## Time & Cost

**Time:** 1–2 minutes for script + 5 minutes for entity extraction
**API Cost:** ~$0.02 per keyword (DataForSEO)

## When to Run

- **Before creating new content**: Understand what entity coverage is required
- **Before major updates**: Check if SERP entity patterns have shifted
- **When stuck on structure**: See what format and entity mix ranks
- **For competitive research**: Understand what you need to match or beat
