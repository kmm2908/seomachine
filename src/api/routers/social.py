from fastapi import APIRouter, Depends

from ..dependencies import make_response, require_api_key, resolve_abbr

router = APIRouter()


@router.get("")
def get_social(abbr: str, _: str = Depends(require_api_key)):
    resolve_abbr(abbr)
    # GHL social accounts not yet connected — return empty state
    return make_response(
        {
            "pipeline_status": "idle",
            "last_run": None,
            "scheduled_posts": [],
            "recent": [],
        },
        note="Social accounts not yet connected in GHL",
    )
