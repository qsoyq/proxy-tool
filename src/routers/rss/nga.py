import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future

import pytz
import feedgen.feed
from fastapi import APIRouter, Request, Response, Query, Path

from routers.nga.thread import get_threads, Threads, Thread, OrderByEnum


router = APIRouter(tags=["Utils"], prefix="/rss/nga")

logger = logging.getLogger(__file__)


@router.get("/favor/{favorid}")
def favorite(
    req: Request,
    favorid: int = Path(None, description="收藏夹ID"),
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
        entry.id(str(thread.tid))
        entry.title(thread.subject)
        entry.content("")
        timezone = pytz.timezone("Asia/Shanghai")
        published = timezone.localize(datetime.fromtimestamp(thread.lastpost))
        entry.published(published)
        entry.link(href=thread.url)
    rss_xml = fg.rss_str(pretty=True)
    return Response(content=rss_xml, media_type="application/xml")


@router.get("/threads")
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
