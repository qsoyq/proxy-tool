import logging
import re

import httpx
from cachetools import FIFOCache
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse, RedirectResponse
from utils.cache import cached
from utils.douyin.video import AsyncDouyinVideoPlaywright, DouyinVideoTool

router = APIRouter(tags=["Utils"], prefix="/tool/url")

logger = logging.getLogger(__file__)


@router.get("/douyin/user/share", summary="抖音分享用户主页")
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


@router.get("/douyin/video/share", summary="抖音分享视频下载")
async def douyin_video_share_link(
    text: str = Query(
        ...,
        examples=[
            "4.30 复制打开抖音，看看【精灵宝可梦AI的作品】宝可梦纪录片-杰尼龟2 # 杰尼龟 # 水箭龟 #... https://v.douyin.com/TBM98eFZOHo/ K@w.sr NJI:/ 07/06"
        ],
    ),
    redirect: bool = Query(False, description="返回结果是否直接重定向, 默认返回纯文本"),
):
    """将抖音的视频分享链接转换为下载链接"""
    download_url = await get_douyin_video_download_link_by_cache(text)
    if redirect:
        return RedirectResponse(download_url)

    else:
        return PlainTextResponse(download_url)


@cached(FIFOCache(4096))
async def get_douyin_video_download_link_by_cache(text: str):
    tool = DouyinVideoTool()
    url = tool.get_video_link_from_share_text(text)
    if not url:
        raise ValueError(f"[get_douyin_video_download_link_by_cache] invalid share text: {text}")
    url = await tool.get_location_from_share_text_url(url)
    if not url:
        raise ValueError(f"[get_douyin_video_download_link_by_cache] invalid url, text: {text}")
    video_path = tool.get_share_url_video_path(url)

    url = f"https://www.douyin.com/video/{video_path}"
    play = AsyncDouyinVideoPlaywright(url)
    body = await play.run()
    assert isinstance(body, dict)
    return tool.to_download_url(body)
