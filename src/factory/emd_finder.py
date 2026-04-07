"""EMD Finder — Find profitable niche+city combos with available exact-match domains.

Reuses:
    - DataForSEO.get_keyword_ideas() for niche keyword expansion
    - DataForSEO.get_serp_data() for competition analysis
    - OpportunityScorer.calculate_score() for profitability scoring
    - domain_api.py (new) for domain availability checking

Usage:
    python3 src/factory/emd_finder.py --niche "locksmith" --cities "Birmingham,Manchester,Leeds"
"""

from data_sources.modules.license import require_feature
require_feature('rankfactory')

# TODO: Phase 1, Step 1 — Implementation
# See plan: /Users/fred/.claude/plans/cozy-tinkering-orbit.md
