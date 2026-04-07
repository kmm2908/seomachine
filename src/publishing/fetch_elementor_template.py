"""
fetch_elementor_template.py
============================
One-time setup script. Fetches the saved Elementor template JSON from WordPress
and saves it to clients/{abbr}/elementor-template.json for use by the batch runner.

Also exposes refresh_if_stale() — called by the batch runner before each publish
to auto-update the local template if it has changed in WordPress.

Usage:
    python3 fetch_elementor_template.py gtm
"""

import json
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENTS_DIR = Path(__file__).parent.parent.parent / "clients"


def refresh_if_stale(abbr: str, wp_config: dict) -> bool:
    """
    Check if the local Elementor template is out of date and re-fetch if so.
    Returns True if the template was refreshed, False if already up to date.
    Silently skips if no template_id is configured or meta file is missing.
    """
    template_id = wp_config.get("elementor_template_id")
    if not template_id:
        return False

    meta_path = CLIENTS_DIR / abbr.lower() / "elementor-template-meta.json"
    if not meta_path.exists():
        return False  # No baseline stored — manual fetch required first

    try:
        stored_modified = json.loads(meta_path.read_text()).get("modified", "")
    except Exception:
        return False

    url = wp_config.get("url", "").rstrip("/")
    username = wp_config.get("username")
    app_password = wp_config.get("app_password")
    verify_ssl = not (url.endswith(".local") or "staging" in url)

    try:
        resp = requests.get(
            f"{url}/wp-json/wp/v2/elementor_library/{template_id}?_fields=modified",
            auth=(username, app_password),
            timeout=15,
            verify=verify_ssl,
        )
        resp.raise_for_status()
        wp_modified = resp.json().get("modified", "")
    except Exception as e:
        print(f"    → Template check failed (using cached): {e}")
        return False

    if wp_modified <= stored_modified:
        return False

    # Template has been updated — re-fetch
    print(f"    → Template updated in WordPress — re-fetching...")
    _fetch_and_save(abbr, wp_config)
    return True


def fetch_template(abbr: str) -> None:
    config_path = CLIENTS_DIR / abbr.lower() / "config.json"
    if not config_path.exists():
        print(f"Error: config not found at {config_path}")
        sys.exit(1)

    config = json.loads(config_path.read_text())
    wp = config.get("wordpress", {})

    url = wp.get("url", "").rstrip("/")
    username = wp.get("username")
    app_password = wp.get("app_password")
    template_id = wp.get("elementor_template_id")

    if not all([url, username, app_password, template_id]):
        print("Error: wordpress config must include url, username, app_password, and elementor_template_id")
        sys.exit(1)

    print(f"Fetching template {template_id} from {url}...")
    _fetch_and_save(abbr, wp)


def _fetch_and_save(abbr: str, wp: dict) -> None:
    """Fetch template from WP and save JSON + meta sidecar."""
    url = wp.get("url", "").rstrip("/")
    username = wp.get("username")
    app_password = wp.get("app_password")
    template_id = wp.get("elementor_template_id")

    api_url = f"{url}/wp-json/wp/v2/elementor_library/{template_id}?context=edit"
    verify_ssl = not (url.endswith(".local") or "staging" in url)
    response = requests.get(api_url, auth=(username, app_password), timeout=30, verify=verify_ssl)

    if response.status_code == 404:
        print(f"Error: template {template_id} not found. Check elementor_template_id in config.")
        sys.exit(1)

    response.raise_for_status()
    data = response.json()

    elementor_data_raw = data.get("meta", {}).get("_elementor_data")
    if not elementor_data_raw:
        print("Error: _elementor_data not found in response. Ensure the template has been saved in Elementor.")
        sys.exit(1)

    template = json.loads(elementor_data_raw)

    output_path = CLIENTS_DIR / abbr.lower() / "elementor-template.json"
    output_path.write_text(json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8")

    # Save sidecar with WP modified date for stale-check comparisons
    meta_path = CLIENTS_DIR / abbr.lower() / "elementor-template-meta.json"
    meta_path.write_text(json.dumps({"modified": data.get("modified", "")}, indent=2), encoding="utf-8")

    print(f"Saved to {output_path}")

    # Summary
    print(f"\nTemplate summary:")
    print(f"  Top-level sections: {len(template)}")
    widget = _find_html_widget(template)
    if widget:
        preview = widget.get("settings", {}).get("html", "")[:80].replace("\n", " ")
        print(f"  HTML widget found: yes")
        print(f"  Widget content preview: {preview!r}")
    else:
        print(f"  HTML widget found: NO — check template structure")


def _find_html_widget(elements: list) -> dict | None:
    """Depth-first search for the HTML injection target widget."""
    for element in elements:
        children = element.get("elements", [])
        if element.get("elType") == "widget" and element.get("widgetType") == "html":
            if "Paste HTML Here" in element.get("settings", {}).get("html", ""):
                return element
        result = _find_html_widget(children)
        if result:
            return result
    # Fallback: first html widget regardless of content
    return _find_first_html_widget(elements)


def _find_first_html_widget(elements: list) -> dict | None:
    for element in elements:
        if element.get("elType") == "widget" and element.get("widgetType") == "html":
            return element
        result = _find_first_html_widget(element.get("elements", []))
        if result:
            return result
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_elementor_template.py <client-abbr>")
        print("Example: python3 fetch_elementor_template.py gtm")
        sys.exit(1)
    fetch_template(sys.argv[1])
