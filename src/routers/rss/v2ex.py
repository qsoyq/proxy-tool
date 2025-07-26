import asyncio
import logging
import httpx
from fastapi import APIRouter, Request, Query
from schemas.rss.jsonfeed import JSONFeed, JSONFeedItem


router = APIRouter(tags=["Utils"], prefix="/rss/jsonfeed/v2ex")

logger = logging.getLogger(__file__)


async def fetch_jsonfeed_items(topic: str) -> list[JSONFeedItem]:
    url = f"https://www.v2ex.com/feed/{topic}.json"
    resp = httpx.get(url)
    resp.raise_for_status()
    return [JSONFeedItem(**x) for x in resp.json()["items"]]


@router.get("/aggregation", response_model=JSONFeed)
async def aggregation(req: Request, topics: list[str] = Query([], description="订阅主题, 如 wechat、design")):
    """RSS 聚合

    https://www.v2ex.com/feed/{topic}.json
    """
    host = req.url.hostname
    port = req.url.port
    if port is None:
        port = 80 if req.url.scheme == "http" else 443

    items: list[JSONFeedItem] = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "V2ex",
        "description": "V2ex RSS 订阅聚合",
        "home_page_url": "https://v2ex.com",
        "feed_url": f"{req.url.scheme}://{host}:{port}/api/rss/jsonfeed/v2ex/aggregation",
        "icon": "https://www.v2ex.com/favicon.ico",
        "favicon": "https://www.v2ex.com/favicon.ico",
        "items": items,
    }
    result = await asyncio.gather(*[fetch_jsonfeed_items(topic) for topic in topics])
    for one in result:
        items.extend(one)

    return feed
