import re
import random
import time
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Any
from queue import Queue, Empty
import threading


import pytz

# from playwright.sync_api import Response
from playwright import sync_api
from playwright import async_api

# from playwright.async_api import async_playwright, Response
from playwright._impl._errors import TargetClosedError

from schemas.rss.jsonfeed import JSONFeedItem
from utils import URLToolkit, ShelveStorage  # type: ignore
from settings import AppSettings

logger = logging.getLogger(__file__)


Headless = AppSettings().rss_douyin_user_headless


class TimeoutException(Exception):
    pass


@dataclass(frozen=True)
class DouyinPlaywrightTask:
    username: str
    cookie: str


class AccessHistory:
    storage = ShelveStorage(AppSettings().rss_douyin_user_history_storage)
    lock = asyncio.Lock()

    @staticmethod
    async def get_history(shuffle: bool = True) -> list[DouyinPlaywrightTask]:
        async with AccessHistory.lock:
            with AccessHistory.storage:
                items = await asyncio.to_thread(AccessHistory.storage.iterall)

            result = [DouyinPlaywrightTask(*item) for item in items]
            if shuffle:
                random.shuffle(result)
            return result

    @staticmethod
    async def append(username: str, cookie: str):
        async with AccessHistory.lock:
            with AccessHistory.storage:
                await asyncio.to_thread(AccessHistory.storage.__setitem__, username, cookie)


class AsyncDouyinPlaywright:
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
        self._timeout = timeout
        self._start_ts = time.time()
        self._end_ts = self._start_ts + timeout

    @property
    def timeout(self) -> float:
        cur = time.time()
        if cur >= self._end_ts:
            return 0

        return self._end_ts - cur

    async def run(self) -> list[JSONFeedItem]:
        logger.debug(f"[DouyinPlaywright] run {self.username}")
        url = f"https://www.douyin.com/user/{self.username}"
        cookies = None
        if self.cookie:
            _cookies = [x.strip().split("=") for x in self.cookie.split(";") if x != ""]
            _cookies_dict = dict([x for x in _cookies if len(x) == 2])
            cookies = [{"name": k, "value": v, "url": "https://www.douyin.com"} for k, v in _cookies_dict.items()]
            logger.debug(f"[DouyinPlaywright] make cookies: {self.username}")
        async with async_api.async_playwright() as playwright:
            logger.debug(f"[DouyinPlaywright] enter playwright context: {self.username}")
            chromium = playwright.chromium
            browser = await chromium.launch(headless=Headless, timeout=self.timeout * 1000)
            logger.debug(f"[DouyinPlaywright] new browser: {self.username}")
            browser = await browser.new_context(user_agent=self.user_agent)
            logger.debug(f"[DouyinPlaywright] new context: {self.username}")
            if cookies:
                await browser.add_cookies(cookies)  # type: ignore

            page = await browser.new_page()
            logger.debug(f"[DouyinPlaywright] new page: {self.username}")
            page.on("response", self.on_response)

            try:
                logger.debug(f"[DouyinPlaywright] goto page: {self.username}")
                await asyncio.wait_for(page.goto(url, timeout=self.timeout * 1000), self.timeout)
                logger.debug(f"[DouyinPlaywright] wait for: {self.username}")
                feeds = await asyncio.wait_for(self.fut, self.timeout)
                logger.debug(f"[DouyinPlaywright] fetch feeds done, {self.username}")
                return feeds
            except asyncio.TimeoutError as e:
                logger.warning(f"[DouyinPlaywright] [run] 等待数据超时, 请检查用户 id: {self.username}")
                raise TimeoutException() from e
            finally:
                await browser.close()
                logger.debug(f"[DouyinPlaywright] close browser: {self.username}")

    async def on_response(self, response: async_api.Response):
        try:
            if "/web/aweme/post" in response.url:
                try:
                    logger.debug(f"[DouyinPlaywright] [on_response] {self.username} {response.request.method}")
                    feeds = await self.to_feeds(response)
                    if not feeds:
                        logger.warning(f"not found feeds, username: {self.username}")

                    if self.fut and not self.fut.done():
                        self.fut.set_result(feeds)
                except Exception as e:
                    if self.fut and not self.fut.done():
                        self.fut.set_exception(e)

        except TargetClosedError as e:
            logger.warning(f"[DouyinPlaywright] on_response: TargetClosedError {e}")

    async def to_feeds(self, response: async_api.Response) -> list[JSONFeedItem]:
        logger.debug(f"[DouyinPlaywright] [to_feeds] {self.username}")
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

            # 图文模式
            if post.get("iamges"):
                images: list[str] | str = [img["url_list"][0] for img in post.get("images", [])]
            else:
                images = []

            aweme_id = post["aweme_id"]
            title = post["item_title"] or re.sub(r"#\w+", "", post["desc"]).strip() or post["desc"]
            url = f"https://www.douyin.com/video/{aweme_id}"
            desc_tags = {x.replace("#", "") for x in re.findall(r"#\w+", post["desc"])}
            video_tags = {x["tag_name"] for x in post["video_tag"] if x["tag_name"]}
            tags = list(video_tags | desc_tags)
            content_html = ""
            if video_url:
                video_url = URLToolkit.make_video_tag_by_url(video_url)
                content_html = f"{content_html} {video_url}<br>"

            if not video_url and img:
                content_html = f"{content_html} {URLToolkit.make_img_tag_by_url(img)}<br>"

            if images:
                images = [URLToolkit.make_img_tag_by_url(img) for img in images]
                images = "<br>".join(images)
                content_html = f"{content_html} {images}<br>"

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

            if img:
                payload["image"] = img

            feeds.append(payload)

        feeds.sort(key=lambda x: -x["date_published"])
        for feed in feeds:
            feed["date_published"] = date_published = (
                pytz.timezone("Asia/Shanghai")
                .localize(datetime.fromtimestamp(feed["date_published"]))
                .strftime("%Y-%m-%dT%H:%M:%S%z")
            )
        leatest_date = feeds[0]["date_published"] if feeds else None
        logger.info(f"[DouyinPlaywright] [to_feeds] user: {nickname} {leatest_date}")
        return [JSONFeedItem(**x) for x in feeds]


