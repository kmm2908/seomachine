# Research Blog Topics Command

Generates prioritised blog topic ideas for a client using keyword research and competitor SERP analysis, then adds Claude's clustering and angle analysis on top.

## Usage
`/research-blog-topics [abbr]`

Examples:
- `/research-blog-topics gtb`
- `/research-blog-topics gtm --limit 30`
- `/research-blog-topics gtb --sheet` (also pushes to Google Sheet with status: pause)

## Steps

### Step 1 — Run the research script

Run the appropriate command based on what the user passed:

```bash
python3 src/research/research_blog_topics.py --abbr [abbr] [any extra flags]
```

If `--sheet` was included in the user's command, add it to the script call.

Print the console output so the user can see progress.

### Step 2 — Read the report

Read the generated report from `research/[abbr]/blog-topics-[today's date].md`.

### Step 3 — Claude analysis layer

Using the report data plus `clients/[abbr]/target-keywords.md` and `clients/[abbr]/brand-voice.md`, produce:

**A. Cluster groupings**
Group the topics into 4–6 thematic clusters (e.g. "Conditions & Pain Relief", "Thai Massage Explained", "Sports & Recovery", "Wellness & Lifestyle"). Show which topics fall into each cluster and why the cluster matters for topical authority.

**B. Top 5 picks with angles**
For the top 5 topics by score, suggest a specific content angle that differentiates from the competition — not just "write about X" but "here's the hook and the unique take".

**C. Content type split**
Identify which topics are better suited to `topical` (question-answering, evergreen) vs `blog` (conversational, seasonal, opinion-led). Flag any that could anchor a topic cluster as a pillar post.

**D. Cross-linking opportunities**
Note 3–4 natural internal linking chains across the topic list — e.g. "this blog post on X should link to this topical post on Y which links to the service page for Z".

**E. Publishing recommendation**
Suggest a publishing cadence based on the number of quality topics found (see guidance below), and confirm which ones are ready to add to the Sheet queue if `--sheet` wasn't already used.

## Publishing cadence guidance

Use this when making the publishing recommendation:

| Quality topics found | Suggested cadence | Posts per week |
|---------------------|-------------------|----------------|
| 30+ | 3× per week | 3 |
| 20–29 | 2× per week | 2 |
| 10–19 | 1× per week | 1 |
| < 10 | Fortnightly | 0.5 |

A "quality topic" is one with volume ≥ 50, competition ≤ 40%, and at least 1 competitor ranking in the SERP (proving demand exists). The script output shows these counts — use the table to set the cadence.

Note: the niche cache refreshes every 30 days, so the topic list is stable between runs. The research script should be re-run monthly to surface new opportunities as keyword trends shift.
