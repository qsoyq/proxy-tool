import logging
from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
import httpx


router = APIRouter(tags=["iptv"], prefix="/iptv")

logger = logging.getLogger(__file__)


@router.get("/subscribe", summary="订阅转换")
def sub(
    user_agent: str = Query("AptvPlayer/1.3.9", description="User-Agent"),
    timeout: float = Query(3, description="单个订阅地址的超时时间"),
    urls: list[str] = Query(..., description="订阅地址"),
):
    # todo: 异步并发
    content = ""
    texts = []
    for url in urls:
        try:
            resp = httpx.get(url, headers={"user-agent": user_agent}, timeout=timeout)
        except httpx.TimeoutException as e:
            logger.warning(f"fetch url {url} timeout: {e}")
        if resp.is_error:
            logger.warning(f"fetch url {url} error: {resp.status_code}, body: {resp.text}")
        else:
            texts.append(resp.text)
    content = "\n".join(texts)
    return PlainTextResponse(content)
