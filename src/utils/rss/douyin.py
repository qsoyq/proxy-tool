import re
import random
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Any


import pytz


from schemas.rss.jsonfeed import JSONFeedItem
from utils import URLToolkit, ShelveStorage  # type: ignore
from utils.playwright import AsyncPlaywright
from settings import AppSettings


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


class DouyinPlaywright(AsyncPlaywright):
    WATCH_URL_PATH = "/web/aweme/post"


def to_feeds(username: str, body: dict, *, video_autoplay: bool = True) -> list[JSONFeedItem]:
    if not body["aweme_list"]:
        return []
    feeds: list[dict[str, Any]] = []
    author = body["aweme_list"][0]["author"]
    nickname = author["nickname"]
    user_avatar = author["avatar_thumb"]["url_list"][-1]
    feed_author = {
        "url": f"https://www.douyin.com/user/{username}",
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
            video_url = URLToolkit.make_video_tag_by_url(video_url, autoplay=video_autoplay)
            content_html = f"{content_html} {video_url}<br>"

        if not video_url and img:
            content_html = f"{content_html} {URLToolkit.make_img_tag_by_url(img)}<br>"

        if images:
            images = [URLToolkit.make_img_tag_by_url(img) for img in images]
            images = "<br>".join(images)
            content_html = f"{content_html} {images}<br>"

        date_published = int(post["create_time"])
        payload = {
            "id": f"douyin.user.{username}.{aweme_id}",
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


logger = logging.getLogger(__file__)

Headless = AppSettings().rss_douyin_user_headless
