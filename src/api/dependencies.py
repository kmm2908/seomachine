import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

ROOT = Path(__file__).parent.parent.parent

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str = Security(_api_key_header)) -> str:
    expected = os.getenv("PORTAL_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=500, detail="PORTAL_API_KEY not configured")
    if key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key


def resolve_abbr(abbr: str) -> Path:
    client_dir = ROOT / "clients" / abbr.lower()
    if not client_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Client '{abbr}' not found")
    config = client_dir / "config.json"
    if not config.exists():
        raise HTTPException(status_code=404, detail=f"No config.json for '{abbr}'")
    return client_dir


def load_config(abbr: str) -> dict:
    client_dir = resolve_abbr(abbr)
    return json.loads((client_dir / "config.json").read_text())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_response(data, **meta_extra) -> dict:
    meta = {"generated_at": now_iso(), **meta_extra}
    return {"data": data, "meta": meta}
