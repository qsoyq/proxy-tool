import ssl
from typing import MutableMapping
import logging
import urllib.parse
import asyncio

import requests
import cloudscraper
import feedgen.feed
import contextvars

from fastapi import APIRouter, Request, Response, Query, Path, HTTPException
from fastapi.responses import JSONResponse
from dateparser import parse
from cachetools import TTLCache
from bs4 import BeautifulSoup as Soup

from responses import PrettyJSONResponse
from schemas.rss.jsonfeed import JSONFeed
from settings import AppSettings


router = APIRouter(tags=["RSS"], prefix="/rss/nodeseek/category")

logger = logging.getLogger(__file__)


class NodeseekToolkit:
    LOCK = asyncio.Lock()
    Semaphore = asyncio.Semaphore(1)
    NEXTWAIT = 2
    ONCE_FETCH_ARTICLE_CACHE_MAX = 50
    ArticlePostCache: MutableMapping[str, str] = TTLCache(4096, ttl=86400 * 3)
    LoginRequired: MutableMapping[str, bool] = TTLCache(4096, ttl=86400 * 3)
    GetOrCreate = contextvars.ContextVar("GetOrCreate", default=False)

    @staticmethod
    async def get_or_create_article_post_content(
        url: str, scraper: cloudscraper.CloudScraper, cookies: dict
    ) -> str | None:
        # 跳过要求登陆的 URL
        async with NodeseekToolkit.LOCK:
            if url in NodeseekToolkit.LoginRequired:
                logger.debug(f"{url} skip because of login required")
                return None

        # 从缓存读取
        content_html = None
        async with NodeseekToolkit.LOCK:
            content_html = NodeseekToolkit.ArticlePostCache.get("url")
            if content_html:
                logger.debug(f"[Nodessk RSS] read from cache for {url}")
                return str(content_html)

        if not NodeseekToolkit.GetOrCreate.get():
            return None

        # 请求网页，限制并发量，同时记录要求登陆的 URL
        try:
            async with NodeseekToolkit.Semaphore:
                content_html = await NodeseekToolkit.fetch_post_content_by_url(url, scraper, cookies)
                await asyncio.sleep(NodeseekToolkit.NEXTWAIT)
        except HTTPException as e:
            if e.status_code in (404, 403):
                async with NodeseekToolkit.LOCK:
                    NodeseekToolkit.LoginRequired[url] = True
                return None
            raise e

        # 根据请求结果写入缓存
        if content_html:
            async with NodeseekToolkit.LOCK:
                NodeseekToolkit.ArticlePostCache[url] = content_html
                logger.debug(f"[Nodessk RSS] set new cache for {url}")
        else:
            logger.warning(f"[Nodeseek RSS] can't fetch post content: {url}")
        return content_html

    @staticmethod
    def make_feeds_by_document(body: str) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        document = Soup(body, "lxml")
        post_list = document.select("li[class='post-list-item']")
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

            payload: dict[str, object] = {
                "id": f"{uid}",
                "title": f"{title}",
                "url": href,
                "date_published": _datetime.strftime("%Y-%m-%dT%H:%M:%S%z") if _datetime else "",
                "content_text": "",
                "author": {"url": author_link, "avatar": avatar, "name": name},
            }

            items.append(payload)
        return items

    @staticmethod
    async def fetch_post_content_by_url(url: str, scraper: cloudscraper.CloudScraper, cookies: dict) -> str | None:
        resp = await cloudscraper_get(scraper, url, cookies)
        if not resp.ok:
            raise HTTPException(resp.status_code, resp.text)

        document = Soup(resp.text, "lxml")
        article = document.select_one("article.post-content")
        return str(article) if article else None


async def cloudscraper_get(
    scraper: cloudscraper.CloudScraper, url: str, cookies: dict | None = None
) -> requests.Response:
    if cookies is None:
        cookies = {}

    if AppSettings().cloud_scraper_verify:
        return await asyncio.to_thread(scraper.get, url, cookies=cookies)

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    scraper = cloudscraper.create_scraper(ssl_context=ssl_context)
    return await asyncio.to_thread(scraper.get, url, cookies=cookies, verify=False)


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

    document = Soup(resp.text, "lxml")
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
async def newest_jsonfeed(
    req: Request,
    session: str = Query(None, description="Cookie.session, 登陆可见的版块需要"),
    smac: str = Query(None, description="Cookie.smac, 登陆可见的版块需要"),
    category: str = Path(..., description="版块名称, 如tech"),
    cookie: str = Query("", description="完整 Cookie 字符串, 存在时无视 session 和 smac"),
    sortby: str = Query("postTime", description="排序方式, postTime、replyTime"),
    get_or_create: bool = Query(False, description="contentHTML缓存策略, 是否在未命中缓存后拉取内容"),
):
    """Nodeseek 分类帖子新鲜出炉

    部分登陆可见的帖子，需要传递 smac 和 session 参数

    在网页控制台中输出当前域的 cookie: console.log(document.cookie);
    """
    token = NodeseekToolkit.GetOrCreate.set(get_or_create)
    url = f"https://www.nodeseek.com/categories/{category}?sortBy={sortby}"
    cookies = {
        "colorscheme": "light",
        "session": session,
        "smac": smac,
        "sortBy": sortby,
    }
    if cookie:
        cookies = {k.strip(): v.strip() for k, v in (item.split("=") for item in cookie.strip().split(";"))}

    scraper = cloudscraper.create_scraper()
    resp = await cloudscraper_get(scraper, url, cookies)
    if not resp.ok:
        return JSONResponse({"msg": resp.text}, status_code=resp.status_code)

    items = []
    feed: dict[str, str | list[dict[str, object]]] = {
        "version": "https://jsonfeed.org/version/1",
        "title": "Nodeseek RSS 订阅",
        "description": f"{category}板块",
        "home_page_url": "https://nodeseek.com",
        "feed_url": f"{req.url.scheme}://{req.url.hostname}{req.url.path}?{req.url.query}",
        "icon": "https://www.nodeseek.com/static/image/favicon/android-chrome-512x512.png",
        "favicon": "https://www.nodeseek.com/static/image/favicon/android-chrome-512x512.png",
        "items": [],
    }
    items = NodeseekToolkit.make_feeds_by_document(resp.text)
    count = 0
    for item in items:
        count += 1
        if count > NodeseekToolkit.ONCE_FETCH_ARTICLE_CACHE_MAX:
            break
        url = str(item["url"])

        try:
            content_html = await NodeseekToolkit.get_or_create_article_post_content(url, scraper, cookies)
        except HTTPException as e:
            if e.status_code == 429:
                logger.warning("[Nodeseek RSS] Request has reached the limit.")
            else:
                logger.warning(
                    f"[Nodeseek RSS] get_or_create_article_post_content failed, {e.status_code}, {e.detail}"
                )
            break

        if content_html:
            item["content_html"] = content_html
            item["content_text"] = None

    feed["items"] = items
    NodeseekToolkit.GetOrCreate.reset(token)
    return feed
