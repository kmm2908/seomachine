import json

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import ROOT, make_response, require_api_key, resolve_abbr

router = APIRouter()

_SECTION_MAX = {
    "schema": 20,
    "content": 20,
    "gbp": 20,
    "reviews": 15,
    "citations": 15,
    "technical": 10,
}


def _load_cached_audit(abbr: str) -> dict | None:
    cache = ROOT / "clients" / abbr.lower() / "audit-latest.json"
    if cache.exists():
        try:
            return json.loads(cache.read_text())
        except Exception:
            return None
    return None


def _format_audit(raw: dict) -> dict:
    sections = {}
    for key, max_pts in _SECTION_MAX.items():
        section_data = raw.get(key) or raw.get("nap") or {}
        if isinstance(section_data, dict):
            sections[key] = {
                "score": section_data.get("score", 0),
                "max": max_pts,
                "findings": section_data.get("findings", []),
            }
        else:
            sections[key] = {"score": 0, "max": max_pts, "findings": []}

    return {
        "date": raw.get("date"),
        "site_url": raw.get("site_url"),
        "total_score": raw.get("total_score", 0),
        "grade": raw.get("grade_letter", "F"),
        "sections": sections,
    }


@router.get("/latest")
def get_latest_audit(abbr: str, _: str = Depends(require_api_key)):
    resolve_abbr(abbr)
    raw = _load_cached_audit(abbr)
    if raw is None:
        raise HTTPException(
            status_code=404,
            detail=f"No audit cache found for '{abbr}'. Run: python3 src/audit/run_audit.py --abbr {abbr}"
        )
    return make_response(_format_audit(raw))
