import re
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Any


import pytz
from fastapi import APIRouter, Query, Path, Request, HTTPException
from playwright.async_api import async_playwright, Response
from playwright._impl._errors import TargetClosedError
from asyncache import cached
from cachetools import TTLCache

from schemas.rss.jsonfeed import JSONFeed, JSONFeedItem
from responses import PrettyJSONResponse
from utils import URLToolkit, ShelveStorage  # type: ignore
from settings import AppSettings


router = APIRouter(tags=["RSS"], prefix="/rss/douyin/user")

logger = logging.getLogger(__file__)

semaphore = asyncio.locks.Semaphore(AppSettings().rss_douyin_user_concurrency)


@dataclass(frozen=True)
class DouyinPlaywrightTask:
    username: str
    cookie: str


class AccessHistory:
    storage = ShelveStorage("~/.proxy-tool/rss.douyin.user.history")
    lock = asyncio.locks.Lock()

    @staticmethod
    async def get_history() -> list[DouyinPlaywrightTask]:
        async with AccessHistory.lock:
            items = await asyncio.to_thread(AccessHistory.storage.iterall)
        return [DouyinPlaywrightTask(*item) for item in items]

    @staticmethod
    async def append(username: str, cookie: str):
        async with AccessHistory.lock:
            await asyncio.to_thread(AccessHistory.storage.__setitem__, username, cookie)


class DouyinPlaywright:
    HISTORY: set[DouyinPlaywrightTask] = set()

    def __init__(
        self,
        username: str,
        cookie: str | None,
        user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        timeout: float = 10,
    ):
        self.fut: asyncio.Future[list[JSONFeedItem]] = asyncio.Future()
        self.feeds: list[JSONFeedItem] | None = None

        self.username = username
        self.cookie = cookie
        self.user_agent = user_agent
        self.timeout = timeout

    async def run(self) -> list[JSONFeedItem]:
        logger.debug("[rss.douyin.user] run")
        url = f"https://www.douyin.com/user/{self.username}"
        cookies = None
        if self.cookie:
            _cookies = [x.strip().split("=") for x in self.cookie.split(";") if x != ""]
            _cookies_dict = dict([x for x in _cookies if len(x) == 2])
            cookies = [{"name": k, "value": v, "url": "https://www.douyin.com"} for k, v in _cookies_dict.items()]

        async with async_playwright() as playwright:
            chromium = playwright.chromium
            browser = await chromium.launch(headless=True)
            browser = await browser.new_context(user_agent=self.user_agent)
            if cookies:
                await browser.add_cookies(cookies)  # type: ignore

            page = await browser.new_page()
            page.on("response", self.on_response)
            await page.goto(url)
            try:
                feeds = await asyncio.wait_for(self.fut, self.timeout)
                return feeds
            except asyncio.TimeoutError:
                logger.warning(f"[DouyinPlaywright] [run] 等待数据超时, 请检查用户 id: {self.username}")
                raise HTTPException(status_code=500, detail="等待数据超时, 请检查用户 id")
            finally:
                await browser.close()

    async def on_response(self, response: Response):
        try:
            if "/web/aweme/post" in response.url:
                try:
                    feeds = await self.to_feeds(response)
                    if not feeds:
                        logger.warning(f"not found feeds, username: {self.username}")

                    if self.fut and not self.fut.done():
                        self.fut.set_result(feeds)
                except Exception as e:
                    if self.fut and not self.fut.done():
                        self.fut.set_exception(e)

        except TargetClosedError as e:
            logger.warning(f"[rss.douyin.user] on_response: TargetClosedError {e}")

    async def to_feeds(self, response: Response) -> list[JSONFeedItem]:
        logger.debug("[rss.douyin.user] to_feeds")
        body = await response.json()
        if not body["aweme_list"]:
            return []
        feeds: list[dict[str, Any]] = []
        author = body["aweme_list"][0]["author"]
        nickname = author["nickname"]
        user_avatar = author["avatar_thumb"]["url_list"][-1]
        feed_author = {
            "url": f"https://www.douyin.com/user/{self.username}",
            "avatar": user_avatar,
            "name": nickname,
        }

        for post in body["aweme_list"]:
            video = post.get("video", {})
            bit_rate = video.get("bit_rate", [])
            video_url = None
            if bit_rate:
                video_url = bit_rate[0]["play_addr"]["url_list"][-1]

            duration = post.get("duration")
            if duration:
                duration /= 1000
            img = (
                video.get("cover", {}).get("url_list", [None])[-1]  # HD
                or video.get("origin_cover", {}).get("url_list", [None])[-1]  # LD
            )
            img = img and URLToolkit.resolve_url(img)

            aweme_id = post["aweme_id"]
            title = post["item_title"] or re.sub(r"#\w+", "", post["desc"]).strip() or post["desc"]
            url = f"https://www.douyin.com/video/{aweme_id}"
            desc_tags = {x.replace("#", "") for x in re.findall(r"#\w+", post["desc"])}
            video_tags = {x["tag_name"] for x in post["video_tag"] if x["tag_name"]}
            tags = list(video_tags | desc_tags)
            content_html = ""
            if img:
                img = URLToolkit.make_img_tag_by_url(img)
                content_html = f"{content_html} {img}"

            if video_url:
                video_url = URLToolkit.make_video_tag_by_url(video_url)
                content_html = f"{content_html} {video_url}"

            date_published = int(post["create_time"])
            payload = {
                "id": f"douyin.user.{self.username}.{aweme_id}",
                "title": title,
                "content_html": content_html,
                "url": url,
                "date_published": date_published,
                "tags": tags,
                "author": feed_author,
            }
            feeds.append(payload)

        feeds.sort(key=lambda x: -x["date_published"])
        for feed in feeds:
            feed["date_published"] = date_published = (
                pytz.timezone("Asia/Shanghai")
                .localize(datetime.fromtimestamp(feed["date_published"]))
                .strftime("%Y-%m-%dT%H:%M:%S%z")
            )
        logger.info(f"[DouyinPlaywright] [to_feeds] user: {nickname}")
        return [JSONFeedItem(**x) for x in feeds]


@cached(TTLCache(4096, AppSettings().rss_douyin_user_feeds_cache_time))
async def get_feeds_by_cache(username: str, cookie: str | None, timeout: float = 10) -> list[JSONFeedItem]:
    return await get_feeds(username, cookie, timeout)


async def get_feeds(username: str, cookie: str | None, timeout: float) -> list[JSONFeedItem]:
    if cookie:
        await AccessHistory.append(username, cookie)

    global semaphore
    async with semaphore:
        play = DouyinPlaywright(username=username, cookie=cookie, timeout=timeout)
        try:
            items = await asyncio.wait_for(play.run(), timeout * 2)
        except asyncio.TimeoutError as e:
            logger.warning("[rss.douyin.user] [get_feeds] timeout")
            raise e
    return items


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
):
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
    items = (
        await get_feeds_by_cache(username, cookie, timeout)
        if use_cache
        else await get_feeds(username, cookie, timeout)
    )
    if items:
        feed["title"] = items[0].author and items[0].author.name
    feed["items"] = items

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
):
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
    items = (
        await get_feeds_by_cache(username, cookie, timeout)
        if use_cache
        else await get_feeds(username, cookie, timeout)
    )
    if items:
        feed["title"] = items[0].author and items[0].author.name
    feed["items"] = items

    return feed
