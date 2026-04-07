"""Rank Factory Orchestrator — Main pipeline from niche to live site.

Wires together: EMD finder → content planner → batch publisher

Reuses:
    - publish_topic() from publish_scheduled.py
    - generate_content() from geo_batch_runner.py
    - All 7 content type prompt builders

Usage:
    python3 src/factory/orchestrator.py --niche locksmith --city Birmingham
    python3 src/factory/orchestrator.py --domain locksmithbirmingham.com --niche locksmith --city Birmingham
    python3 src/factory/orchestrator.py --status
"""

from data_sources.modules.license import require_feature
require_feature('rankfactory')

# TODO: Phase 1, Step 5 — Wire EMD finder → content planner → publisher
