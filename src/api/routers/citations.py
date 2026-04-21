import json

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import ROOT, make_response, require_api_key, resolve_abbr

router = APIRouter()


def _citations_dir(abbr: str) -> object:
    return ROOT / "clients" / abbr.lower() / "citations"


def _summarise_sites(sites: dict) -> dict:
    counts = {"listed": 0, "not_found": 0, "pending_verification": 0, "manual_required": 0, "total": 0}
    for site in sites.values():
        counts["total"] += 1
        status = site.get("status", "")
        submit = site.get("submit_status", "")
        if status == "found":
            counts["listed"] += 1
        elif status == "not_found":
            counts["not_found"] += 1
        if submit == "pending_verification":
            counts["pending_verification"] += 1
        if submit == "manual_required":
            counts["manual_required"] += 1
    return counts


@router.get("")
def get_citations(abbr: str, _: str = Depends(require_api_key)):
    resolve_abbr(abbr)
    state_path = _citations_dir(abbr) / "state.json"
    if not state_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No citation data for '{abbr}'. Run: python3 src/citations/run_citations.py --abbr {abbr}"
        )

    raw = json.loads(state_path.read_text())
    sites_raw = raw.get("sites", {})

    sites = []
    for site_id, site_data in sites_raw.items():
        sites.append({
            "site_id": site_id,
            "site_name": site_data.get("found_name") or site_id.replace("_", " ").title(),
            "status": site_data.get("status"),
            "listing_url": site_data.get("listing_url"),
            "nap_match": site_data.get("nap_match"),
            "submit_status": site_data.get("submit_status"),
            "last_checked": site_data.get("last_checked"),
        })

    return make_response({
        "last_run": raw.get("last_run"),
        "summary": _summarise_sites(sites_raw),
        "sites": sites,
    })


@router.get("/gaps")
def get_citation_gaps(abbr: str, _: str = Depends(require_api_key)):
    resolve_abbr(abbr)
    gaps_path = _citations_dir(abbr) / "gap-results.json"
    if not gaps_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No gap analysis for '{abbr}'. Run: python3 src/citations/run_citations.py --abbr {abbr} --competitor-gaps"
        )

    return make_response(json.loads(gaps_path.read_text()))
