import logging
from fastapi.responses import PlainTextResponse
import httpx
from fastapi import APIRouter, Query
from pydantic import HttpUrl
import yaml

router = APIRouter(tags=["stash"], prefix="/stash/stoverride")

logger = logging.getLogger(__file__)


@router.get("/override")
def Override(
    url: HttpUrl = Query(..., description="覆写文件订阅地址"),
    category: str = Query(..., description="分类名称"),
    icon: str | None = Query(None),
):
    """覆盖覆写文件"""
    logger.debug(f"url: {url}")
    res = httpx.get(str(url))
    res.raise_for_status()
    dom = yaml.safe_load(res.content)
    dom["category"] = category
    if icon is not None:
        dom["icon"] = icon
    content = yaml.safe_dump(dom, allow_unicode=True)
    return PlainTextResponse(content=content)
