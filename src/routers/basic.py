import json
import logging
from fastapi import Depends, APIRouter, Request
from deps import get_current_username

router = APIRouter(tags=["Basic"], prefix="/basic")

logger = logging.getLogger(__file__)


@router.get("/users/me", summary="获取当前用户")
def read_current_user(username: str = Depends(get_current_username)):
    return {"username": username}


@router.get("/whoami", summary="Who am i")
@router.post("/whoami", summary="Who am i")
@router.put("/whoami", summary="Who am i")
@router.delete("/whoami", summary="Who am i")
async def body(req: Request):
    headers = dict(req.headers)
    path = req.url.path
    query = req.url.query
    _json = {}
    scheme = req.url.scheme
    hostname = req.url.hostname
    port = req.url.port
    try:
        _json = await req.json()
    except json.JSONDecodeError as _:
        pass
    return {
        "headers": headers,
        "query": query,
        "json": _json,
        "path": path,
        "scheme": scheme,
        "hostname": hostname,
        "port": port,
    }
