"""Feature gate for premium SEO Machine add-ons."""

import json
import sys
from pathlib import Path


def load_license_config() -> dict:
    """Load license config from .env or config file."""
    config_path = Path(__file__).parent.parent.parent / 'license.json'
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {'plan': 'free', 'licensed_features': []}


def require_feature(feature: str):
    """Gate access to premium features. Call at the top of any premium command."""
    config = load_license_config()

    # Dev mode — if license.json doesn't exist, allow everything
    if config.get('plan') == 'dev':
        return

    if feature not in config.get('licensed_features', []):
        print(f"\n⚠️  '{feature}' requires SEO Machine Pro.")
        print(f"   Upgrade at seomachine.com/upgrade\n")
        sys.exit(1)


def has_feature(feature: str) -> bool:
    """Check if a feature is licensed without exiting."""
    config = load_license_config()
    if config.get('plan') == 'dev':
        return True
    return feature in config.get('licensed_features', [])
