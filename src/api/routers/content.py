import csv
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..dependencies import ROOT, make_response, require_api_key, resolve_abbr

router = APIRouter()


def _load_queues(abbr: str) -> list[dict]:
    research_dir = ROOT / "research" / abbr.lower()
    queues = []
    if not research_dir.is_dir():
        return queues
    for queue_file in sorted(research_dir.glob("*-queue.json")):
        try:
            data = json.loads(queue_file.read_text())
            queues.append({
                "queue_name": queue_file.stem,
                "cadence_days": data.get("cadence_days"),
                "topics": data.get("topics", []),
            })
        except Exception:
            continue
    return queues


def _queue_summary(queues: list[dict]) -> dict:
    counts = {"total": 0, "pending": 0, "published": 0, "review": 0, "failed": 0}
    for q in queues:
        for t in q.get("topics", []):
            status = t.get("status", "")
            counts["total"] += 1
            if status in ("published", "done"):
                counts["published"] += 1
            elif status in ("published_review", "review"):
                counts["review"] += 1
            elif status == "failed":
                counts["failed"] += 1
            else:
                counts["pending"] += 1
    return counts


@router.get("/queue")
def get_queue(
    abbr: str,
    status: Optional[str] = Query(None, description="Filter by status: pending|published|review|failed"),
    _: str = Depends(require_api_key),
):
    resolve_abbr(abbr)
    queues = _load_queues(abbr)

    if status:
        _status_map = {
            "published": {"published", "done"},
            "review": {"published_review", "review"},
            "failed": {"failed"},
            "pending": {"pending"},
        }
        keep = _status_map.get(status, {status})
        filtered = []
        for q in queues:
            topics = [t for t in q.get("topics", []) if t.get("status") in keep]
            if topics:
                filtered.append({**q, "topics": topics})
        queues = filtered

    return make_response({"queues": queues, "summary": _queue_summary(queues)})


@router.get("/published")
def get_published(
    abbr: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    content_type: Optional[str] = Query(None),
    _: str = Depends(require_api_key),
):
    resolve_abbr(abbr)
    log_path = ROOT / "logs" / "scheduled-publish-log.csv"

    items = []
    if log_path.exists():
        with log_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("abbr", "").lower() != abbr.lower():
                    continue
                if content_type and row.get("content_type") != content_type:
                    continue
                post_id = row.get("post_id", "").strip()
                items.append({
                    "date": row.get("date", "").strip(),
                    "topic": row.get("topic", "").strip(),
                    "content_type": row.get("content_type", "").strip(),
                    "status": row.get("status", "").strip(),
                    "post_id": int(post_id) if post_id.isdigit() else None,
                    "cost": row.get("cost", "").strip() or None,
                    "notes": row.get("notes", "").strip(),
                })

    total = len(items)
    page = items[offset: offset + limit]

    return make_response({"items": page}, total=total, limit=limit, offset=offset)
