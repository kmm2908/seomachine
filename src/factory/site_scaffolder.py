"""Site Scaffolder — Bootstrap a new rank-and-rent client and provision hosting.

Phase 1: Client config bootstrapping only (manual hosting)
Phase 2: Full automated provisioning (Hetzner + WordOps + DNS)

Reuses:
    - clients/README.md config schema
    - research_competitors.py for competitor context
    - Claude API for brand-voice and seo-guidelines generation

Usage:
    python3 src/factory/site_scaffolder.py --domain locksmithbirmingham.com --niche locksmith --city Birmingham
"""

from data_sources.modules.license import require_feature
require_feature('rankfactory')

# TODO: Phase 1, Step 3 — Client bootstrapping
# TODO: Phase 2, Steps 6-8 — Hosting automation
