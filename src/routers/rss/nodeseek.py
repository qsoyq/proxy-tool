import logging
import httpx
from fastapi import APIRouter, Request, Response, Query, Path
from fastapi.responses import JSONResponse
import feedgen.feed
from dateparser import parse
from bs4 import BeautifulSoup as soup


router = APIRouter(tags=["Utils"], prefix="/rss/nodeseek/category")

logger = logging.getLogger(__file__)


@router.get("/{category}")
def newest(
    req: Request,
    session: str = Query(None, description="Cookie.session, 登陆可见的版块需要"),
    smac: str = Query(None, description="Cookie.smac, 登陆可见的版块需要"),
    category: str = Path(..., description="分类名称, 如tech"),
    cookie: str = Query("", description="完整 Cookie 字符串, 存在时无视 session 和 smac"),
):
    """Nodeseek 分类帖子新鲜出炉

    部分登陆可见的帖子，需要传递 smac 和 session 参数

    在网页控制台中输出当前域的 cookie: console.log(document.cookie);
    """
    host = req.url.hostname
    port = req.url.port
    if port is None:
        port = 80 if req.url.scheme == "http" else 443

    url = f"https://www.nodeseek.com/categories/{category}"
    headers = {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }
    cookies = {
        "colorscheme": "light",
        "session": session,
        "smac": smac,
        "sortBy": "postTime",
    }
    if cookie:
        cookies = {k: v for k, v in (item.split("=") for item in cookie.strip().split("; "))}
    resp = httpx.get(url, headers=headers, verify=False, cookies=cookies)
    if resp.is_error:
        return JSONResponse({"msg": resp.text}, status_code=resp.status_code)

    resp.raise_for_status()
    document = soup(resp.text, "lxml")
    post_list = document.select("div[class='post-list-content']")

    fg = feedgen.feed.FeedGenerator()
    fg.id("https://www.nodeseek.com/")
    fg.title("Nodeseek 分类 RSS 订阅")
    fg.subtitle("按发帖时间")
    fg.author({"name": "qsssssssss", "email": "support@19940731.xyz"})
    fg.link(href="https://www.nodeseek.com/", rel="alternate")
    fg.logo("https://www.nodeseek.com/static/image/favicon/favicon-32x32.png")
    fg.link(href=f"https://{host}:{port}/api/rss/nodessek/category/{category}", rel="self")
    fg.language("zh-CN")
    for item in post_list:
        a = item.select_one("div > a")
        if not a:
            continue
        href = f"https://www.nodeseek.com{a.attrs['href']}"  # type: ignore
        title = a.text
        datetime = parse(item.select_one("a[class='info-item info-last-comment-time'] > time").attrs["datetime"])  # type: ignore

        entry = fg.add_entry()
        entry.id(href)
        entry.title(title)
        entry.content("")
        entry.published(datetime)
        entry.link(href=href)
    rss_xml = fg.rss_str(pretty=True)
    return Response(content=rss_xml, media_type="application/xml")