class DouyinPlaywright:
    HISTORY: set[DouyinPlaywrightTask] = set()

    def __init__(
        self,
        username: str,
        cookie: str | None,
        user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        timeout: float = 10,
    ):
        self.queue: Queue[list[JSONFeedItem]] = Queue()
        self.cond = threading.Condition()
        self.exception: Exception | None = None
        self.feeds: list[JSONFeedItem] | None = None

        self.username = username
        self.cookie = cookie
        self.user_agent = user_agent
        self._timeout = timeout
        self._start_ts = time.time()
        self._end_ts = self._start_ts + timeout

    @property
    def timeout(self) -> float:
        cur = time.time()
        if cur >= self._end_ts:
            return 0

        return self._end_ts - cur

    def run(self) -> list[JSONFeedItem]:
        logger.debug(f"[DouyinPlaywright] run {self.username}")
        self.cond.acquire()
        url = f"https://www.douyin.com/user/{self.username}"
        cookies = None
        if self.cookie:
            _cookies = [x.strip().split("=") for x in self.cookie.split(";") if x != ""]
            _cookies_dict = dict([x for x in _cookies if len(x) == 2])
            cookies = [{"name": k, "value": v, "url": "https://www.douyin.com"} for k, v in _cookies_dict.items()]
            logger.debug(f"[DouyinPlaywright] make cookies: {self.username}")

        with sync_api.sync_playwright() as playwright:
            try:
                logger.debug(f"[DouyinPlaywright] enter playwright context: {self.username}")
                chromium = playwright.chromium
                browser = chromium.launch(headless=Headless, timeout=self.timeout * 1000)

                logger.debug(f"[DouyinPlaywright] new browser: {self.username}")
                browser = browser.new_context(user_agent=self.user_agent)
                logger.debug(f"[DouyinPlaywright] new context: {self.username}")

                if cookies:
                    browser.add_cookies(cookies)  # type: ignore

                page = browser.new_page()
                logger.debug(f"[DouyinPlaywright] new page: {self.username}")
                page.on("response", self.on_response)
                logger.debug(f"[DouyinPlaywright] goto page: {self.username}")
                page.goto(url, timeout=self.timeout * 1000)
                logger.debug(f"[DouyinPlaywright] wait for: {self.username}")
                self.cond.wait(timeout=self.timeout)

                if self.exception is not None:
                    raise self.exception

                feeds = self.queue.get(timeout=self.timeout)
                logger.debug(f"[DouyinPlaywright] fetch feeds done, {self.username}")
                return feeds
            except Empty as e:
                logger.warning(f"[DouyinPlaywright] [run] 等待数据超时, 请检查用户 id: {self.username}")
                raise TimeoutException() from e
            finally:
                browser.close()
                logger.debug(f"[DouyinPlaywright] close browser: {self.username}")

    def on_response(self, response: sync_api.Response):
        try:
            if "/web/aweme/post" in response.url:
                try:
                    logger.debug(f"[DouyinPlaywright] [on_response] {self.username} {response.request.method}")
                    feeds = self.to_feeds(response)
                    if not feeds:
                        logger.warning(f"not found feeds, username: {self.username}")
                    self.queue.put(feeds)
                except Exception as e:
                    self.exception = e
                finally:
                    self.cond.notify()

        except TargetClosedError as e:
            logger.warning(f"[DouyinPlaywright] on_response: TargetClosedError {e}")

    def to_feeds(self, response: sync_api.Response) -> list[JSONFeedItem]:
        logger.debug(f"[DouyinPlaywright] [to_feeds] {self.username}")
        body = response.json()
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

            # 图文模式
            if post.get("iamges"):
                images: list[str] | str = [img["url_list"][0] for img in post.get("images", [])]
            else:
                images = []

            aweme_id = post["aweme_id"]
            title = post["item_title"] or re.sub(r"#\w+", "", post["desc"]).strip() or post["desc"]
            url = f"https://www.douyin.com/video/{aweme_id}"
            desc_tags = {x.replace("#", "") for x in re.findall(r"#\w+", post["desc"])}
            video_tags = {x["tag_name"] for x in post["video_tag"] if x["tag_name"]}
            tags = list(video_tags | desc_tags)
            content_html = ""
            if video_url:
                video_url = URLToolkit.make_video_tag_by_url(video_url)
                content_html = f"{content_html} {video_url}<br>"

            if not video_url and img:
                content_html = f"{content_html} {URLToolkit.make_img_tag_by_url(img)}<br>"

            if images:
                images = [URLToolkit.make_img_tag_by_url(img) for img in images]
                images = "<br>".join(images)
                content_html = f"{content_html} {images}<br>"

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

            if img:
                payload["image"] = img

            feeds.append(payload)

        feeds.sort(key=lambda x: -x["date_published"])
        for feed in feeds:
            feed["date_published"] = date_published = (
                pytz.timezone("Asia/Shanghai")
                .localize(datetime.fromtimestamp(feed["date_published"]))
                .strftime("%Y-%m-%dT%H:%M:%S%z")
            )
        leatest_date = feeds[0]["date_published"] if feeds else None
        logger.info(f"[DouyinPlaywright] [to_feeds] user: {nickname} {leatest_date}")
        return [JSONFeedItem(**x) for x in feeds]
