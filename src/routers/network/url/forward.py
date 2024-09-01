import logging
import httpx

from fastapi import APIRouter, Query
from fastapi.responses import Response

router = APIRouter(tags=["network.url"], prefix="/network/url")

logger = logging.getLogger(__file__)


@router.get("/forward", summary="Forward")
def get(
    url: str = Query(..., description="待访问 url"),
    user_agent: str = Query(None, description="user-agent"),
    authorization: str = Query(None, description="Authorization"),
    accept: str = Query(None, description="Accept"),
):
    headers = {}
    if user_agent:
        headers["user-agent"] = user_agent

    if authorization:
        headers["authorization"] = authorization

    if accept:
        headers["accept"] = accept

    resp = httpx.get(url, headers=headers)
    headers = {}
    for field in ("content-type",):
        if field in resp.headers:
            headers[field] = resp.headers[field]
    return Response(resp.content, status_code=resp.status_code, headers=headers)
