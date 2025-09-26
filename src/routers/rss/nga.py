import asyncio
import logging
from datetime import datetime
from itertools import chain

import pytz
from schemas.rss.jsonfeed import JSONFeed
from responses import PrettyJSONResponse
from fastapi import APIRouter, Request, Query, Path

from utils.nga import NgaToolkit  # type: ignore
from schemas.nga.thread import Thread
from utils.cache import cached, RandomTTLCache
from utils.nga import OrderByEnum, Threads


router = APIRouter(tags=["RSS"], prefix="/rss/nga")

logger = logging.getLogger(__file__)


@router.get(
    "/favor/{favorid}", summary="NGA 收藏贴回复 RSS 订阅", response_model=JSONFeed, response_class=PrettyJSONResponse
)
async def favorite_jsonfeed(
    req: Request,
    favorid: int = Path(..., description="收藏夹ID"),
    uid: str = Query(..., description="ngaPassportUid, 验签"),
    cid: str = Query(..., description="ngaPassportCid, 验签"),
):
    """NGA 收藏帖子 RSS 订阅

    收藏夹id 见网页中的 favor 参数 https://bbs.nga.cn/thread.php?favor=1

    需要传递 ngaPassportUid 和 ngaPassportCid 参数

    在网页控制台中输出当前域的 cookie: console.log(document.cookie);
    """
    threads = await get_threads_by_cache(uid, cid, favor=favorid)
    items: list = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "NGA 分区 RSS 订阅",
        "description": "按创建时间订阅指定分区的帖子",
        "home_page_url": "https://bbs.nga.cn/",
        "feed_url": f"{req.url.scheme}://{req.url.hostname}/api/rss/nga/threads?{req.url.query}",
        "icon": "https://bbs.nga.cn/favicon.ico",
        "favicon": "https://bbs.nga.cn/favicon.ico",
        "items": items,
    }

    # 过滤权限不足/已过期的帖子
    threads.threads = [t for t in threads.threads if t.lastpost]
    for thread in threads.threads:
        timezone = pytz.timezone("Asia/Shanghai")
        published = timezone.localize(datetime.fromtimestamp(thread.lastpost))
        payload = {
            "id": f"{thread.tid}",
            "title": f"{thread.subject}",
            "url": thread.url,
            "date_published": published.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "content_text": "",
        }
        items.append(payload)

    thread_detail_list = await asyncio.gather(*[NgaToolkit.fetch_thread_detail(t["url"], cid, uid) for t in items])
    for index, detail in enumerate(thread_detail_list):
        if detail is None:
            continue
        author = detail.as_author()
        if author:
            items[index]["author"] = author
        if detail.content_html:
            items[index]["content_html"] = detail.content_html
            items[index]["content_text"] = None
    return feed


@router.get("/threads", summary="NGA 分区新贴 RSS 订阅", response_model=JSONFeed, response_class=PrettyJSONResponse)
async def threads_jsonfeed(
    req: Request,
    fids: list[int] = Query(..., description="分区 id 列表"),
    uid: str = Query(..., description="ngaPassportUid, 验签"),
    cid: str = Query(..., description="ngaPassportCid, 验签"),
):
    """NGA分区订阅 RSS

    在网页控制台中输出当前域的 cookie: console.log(document.cookie);
    """
    host = req.url.hostname
    tasks = [get_threads_by_cache(uid, cid, fid=fid, if_include_child_node=False) for fid in fids]
    res = await asyncio.gather(*tasks)

    threads: list[Thread] = list(chain(*[threads.threads for threads in res]))

    # 过滤权限不足/已过期的帖子
    threads = [t for t in threads if t.lastpost]

    items: list = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "NGA 分区 RSS 订阅",
        "description": "按创建时间订阅指定分区的帖子",
        "home_page_url": "https://bbs.nga.cn/",
        "feed_url": f"{req.url.scheme}://{host}{req.url.path}?{req.url.query}",
        "icon": "https://bbs.nga.cn/favicon.ico",
        "favicon": "https://bbs.nga.cn/favicon.ico",
        "items": items,
    }

    for thread in threads:
        timezone = pytz.timezone("Asia/Shanghai")
        published = timezone.localize(datetime.fromtimestamp(thread.postdate))
        payload = {
            "id": f"{thread.tid}",
            "title": f"{thread.subject}",
            "url": thread.url,
            "date_published": published.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "content_text": "",
        }
        items.append(payload)

    thread_detail_list = await asyncio.gather(*[NgaToolkit.fetch_thread_detail(t["url"], cid, uid) for t in items])
    for index, detail in enumerate(thread_detail_list):
        if detail is None:
            continue
        author = detail.as_author()
        if author:
            items[index]["author"] = author
        if detail.content_html:
            items[index]["content_html"] = detail.content_html
            items[index]["content_text"] = None
    return feed


@cached(RandomTTLCache(4096, 300))
async def get_threads_by_cache(
    uid: str | None = None,
    cid: str | None = None,
    order_by: OrderByEnum | None = OrderByEnum.lastpostdesc,
    *,
    fid: int | None = None,
    favor: int | None = None,
    if_include_child_node: bool | None = None,
    page: int = 1,
) -> Threads:
    return await NgaToolkit.get_threads(
        uid, cid, order_by=order_by, fid=fid, favor=favor, if_include_child_node=if_include_child_node, page=page
    )
