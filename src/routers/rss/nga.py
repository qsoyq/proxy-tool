import logging
from datetime import datetime
import pytz
from fastapi import APIRouter, Request, Response, Query, Path
import feedgen.feed
from routers.nga.thread import get_threads


router = APIRouter(tags=["Utils"], prefix="/rss/nga/favor")

logger = logging.getLogger(__file__)


@router.get("/{favorid}")
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
    fg.logo("https://bbs.nga.cn/favicon.ico")
    fg.link(href=f"https://{host}:{port}/api/rss/nga/favor/{favorid}", rel="self")
    fg.language("zh-CN")
    for thread in threads.threads:
        entry = fg.add_entry()
        entry.id(str(thread.fid))
        entry.title(thread.subject)
        entry.content("")
        timezone = pytz.timezone("Asia/Shanghai")
        published = timezone.localize(datetime.fromtimestamp(thread.lastpost))
        entry.published(published)
        entry.link(href=thread.url)
    rss_xml = fg.rss_str(pretty=True)
    return Response(content=rss_xml, media_type="application/xml")
