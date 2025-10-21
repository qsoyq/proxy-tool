import asyncio
import logging
import httpx
from fastapi import APIRouter, Request, Query
from schemas.rss.jsonfeed import JSONFeed, JSONFeedItem
from routers.v2ex.my import get_topics
from asyncache import cached
from utils.cache import RandomTTLCache

router = APIRouter(tags=["RSS"], prefix="/rss/jsonfeed/v2ex")

logger = logging.getLogger(__file__)


@cached(RandomTTLCache(4096, 600))
async def fetch_jsonfeed_items(topic: str) -> list[JSONFeedItem]:
    url = f"https://www.v2ex.com/feed/{topic}.json"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=30)
    except httpx.TimeoutException:
        logger.warning(f"[V2ex.RSS.Aggregation] request timeout, topic: {topic}")
        return []
    if resp.is_error:
        logger.warning(f"[V2ex.RSS.Aggregation] request error, text: {resp.text}")
        return []
    return [JSONFeedItem(**x) for x in resp.json()["items"]]


@router.get("/aggregation", response_model=JSONFeed, summary="V2ex 节点 RSS 订阅聚合")
async def aggregation(req: Request, topics: list[str] = Query([], description="订阅主题, 如 wechat、design")):
    """RSS 聚合

    https://www.v2ex.com/feed/{topic}.json
    """
    host = req.url.hostname
    items: list[JSONFeedItem] = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "V2ex",
        "description": "V2ex RSS 订阅聚合",
        "home_page_url": "https://v2ex.com",
        "feed_url": f"{req.url.scheme}://{host}{req.url.path}?{req.url.query}",
        "icon": "https://www.v2ex.com/favicon.ico",
        "favicon": "https://www.v2ex.com/favicon.ico",
        "items": items,
    }
    tasks: list[asyncio.Task[list[JSONFeedItem]]] = []
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch_jsonfeed_items(topic)) for topic in topics]

    items = [item for task in tasks for item in task.result()]
    feed["items"] = items
    return feed


@router.get("/favorite", response_model=JSONFeed, summary="V2ex 收藏帖回复 RSS 订阅")
def favorite(
    req: Request,
    session_key: str = Query(..., description="V2ex 登录态,Cookie.A2"),
    page: int = Query(1, description="收藏页，默认为 1"),
):
    """RSS 收藏贴回复订阅

    https://www.v2ex.com/feed/{topic}.json
    """
    host = req.url.hostname

    items: list[JSONFeedItem] = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "V2ex",
        "description": "V2ex 收藏帖子RSS订阅",
        "home_page_url": "https://v2ex.com",
        "feed_url": f"{req.url.scheme}://{host}{req.url.path}?{req.url.query}",
        "icon": "https://www.v2ex.com/favicon.ico",
        "favicon": "https://www.v2ex.com/favicon.ico",
        "items": items,
    }
    ret = get_topics(session_key, page)
    for topic in ret.topics:
        payload = {
            "author": {},
            "url": f"https://v2ex.com/t/{topic.id}",
            "title": f"{topic.title}",
            "id": topic.id,
            "date_published": topic.lastTouchedStr,
            "content_html": "",
        }
        items.append(JSONFeedItem(**payload))
    return feed
