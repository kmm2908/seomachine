"""
PDF Generator — converts HTML to PDF via Playwright.

Requires:  pip install playwright && playwright install chromium
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_pdf(html_content: str, output_path: Path) -> bool:
    """
    Render html_content to a PDF file using Playwright (headless Chromium).

    Returns True on success, False on failure (caller can decide what to do).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error(
            'Playwright not installed. Run:\n'
            '  pip install playwright\n'
            '  playwright install chromium'
        )
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html_content, wait_until='networkidle')
            page.pdf(
                path=str(output_path),
                format='A4',
                print_background=True,
                margin={
                    'top': '0',
                    'bottom': '0',
                    'left': '0',
                    'right': '0',
                },
            )
            browser.close()
        logger.info(f'PDF saved to {output_path}')
        return True
    except Exception as e:
        logger.error(f'PDF generation failed: {e}')
        return False
