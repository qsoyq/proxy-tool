import asyncio
import logging
from typing import cast

from fastapi import APIRouter, Query, Path, Request, HTTPException

from schemas.rss.jsonfeed import JSONFeed, JSONFeedItem
from responses import PrettyJSONResponse
from utils.rss.douyin import TimeoutException, AccessHistory, AsyncDouyinPlaywright
from asyncache import cached
from settings import AppSettings
from utils.cache import RandomTTLCache

rss_douyin_user_semaphore = asyncio.locks.Semaphore(AppSettings().rss_douyin_user_semaphore)

router = APIRouter(tags=["RSS"], prefix="/rss/douyin/user")

logger = logging.getLogger(__file__)


@router.get(
    "/{username:str}",
    summary="抖音用户作品订阅",
    response_model=JSONFeed,
    response_class=PrettyJSONResponse,
)
async def user(
    req: Request,
    username: str = Path(
        ..., description="用户主页 id", examples=["MS4wLjABAAAAv4fFOLeoSQ9g8Mnc0mfPq0P6Gm14KBm2-p5sNVsdXhM"]
    ),
    timeout: float = Query(10, description="执行抖音内容抓取的超时时间"),
    use_cache: bool | None = Query(True, description="是否从缓存返回"),
    autoplay: bool = Query(True, description="是否为video 标签添加 autoplay 属性"),
):
    """
    <pre class="mermaid">
        flowchart TB
            A[请求抖音用户作品数据开始] --> B{是否存在未过期的缓存?}
            B -->|YES| C[返回缓存结果]
            B -->|NO| D[超时检测上下文]
            D -->|超时| E[返回 504 超时响应]
            D -->|未超时| D2[无头浏览器Playwright]
            subgraph 无头浏览器获取用户作品
                direction LR
                D2-->F[打开用户主页]
                F -->|监听/web/aweme/post| G[获取用户作品数据]
                G --> H[生成 Feeds 数据]
                H --> I[写入缓存结果]
                H --> J[构造 JSONFeed]
            end
            J --> K[返回200]
    </pre>
    """
    items: list[JSONFeedItem] = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "抖音用户作品RSS订阅",
        "description": "",
        "home_page_url": f"https://www.douyin.com/user/{username}",
        "feed_url": f"{req.url.scheme}://{req.url.hostname}{req.url.path}?{req.url.query}",
        "icon": "https://www.douyin.com/favicon.ico",
        "favicon": "https://www.douyin.com/favicon.ico",
        "items": items,
    }
    cookie = None
    try:
        items = (
            await get_feeds_by_cache(username, cookie, timeout=timeout, video_autoplay=autoplay)
            if use_cache
            else await get_feeds(username, cookie, timeout, video_autoplay=autoplay)
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="获取数据超时")
    except TimeoutException:
        raise HTTPException(status_code=504, detail="获取数据超时")
    douyin_user_feeds_handler(feed, items)

    return feed


@router.get(
    "/{username:str}/{sessionid_ss:str}",
    summary="抖音用户作品订阅",
    response_model=JSONFeed,
    response_class=PrettyJSONResponse,
)
async def user_with_cookie(
    req: Request,
    username: str = Path(
        ..., description="用户主页 id", examples=["MS4wLjABAAAAv4fFOLeoSQ9g8Mnc0mfPq0P6Gm14KBm2-p5sNVsdXhM"]
    ),
    sessionid_ss: str = Path(..., description="用户 Cookie"),
    timeout: float = Query(10, description="执行抖音内容抓取的超时时间"),
    use_cache: bool | None = Query(True, description="是否从缓存返回"),
    autoplay: bool = Query(True, description="是否为video 标签添加 autoplay 属性"),
):
    """
    <pre class="mermaid">
        flowchart TB
            A[请求抖音用户作品数据开始] --> B{是否存在未过期的缓存?}
            B -->|YES| C[返回缓存结果]
            B -->|NO| D[超时检测上下文]
            D -->|超时| E[返回 504 超时响应]
            D -->|未超时| D2[无头浏览器Playwright]
            subgraph 无头浏览器获取用户作品
                direction LR
                D2-->F[打开用户主页]
                F -->|监听/web/aweme/post| G[获取用户作品数据]
                G --> H[生成 Feeds 数据]
                H --> I[写入缓存结果]
                H --> J[构造 JSONFeed]
            end
            J --> K[返回200]
    </pre>
    """
    items: list[JSONFeedItem] = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "抖音用户作品RSS订阅",
        "description": "",
        "home_page_url": f"https://www.douyin.com/user/{username}",
        "feed_url": f"{req.url.scheme}://{req.url.hostname}{req.url.path}?{req.url.query}",
        "icon": "https://www.douyin.com/favicon.ico",
        "favicon": "https://www.douyin.com/favicon.ico",
        "items": items,
    }
    cookie = f"sessionid_ss={sessionid_ss}"
    try:
        items = (
            await get_feeds_by_cache(username, cookie, timeout=timeout, video_autoplay=autoplay)
            if use_cache
            else await get_feeds(username, cookie, timeout, video_autoplay=autoplay)
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="获取数据超时")
    except TimeoutException:
        raise HTTPException(status_code=504, detail="获取数据超时")
    douyin_user_feeds_handler(feed, items)
    return feed


def douyin_user_feeds_handler(feed: dict, items: list[JSONFeedItem]):
    if items and items[0].author:
        feed["title"] = items[0].author.name
        feed["author"] = items[0].author

    if items and items[0].author and items[0].author.avatar:
        feed["icon"] = feed["favicon"] = items[0].author.avatar

    for item in items:
        if item.image and item.author:
            item.author.avatar = item.image
    feed["items"] = items


@cached(RandomTTLCache(4096, AppSettings().rss_douyin_user_feeds_cache_time))
async def get_feeds_by_cache(
    username: str, cookie: str | None, *, timeout: float = 10, video_autoplay: bool
) -> list[JSONFeedItem]:
    return await get_feeds(username, cookie, timeout, video_autoplay=video_autoplay)


async def get_feeds(username: str, cookie: str | None, timeout: float, video_autoplay: bool) -> list[JSONFeedItem]:
    async with rss_douyin_user_semaphore:
        if cookie:
            await AccessHistory.append(username, cookie)

        play = AsyncDouyinPlaywright(username=username, cookie=cookie, timeout=timeout, video_autoplay=video_autoplay)
        items = await play.run()
        return cast(list[JSONFeedItem], items)
