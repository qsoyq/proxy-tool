import ssl
import logging
import urllib.parse
import cloudscraper
from fastapi import APIRouter, Request, Response, Query, Path
from fastapi.responses import JSONResponse
import feedgen.feed
from dateparser import parse
from bs4 import BeautifulSoup as soup
from responses import PrettyJSONResponse
from schemas.rss.jsonfeed import JSONFeed


router = APIRouter(tags=["RSS"], prefix="/rss/nodeseek/category")

logger = logging.getLogger(__file__)


@router.get("/{category}/v1", summary="Nodeseek 板块新贴 RSS 订阅", include_in_schema=False)
def newest(
    req: Request,
    session: str = Query(None, description="Cookie.session, 登陆可见的版块需要"),
    smac: str = Query(None, description="Cookie.smac, 登陆可见的版块需要"),
    category: str = Path(..., description="版块名称, 如tech"),
    cookie: str = Query("", description="完整 Cookie 字符串, 存在时无视 session 和 smac"),
    sortby: str = Query("postTime", description="排序方式, postTime、replyTime"),
):
    """Nodeseek 分类帖子新鲜出炉

    部分登陆可见的帖子，需要传递 smac 和 session 参数

    在网页控制台中输出当前域的 cookie: console.log(document.cookie);
    """
    host = req.url.hostname
    port = req.url.port
    if port is None:
        port = 80 if req.url.scheme == "http" else 443

    url = f"https://www.nodeseek.com/categories/{category}?sortBy={sortby}"
    cookies = {
        "colorscheme": "light",
        "session": session,
        "smac": smac,
        "sortBy": sortby,
    }
    if cookie:
        cookies = {k.strip(): v.strip() for k, v in (item.split("=") for item in cookie.strip().split("; "))}
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    scraper = cloudscraper.create_scraper(ssl_context=ssl_context)
    resp = scraper.get(url, cookies=cookies, verify=False)
    if not resp.ok:
        return JSONResponse({"msg": resp.text}, status_code=resp.status_code)

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
        ret = urllib.parse.urlparse(href)
        uid = ret.path.split("/")[-1].split("-")[1]

        entry = fg.add_entry()
        entry.id(uid)
        entry.title(f"{title}")
        entry.content("")
        entry.published(datetime)
        entry.link(href=href)
    rss_xml = fg.rss_str(pretty=True)
    return Response(content=rss_xml, media_type="application/xml")


@router.get(
    "/{category}", summary="Nodeseek 板块新贴 RSS 订阅", response_model=JSONFeed, response_class=PrettyJSONResponse
)
def newest_jsonfeed(
    req: Request,
    session: str = Query(None, description="Cookie.session, 登陆可见的版块需要"),
    smac: str = Query(None, description="Cookie.smac, 登陆可见的版块需要"),
    category: str = Path(..., description="版块名称, 如tech"),
    cookie: str = Query("", description="完整 Cookie 字符串, 存在时无视 session 和 smac"),
    sortby: str = Query("postTime", description="排序方式, postTime、replyTime"),
):
    """Nodeseek 分类帖子新鲜出炉

    部分登陆可见的帖子，需要传递 smac 和 session 参数

    在网页控制台中输出当前域的 cookie: console.log(document.cookie);
    """
    host = req.url.hostname
    port = req.url.port
    if port is None:
        port = 80 if req.url.scheme == "http" else 443

    url = f"https://www.nodeseek.com/categories/{category}?sortBy={sortby}"
    cookies = {
        "colorscheme": "light",
        "session": session,
        "smac": smac,
        "sortBy": sortby,
    }
    if cookie:
        cookies = {k.strip(): v.strip() for k, v in (item.split("=") for item in cookie.strip().split("; "))}
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    scraper = cloudscraper.create_scraper(ssl_context=ssl_context)
    resp = scraper.get(url, cookies=cookies, verify=False)
    if not resp.ok:
        return JSONResponse({"msg": resp.text}, status_code=resp.status_code)

    document = soup(resp.text, "lxml")
    post_list = document.select("li[class='post-list-item']")

    items: list = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "Nodeseek RSS 订阅",
        "description": f"{category}板块",
        "home_page_url": "https://nodeseek.com",
        "feed_url": f"{req.url.scheme}://{host}{req.url.path}?{req.url.query}",
        "icon": "https://www.nodeseek.com/static/image/favicon/android-chrome-512x512.png",
        "favicon": "https://www.nodeseek.com/static/image/favicon/android-chrome-512x512.png",
        "items": items,
    }
    for item in post_list:
        author = item.select_one("a")
        name = avatar = author_link = ""
        if author:
            img = author.select_one("img")
            if img:
                name = str(img.attrs["alt"])
                avatar = f'https://nodeseek.com{img.attrs["src"]}'
                author_link = f"https://nodeseek.com{author.attrs['href']}"
        _content = item.select_one("div[class='post-list-content']")
        if not _content:
            continue
        a = _content.select_one("div > a")
        if not a:
            continue
        href = f"https://www.nodeseek.com{a.attrs['href']}"  # type: ignore
        title = a.text
        _datetime = parse(item.select_one("a[class='info-item info-last-comment-time'] > time").attrs["datetime"])  # type: ignore
        ret = urllib.parse.urlparse(href)
        uid = ret.path.split("/")[-1].split("-")[1]

        payload = {
            "id": f"{uid}",
            "title": f"{title}",
            "url": href,
            "date_published": _datetime.strftime("%Y-%m-%d %H:%M:%S%Z") if _datetime else "",
            "content_text": "",
            "author": {"url": author_link, "avatar": avatar, "name": name},
        }

        items.append(payload)
    return feed
