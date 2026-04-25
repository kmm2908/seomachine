import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional

import requests

_ACTOR_ID = 'compass~google-maps-reviews-scraper'
_APIFY_URL = f'https://api.apify.com/v2/acts/{_ACTOR_ID}/run-sync-get-dataset-items'


def _send_alert(subject: str, body: str) -> None:
    smtp_host = os.getenv('GEO_EMAIL_SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('GEO_EMAIL_SMTP_PORT', '587'))
    smtp_user = os.getenv('GEO_EMAIL_SMTP_USER', '')
    smtp_pass = os.getenv('GEO_EMAIL_SMTP_PASS', '')
    email_from = os.getenv('GEO_EMAIL_FROM', smtp_user)
    email_to = os.getenv('GEO_EMAIL_TO', smtp_user).split(',')[0].strip()

    if not smtp_user or not smtp_pass:
        return

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = email_from
    msg['To'] = email_to

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception:
        pass


def get_response_rate(place_id: str, max_reviews: int = 100) -> Optional[float]:
    """
    Fetch Google Maps reviews via Apify and calculate owner response rate.

    Returns 0.0–1.0, or None if the API call fails or no reviews are found.
    Sends an email alert on authentication failures so the key can be renewed.
    Requires APIFY_API_KEY in environment.
    """
    api_key = os.getenv('APIFY_API_KEY')
    if not api_key:
        return None

    try:
        r = requests.post(
            _APIFY_URL,
            json={
                'placeIds': [place_id],
                'maxReviews': max_reviews,
                'reviewsSort': 'newest',
                'language': 'en',
            },
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=300,
        )
    except requests.Timeout:
        return None
    except Exception:
        return None

    if r.status_code == 401:
        _send_alert(
            'SEO Machine: Apify API key invalid or expired',
            f'Apify returned 401 for place_id {place_id}.\n\n'
            'Check APIFY_API_KEY in .env and renew if needed.\n'
            'Response rate scoring has been skipped for this audit run.',
        )
        return None

    if r.status_code not in (200, 201):
        return None

    try:
        reviews = r.json()
    except Exception:
        return None

    if not reviews:
        return None

    total = len(reviews)
    replied = sum(1 for rev in reviews if rev.get('responseFromOwnerText'))
    return replied / total
