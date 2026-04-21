import json

from fastapi import APIRouter, Depends

from ..dependencies import ROOT, load_config, make_response, require_api_key

router = APIRouter()

_CLIENT_FIELDS = ("abbr", "abbreviation", "name", "website", "area", "niche")
_PROFILE_FIELDS = ("abbr", "abbreviation", "name", "website", "address", "postcode",
                   "phone", "booking_url", "area", "niche", "services")


def _abbr(cfg: dict) -> str:
    return (cfg.get("abbr") or cfg.get("abbreviation") or "").lower()


def _list_entry(cfg: dict) -> dict:
    return {k: cfg.get(k) for k in _CLIENT_FIELDS if cfg.get(k) is not None}


def _profile_entry(cfg: dict) -> dict:
    return {k: cfg.get(k) for k in _PROFILE_FIELDS if cfg.get(k) is not None}


@router.get("")
def list_clients(_: str = Depends(require_api_key)):
    clients = []
    for config_path in sorted((ROOT / "clients").glob("*/config.json")):
        try:
            cfg = json.loads(config_path.read_text())
            entry = _list_entry(cfg)
            if not entry.get("abbr") and not entry.get("abbreviation"):
                entry["abbr"] = config_path.parent.name
            clients.append(entry)
        except Exception:
            continue
    return make_response(clients)


@router.get("/{abbr}")
def get_client(abbr: str, _: str = Depends(require_api_key)):
    cfg = load_config(abbr)
    profile = _profile_entry(cfg)
    if not profile.get("abbr") and not profile.get("abbreviation"):
        profile["abbr"] = abbr.lower()
    return make_response(profile)
