import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future

import pytz
import feedgen.feed
from schemas.rss.jsonfeed import JSONFeed
from responses import PrettyJSONResponse
from fastapi import APIRouter, Request, Response, Query, Path

from routers.nga.thread import get_threads, Threads, Thread, OrderByEnum


router = APIRouter(tags=["RSS"], prefix="/rss/nga")

logger = logging.getLogger(__file__)


@router.get("/favor/{favorid}/v1", summary="NGA 收藏贴回复 RSS 订阅", include_in_schema=False)
def favorite(
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
    host = req.url.hostname
    port = req.url.port
    if port is None:
        port = 80 if req.url.scheme == "http" else 443

    threads = get_threads(uid, cid, favor=favorid)
    fg = feedgen.feed.FeedGenerator()
    fg.id("https://bbs.nga.cn/")
    fg.title("NGA 收藏夹 RSS 订阅")
    fg.subtitle("按回复时间")
    fg.author({"name": "qsssssssss", "email": "support@19940731.xyz"})
    fg.link(href="https://bbs.nga.cn/", rel="alternate")
    fg.logo("https://raw.githubusercontent.com/qsoyq/icons/main/assets/icon/nga.png")
    fg.link(href=f"https://{host}:{port}/api/rss/nga/favor/{favorid}", rel="self")
    fg.language("zh-CN")
    # 过滤权限不足/已过期的帖子
    threads.threads = [t for t in threads.threads if t.lastpost]
    for thread in threads.threads:
        entry = fg.add_entry()
        entry.id(f"{thread.tid}-{thread.lastpost}")
        entry.title(thread.subject)
        entry.content("")
        timezone = pytz.timezone("Asia/Shanghai")
        published = timezone.localize(datetime.fromtimestamp(thread.lastpost))
        entry.published(published)
        entry.link(href=thread.url)
    rss_xml = fg.rss_str(pretty=True)
    return Response(content=rss_xml, media_type="application/xml")


@router.get("/threads/v1", summary="NGA 分区新贴 RSS 订阅", include_in_schema=False)
def _threads(
    req: Request,
    fids: list[int] = Query(..., description="分区 id 列表"),
    uid: str = Query(..., description="ngaPassportUid, 验签"),
    cid: str = Query(..., description="ngaPassportCid, 验签"),
):
    """NGA分区订阅 RSS

    在网页控制台中输出当前域的 cookie: console.log(document.cookie);
    """
    host = req.url.hostname
    port = req.url.port
    if port is None:
        port = 80 if req.url.scheme == "http" else 443

    threads: list[Thread] = []

    with ThreadPoolExecutor() as executor:
        tasks: list[Future[Threads]] = []
        for fid in fids:
            t = executor.submit(
                get_threads,
                uid,
                cid,
                OrderByEnum.postdatedesc,
                fid=fid,
                favor=None,
                if_include_child_node=False,
                page=1,
            )
            tasks.append(t)
        for task in tasks:
            ret = task.result()
            threads.extend(ret.threads)

    fg = feedgen.feed.FeedGenerator()
    fg.id("https://bbs.nga.cn/")
    fg.title("NGA 分区 RSS 订阅")
    fg.subtitle("按创建时间")
    fg.author({"name": "qsssssssss", "email": "support@19940731.xyz"})
    fg.link(href="https://bbs.nga.cn/", rel="alternate")
    fg.logo("https://raw.githubusercontent.com/qsoyq/icons/main/assets/icon/nga.png")
    fg.link(href=f"https://{host}:{port}/api/rss/nga/threads", rel="self")
    fg.language("zh-CN")

    # 过滤权限不足/已过期的帖子
    threads = [t for t in threads if t.lastpost]
    for thread in threads:
        entry = fg.add_entry()
        entry.id(str(thread.tid))
        entry.title(thread.subject)
        entry.content("")
        timezone = pytz.timezone("Asia/Shanghai")
        published = timezone.localize(datetime.fromtimestamp(thread.lastpost))
        entry.published(published)
        entry.link(href=thread.url)
    rss_xml = fg.rss_str(pretty=True)
    return Response(content=rss_xml, media_type="application/xml")


@router.get(
    "/favor/{favorid}", summary="NGA 收藏贴回复 RSS 订阅", response_model=JSONFeed, response_class=PrettyJSONResponse
)
def favorite_jsonfeed(
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
    host = req.url.hostname

    threads = get_threads(uid, cid, favor=favorid)

    items: list = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "NGA 分区 RSS 订阅",
        "description": "按创建时间订阅指定分区的帖子",
        "home_page_url": "https://bbs.nga.cn/",
        "feed_url": f"{req.url.scheme}://{host}/api/rss/nga/threads?{req.url.query}",
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
    return feed


@router.get("/threads", summary="NGA 分区新贴 RSS 订阅", response_model=JSONFeed, response_class=PrettyJSONResponse)
def _threads_json(
    req: Request,
    fids: list[int] = Query(..., description="分区 id 列表"),
    uid: str = Query(..., description="ngaPassportUid, 验签"),
    cid: str = Query(..., description="ngaPassportCid, 验签"),
):
    """NGA分区订阅 RSS

    在网页控制台中输出当前域的 cookie: console.log(document.cookie);
    """
    host = req.url.hostname
    port = req.url.port
    if port is None:
        port = 80 if req.url.scheme == "http" else 443

    threads: list[Thread] = []

    with ThreadPoolExecutor() as executor:
        tasks: list[Future[Threads]] = []
        for fid in fids:
            t = executor.submit(
                get_threads,
                uid,
                cid,
                OrderByEnum.postdatedesc,
                fid=fid,
                favor=None,
                if_include_child_node=False,
                page=1,
            )
            tasks.append(t)
        for task in tasks:
            ret = task.result()
            threads.extend(ret.threads)

    items: list = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "NGA 分区 RSS 订阅",
        "description": "按创建时间订阅指定分区的帖子",
        "home_page_url": "https://bbs.nga.cn/",
        "feed_url": f"{req.url.scheme}://{host}/api/rss/nga/threads?{req.url.query}",
        "icon": "https://bbs.nga.cn/favicon.ico",
        "favicon": "https://bbs.nga.cn/favicon.ico",
        "items": items,
    }

    # 过滤权限不足/已过期的帖子
    threads = [t for t in threads if t.lastpost]
    for thread in threads:
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
    return feed
