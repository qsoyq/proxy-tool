import logging
from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
import httpx


router = APIRouter(tags=["iptv"], prefix="/iptv")

logger = logging.getLogger(__file__)


@router.get("/subscribe", summary="订阅转换")
def sub(
    user_agent: str = Query("AptvPlayer/1.3.9", description="User-Agent"),
    urls: list[str] = Query(..., description="订阅地址"),
):
    content = ""
    texts = []
    for url in urls:
        resp = httpx.get(url, headers={"user-agent": user_agent})
        texts.append(resp.text)
    content = "\n".join(texts)
    return PlainTextResponse(content)
