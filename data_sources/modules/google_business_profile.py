"""
Google Business Profile API Integration

Fetches business info, hours, reviews, and attributes from the Google Business
Profile API (formerly Google My Business).

=== SETUP: Google Cloud credentials ===

1. Google Cloud Console — enable these APIs on your project:
   - "My Business Business Information API"
   - "My Business Reviews API"
   - "My Business Account Management API"
   Search for them at console.cloud.google.com/apis/library

2. Service account credentials:
   - Create a service account at console.cloud.google.com/iam-admin/serviceaccounts
   - Download the JSON key and save to config/ (e.g. config/gbp-credentials.json)
   - The GBP_CREDENTIALS_PATH env var should point to this file

3. Grant the service account access to each business location:
   - In Google Business Profile Manager (business.google.com), go to the location
   - Settings → Managers → Add manager
   - Add the service account email (looks like name@project.iam.gserviceaccount.com)
   - Role: Manager (required for reviews; Owner for full access)

4. Find your location ID:
   - Use the Account Management API or GBP Manager URL
   - Format: numeric string, e.g. "123456789012345678"
   - Add to client config.json as: "gbp_location_id": "123456789012345678"

5. Required OAuth scope:
   https://www.googleapis.com/auth/business.manage

=== Cost ===
GBP API calls are free (no per-call billing). Rate limits apply.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import diskcache
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

# 30-day TTL for business info, hours, and attributes (slow-changing data)
_TTL_SLOW = 60 * 60 * 24 * 30
# 24-hour TTL for reviews (changes more frequently)
_TTL_REVIEWS = 60 * 60 * 24

_CACHE_DIR = Path(__file__).parent.parent / "cache" / "gbp"

_GBP_INFO_BASE = "https://mybusinessbusinessinformation.googleapis.com/v1"
_GBP_REVIEWS_BASE = "https://mybusiness.googleapis.com/v4"

_SCOPES = ["https://www.googleapis.com/auth/business.manage"]


class GoogleBusinessProfile:
    """Fetch data from the Google Business Profile API."""

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialise the GBP client.

        Args:
            credentials_path: Path to service account JSON key.
                              Falls back to GBP_CREDENTIALS_PATH env var.
            cache_dir: Override the default diskcache directory.
        """
        credentials_path = credentials_path or os.getenv("GBP_CREDENTIALS_PATH")

        if not credentials_path or not Path(credentials_path).exists():
            raise ValueError(
                f"GBP credentials file not found: {credentials_path!r}. "
                "Set GBP_CREDENTIALS_PATH in .env or pass credentials_path."
            )

        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=_SCOPES,
        )
        self._session = AuthorizedSession(credentials)
        self._cache = diskcache.Cache(str(cache_dir or _CACHE_DIR))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_business_info(self, location_id: str) -> Dict[str, Any]:
        """
        Fetch core business details for a GBP location.

        Returns a dict shaped for direct merge into a LocalBusiness JSON-LD node:
        {
            "name": "...",
            "telephone": "...",
            "url": "...",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "...",
                "addressLocality": "...",
                "addressRegion": "...",
                "postalCode": "...",
                "addressCountry": "..."
            },
            "description": "...",
            "categories": ["Primary Category", "Secondary Category", ...],
            "_raw_location_name": "locations/123..."   # GBP resource name
        }
        """
        cache_key = f"business_info:{location_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        resource = f"locations/{location_id}"
        read_mask = (
            "name,title,phoneNumbers,websiteUri,"
            "categories,profile,storefrontAddress"
        )
        url = f"{_GBP_INFO_BASE}/{resource}"

        data = self._get(url, params={"readMask": read_mask})
        if not data:
            return {}

        result = self._map_business_info(data)
        self._cache.set(cache_key, result, expire=_TTL_SLOW)
        return result

    def get_hours(self, location_id: str) -> Dict[str, Any]:
        """
        Fetch regular and special opening hours for a location.

        Returns:
        {
            "openingHoursSpecification": [
                {"@type": "OpeningHoursSpecification", "dayOfWeek": "Monday",
                 "opens": "09:00", "closes": "18:00"},
                ...
            ],
            "specialOpeningHoursSpecification": [
                {"@type": "OpeningHoursSpecification", "validFrom": "2026-12-25",
                 "validThrough": "2026-12-25", "opens": "00:00", "closes": "00:00"},
                ...
            ]
        }
        """
        cache_key = f"hours:{location_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        resource = f"locations/{location_id}"
        url = f"{_GBP_INFO_BASE}/{resource}"

        data = self._get(url, params={"readMask": "regularHours,specialHours,moreHours"})
        if not data:
            return {}

        result = self._map_hours(data)
        self._cache.set(cache_key, result, expire=_TTL_SLOW)
        return result

    def get_reviews(self, location_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch recent reviews for a location.

        Returns a list of:
        {
            "author": "...",
            "rating": 5,
            "text": "...",
            "published_date": "2026-03-15",
            "reply": "..."   # owner reply, or None
        }
        Sorted newest-first.
        """
        cache_key = f"reviews:{location_id}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        # Reviews endpoint uses the v4 API with accounts path
        # location_id here is the numeric ID; the v4 endpoint needs
        # the full resource name accounts/{id}/locations/{id}/reviews
        # We derive it from the location's resource name returned by info.
        info = self.get_business_info(location_id)
        raw_name = info.get("_raw_location_name", f"locations/{location_id}")
        # Expect raw_name like "accounts/123/locations/456" from info fetch
        # If we only have "locations/456" fall back gracefully
        reviews_resource = raw_name if raw_name.startswith("accounts/") else raw_name

        url = f"{_GBP_REVIEWS_BASE}/{reviews_resource}/reviews"
        data = self._get(url, params={"pageSize": min(limit, 50)})
        if not data:
            return []

        reviews = [
            self._map_review(r) for r in data.get("reviews", [])
        ]
        reviews = reviews[:limit]
        self._cache.set(cache_key, reviews, expire=_TTL_REVIEWS)
        return reviews

    def get_attributes(self, location_id: str) -> Dict[str, Any]:
        """
        Fetch location attributes (amenities, accessibility, service options, etc.).

        Returns:
        {
            "amenitiesOffered": ["Wi-Fi", "Parking"],
            "accessibilityFeature": ["Wheelchair accessible entrance"],
            "serviceOptions": ["By appointment only"],
            "_raw_attributes": [...]   # full GBP attribute list for reference
        }
        """
        cache_key = f"attributes:{location_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        url = f"{_GBP_INFO_BASE}/locations/{location_id}/attributes"
        data = self._get(url)
        if not data:
            return {}

        result = self._map_attributes(data)
        self._cache.set(cache_key, result, expire=_TTL_SLOW)
        return result

    # ------------------------------------------------------------------
    # Mapping helpers — GBP API → LocalBusiness JSON-LD shapes
    # ------------------------------------------------------------------

    def _map_business_info(self, data: Dict) -> Dict[str, Any]:
        address_raw = data.get("storefrontAddress", {})
        address_lines = address_raw.get("addressLines", [])

        result: Dict[str, Any] = {
            "name": data.get("title", ""),
            "telephone": "",
            "url": data.get("websiteUri", ""),
            "address": {
                "@type": "PostalAddress",
                "streetAddress": ", ".join(address_lines),
                "addressLocality": address_raw.get("locality", ""),
                "addressRegion": address_raw.get("administrativeArea", ""),
                "postalCode": address_raw.get("postalCode", ""),
                "addressCountry": address_raw.get("regionCode", ""),
            },
            "description": data.get("profile", {}).get("description", ""),
            "categories": [],
            "_raw_location_name": data.get("name", ""),
        }

        # Primary phone
        phone_numbers = data.get("phoneNumbers", {})
        primary = phone_numbers.get("primaryPhone", "")
        if primary:
            result["telephone"] = primary

        # Categories — primary first
        categories_data = data.get("categories", {})
        primary_cat = categories_data.get("primaryCategory", {})
        additional = categories_data.get("additionalCategories", [])
        cats = []
        if primary_cat.get("displayName"):
            cats.append(primary_cat["displayName"])
        for cat in additional:
            if cat.get("displayName"):
                cats.append(cat["displayName"])
        result["categories"] = cats

        return result

    def _map_hours(self, data: Dict) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "openingHoursSpecification": [],
            "specialOpeningHoursSpecification": [],
        }

        _day_map = {
            "MONDAY": "Monday",
            "TUESDAY": "Tuesday",
            "WEDNESDAY": "Wednesday",
            "THURSDAY": "Thursday",
            "FRIDAY": "Friday",
            "SATURDAY": "Saturday",
            "SUNDAY": "Sunday",
        }

        regular = data.get("regularHours", {}).get("periods", [])
        for period in regular:
            day_key = period.get("openDay", "")
            day = _day_map.get(day_key, day_key.capitalize())
            open_time = period.get("openTime", {})
            close_time = period.get("closeTime", {})
            opens = f"{open_time.get('hours', 0):02d}:{open_time.get('minutes', 0):02d}"
            closes = f"{close_time.get('hours', 0):02d}:{close_time.get('minutes', 0):02d}"
            result["openingHoursSpecification"].append({
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": day,
                "opens": opens,
                "closes": closes,
            })

        special = data.get("specialHours", {}).get("specialHourPeriods", [])
        for period in special:
            start = period.get("startDate", {})
            end = period.get("endDate", {}) or start
            valid_from = self._date_str(start)
            valid_through = self._date_str(end)
            spec: Dict[str, Any] = {
                "@type": "OpeningHoursSpecification",
                "validFrom": valid_from,
                "validThrough": valid_through,
            }
            if period.get("closed"):
                spec["opens"] = "00:00"
                spec["closes"] = "00:00"
            else:
                ot = period.get("openTime", {})
                ct = period.get("closeTime", {})
                spec["opens"] = f"{ot.get('hours', 0):02d}:{ot.get('minutes', 0):02d}"
                spec["closes"] = f"{ct.get('hours', 0):02d}:{ct.get('minutes', 0):02d}"
            result["specialOpeningHoursSpecification"].append(spec)

        return result

    def _map_review(self, review: Dict) -> Dict[str, Any]:
        reviewer = review.get("reviewer", {})
        reply = review.get("reviewReply", {})
        create_time = review.get("createTime", "")
        date_str = create_time[:10] if create_time else ""

        star_map = {
            "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5,
        }
        rating = star_map.get(review.get("starRating", ""), 0)

        return {
            "author": reviewer.get("displayName", ""),
            "rating": rating,
            "text": review.get("comment", ""),
            "published_date": date_str,
            "reply": reply.get("comment") if reply else None,
        }

    def _map_attributes(self, data: Dict) -> Dict[str, Any]:
        attributes = data.get("attributes", [])

        amenities: List[str] = []
        accessibility: List[str] = []
        service_options: List[str] = []

        for attr in attributes:
            attr_id: str = attr.get("name", "")
            values = attr.get("values", [])

            # Only include attributes that are explicitly true
            if not any(v is True or v == "true" for v in values):
                continue

            display = attr.get("displayName", attr_id)

            if "accessibility" in attr_id.lower():
                accessibility.append(display)
            elif "service" in attr_id.lower() or "appointment" in attr_id.lower():
                service_options.append(display)
            else:
                amenities.append(display)

        return {
            "amenitiesOffered": amenities,
            "accessibilityFeature": accessibility,
            "serviceOptions": service_options,
            "_raw_attributes": attributes,
        }

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------

    def _get(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        try:
            response = self._session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.warning("GBP API request failed: %s — %s", url, exc)
            return None

    @staticmethod
    def _date_str(date_dict: Dict) -> str:
        """Convert a GBP date object {year, month, day} to YYYY-MM-DD."""
        y = date_dict.get("year", 0)
        m = date_dict.get("month", 1)
        d = date_dict.get("day", 1)
        if not y:
            return ""
        return f"{y:04d}-{m:02d}-{d:02d}"


# ---------------------------------------------------------------------------
# Convenience factory — load credentials path from client config
# ---------------------------------------------------------------------------

def from_client_config(config: Dict, credentials_path: Optional[str] = None) -> GoogleBusinessProfile:
    """
    Instantiate GoogleBusinessProfile using a client config dict.

    The config must contain a top-level "gbp_location_id" key (optional — the
    caller can pass location_id directly to the individual methods).

    Example:
        gbp = from_client_config(config)
        info = gbp.get_business_info(config["gbp_location_id"])
    """
    return GoogleBusinessProfile(credentials_path=credentials_path)


# ---------------------------------------------------------------------------
# CLI smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    from pathlib import Path
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent.parent / ".env")

    location_id = os.getenv("GBP_TEST_LOCATION_ID", "")
    if not location_id:
        print("Set GBP_TEST_LOCATION_ID in .env to run the smoke test.")
    else:
        gbp = GoogleBusinessProfile()
        print("Business info:")
        print(json.dumps(gbp.get_business_info(location_id), indent=2))
        print("\nHours:")
        print(json.dumps(gbp.get_hours(location_id), indent=2))
        print("\nTop 5 reviews:")
        for r in gbp.get_reviews(location_id, limit=5):
            print(f"  {'★' * r['rating']} — {r['author']}: {r['text'][:80]}")
