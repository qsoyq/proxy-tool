import logging
from typing import Any
from typing import cast
from fastapi import APIRouter, Request, Query, Path
from schemas.rss.jsonfeed import JSONFeed, JSONFeedItem
from utils.f50 import SMS
from schemas.f50 import Message


router = APIRouter(tags=["RSS"], prefix="/rss/f50")

logger = logging.getLogger(__file__)


@router.get("/sms/{password}", summary="F50 短信 RSS 订阅", response_model=JSONFeed)
async def sms_list(
    req: Request,
    password: str = Path(..., description="编码后的字符串"),
    number: str | None = Query(None, description="按照号码过滤"),
):
    """f50 短信订阅"""
    items: list[JSONFeedItem] = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "F50 - 短信订阅",
        "description": "",
        "home_page_url": "http://192.168.0.1/index.html",
        "feed_url": f"{req.url.scheme}://{req.url.hostname}{req.url.path}?{req.url.query}",
        "icon": "https://www.zte.com.cn/favicon.ico",
        "favicon": "https://www.zte.com.cn/favicon.ico",
        "items": items,
    }

    sms = SMS(password)
    await sms.login()
    messages: list[Message] = await sms.get_sms_list()

    messages.sort(key=lambda x: -cast(int, x.timestamp))
    if number is not None:
        messages = [x for x in messages if x.number == number]

    for message in messages:
        payload: dict[str, Any] = {
            "url": "http://192.168.0.1/index.html#sms",
            "title": f"{message.number}",
            "id": f"f50-sms-{message.id} - {message.date}",
            "date_published": message.date,
            "content_text": message.content,
        }
        items.append(JSONFeedItem(**payload))

    return feed
