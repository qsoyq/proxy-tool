import re
import logging
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import PlainTextResponse
import httpx


router = APIRouter(tags=["Utils"], prefix="/tool/url")

logger = logging.getLogger(__file__)


@router.get("/douyin/user/share")
async def douyin_user_share_link(
    text: str = Query(
        ...,
        examples=[
            "7- 长按复制此条消息，打开抖音搜索，查看TA的更多作品。 https://v.douyin.com/X8LSqawyHdg/ 3@8.com :8pm"
        ],
    ),
):
    """
    将如下的抖音分享消息解析为真实的用户主页地址
    """
    matched = re.search(r"https://v.douyin.com/.*/", text)
    if not matched:
        raise HTTPException(400, detail="无效的 url 参数")

    url = matched.group()
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        return PlainTextResponse(res.headers["Location"])
