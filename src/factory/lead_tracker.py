"""Lead Tracker — Twilio call/form tracking setup per site.

Reuses:
    - twilio_tracker.py (new) for phone provisioning
    - Extends seomachine.php with [rnr_contact_form] shortcode

Usage:
    python3 src/factory/lead_tracker.py --abbr rnr-lkb --city Birmingham
"""

from data_sources.modules.license import require_feature
require_feature('rankfactory')

# TODO: Phase 3, Step 9 — Implementation
