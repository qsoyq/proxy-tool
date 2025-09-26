import logging
import asyncio
from itertools import chain

import markdown
from fastapi import APIRouter, Request, Query
from responses import PrettyJSONResponse
from schemas.rss.jsonfeed import JSONFeed, JSONFeedItem
from utils import TelegramToolkit  # type:ignore
from asyncache import cached
from utils.cache import RandomTTLCache


router = APIRouter(tags=["RSS"], prefix="/rss/telegram")

logger = logging.getLogger(__file__)


@router.get(
    "/channel", summary="Telegram Channel RSS Subscribe", response_model=JSONFeed, response_class=PrettyJSONResponse
)
async def channel_jsonfeed(req: Request, channels: list[str] = Query(..., description="channel name")):
    """Telegram Channel RSS Subscribe"""
    items = await fetch_feeds(channels)
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "Telegram Channel RSS Subscribe",
        "description": "",
        "home_page_url": "https://t.me",
        "feed_url": f"{req.url.scheme}://{req.url.hostname}{req.url.path}?{req.url.query}",
        "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Telegram.png",
        "favicon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Telegram.png",
        "items": items,
    }
    for item in items:
        if item.author and item.author.avatar:
            feed["icon"] = item.author.avatar
            feed["favicon"] = item.author.avatar
            break

    for item in items:
        if item.author and item.author.name:
            feed["title"] = item.author.name
            break
    return feed


async def fetch_feeds(channels: list[str]) -> list[JSONFeedItem]:
    items = []
    tasks = await asyncio.gather(*[get_channel_messages(channelName) for channelName in channels])
    for message in chain(*tasks):
        if message.contentHtml:
            try:
                message.contentHtml = markdown.markdown(message.contentHtml)
            except Exception as e:
                logger.warning(f"convert markdown to html failed: {e}")
        payload = {
            "id": f"{message.channelName}-{message.msgid}",
            "title": f"{message.title}",
            "url": f"https://t.me/{message.channelName}/{message.msgid}",
            "date_published": message.updated,
            "content_html": message.contentHtml or "",
            "tags": message.tags,
            "author": {
                "avatar": message.head,
                "name": message.channelName,
                "url": f"https://t.me/{message.channelName}",
            },
        }

        if message.photoUrls:
            payload["image"] = message.photoUrls[0]
            payload["banner_image"] = message.photoUrls[0]
            photosOuterHTML = ""
            for url in message.photoUrls:
                tag = TelegramToolkit.generate_img_tag(url)
                photosOuterHTML = f"{photosOuterHTML}{tag}"
            payload["content_html"] = f"{photosOuterHTML}{payload['content_html']}"

        items.append(JSONFeedItem(**payload))

    return items


@cached(RandomTTLCache(4096, 900))
async def get_channel_messages(channelName: str):
    return await TelegramToolkit.get_channel_messages(channelName)
