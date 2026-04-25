import requests


def get_place_details(place_id: str, api_key: str) -> dict:
    """Fetch rating, review count, and recent reviews from Google Places API (New)."""
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "rating,userRatingCount",
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}
