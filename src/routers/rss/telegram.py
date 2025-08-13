import logging
import asyncio
from itertools import chain
from fastapi import APIRouter, Request, Query
from responses import PrettyJSONResponse
from schemas.rss.jsonfeed import JSONFeed
from utils import TelegramToolkit  # type:ignore


router = APIRouter(tags=["RSS"], prefix="/rss/telegram")

logger = logging.getLogger(__file__)


@router.get(
    "/channel", summary="Telegram Channel RSS Subscribe", response_model=JSONFeed, response_class=PrettyJSONResponse
)
async def channel_jsonfeed(
    req: Request,
    channels: list[str] = Query(..., description="channel name"),
    urlscheme: bool = Query(False, description="是否返回 URLScheme 直接跳转到 App"),
):
    """Telegram Channel RSS Subscribe"""
    try:
        token = TelegramToolkit.URLScheme.set(urlscheme)
        host = req.url.hostname
        items: list = []
        feed = {
            "version": "https://jsonfeed.org/version/1",
            "title": "Telegram Channel RSS Subscribe",
            "description": "",
            "home_page_url": "https://t.me",
            "feed_url": f"{req.url.scheme}://{host}{req.url.path}?{req.url.query}",
            "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Telegram.png",
            "favicon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Telegram.png",
            "items": items,
        }
        feed_icon = None
        feed_title = None
        tasks = await asyncio.gather(*[TelegramToolkit.get_channel_messages(channelName) for channelName in channels])
        for message in chain(*tasks):
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
            if message.head and feed_icon is None:
                feed_icon = message.head

            if message.authorName and feed_title is None:
                feed_title = message.authorName

            if message.photoUrls:
                payload["image"] = message.photoUrls[0]
                payload["banner_image"] = message.photoUrls[0]

                photosOuterHTML = ""
                for url in message.photoUrls:
                    tag = TelegramToolkit.generate_img_tag(url)
                    photosOuterHTML = f"{photosOuterHTML}{tag}"
                payload["content_html"] = f"{photosOuterHTML}{payload['content_html']}"

            items.append(payload)

        if feed_title is not None:
            feed["title"] = feed_title

        if feed_icon is not None:
            feed["icon"] = feed_icon
            feed["favicon"] = feed_icon

    except Exception as e:
        raise e
    finally:
        TelegramToolkit.URLScheme.reset(token)
    return feed
