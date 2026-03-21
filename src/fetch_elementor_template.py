"""
fetch_elementor_template.py
============================
One-time setup script. Fetches the saved Elementor template JSON from WordPress
and saves it to clients/{abbr}/elementor-template.json for use by the batch runner.

Usage:
    python3 fetch_elementor_template.py gtm
"""

import json
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENTS_DIR = Path(__file__).parent.parent / "clients"


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

    api_url = f"{url}/wp-json/wp/v2/elementor_library/{template_id}?context=edit"
    print(f"Fetching template {template_id} from {url}...")

    response = requests.get(api_url, auth=(username, app_password), timeout=30)

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
