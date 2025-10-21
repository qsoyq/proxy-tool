import asyncio
import logging

import httpx
from bs4 import BeautifulSoup as Soup
from fastapi import APIRouter, Request, Query, Path, HTTPException
from schemas.rss.jsonfeed import JSONFeed, JSONFeedItem
from schemas.v2ex.notification import Notification
from routers.v2ex.my import get_topics
from asyncache import cached
from utils.cache import RandomTTLCache
from utils.basic import get_date_string_for_shanghai

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
        "title": "V2ex RSS 订阅聚合",
        "description": "",
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
    items: list[JSONFeedItem] = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "V2ex 收藏帖子RSS订阅",
        "description": "",
        "home_page_url": "https://v2ex.com",
        "feed_url": f"{req.url.scheme}://{req.url.hostname}{req.url.path}?{req.url.query}",
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


@router.get("/notifications/{token}", summary="V2ex 个人通知提醒")
async def notifications(
    req: Request, page: int = Query(1, description="分页，默认为 1"), token: str = Path(..., description="API Token")
):
    items: list[JSONFeedItem] = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "V2ex通知提醒",
        "description": "",
        "home_page_url": "https://www.v2ex.com/notifications",
        "feed_url": f"{req.url.scheme}://{req.url.hostname}{req.url.path}?{req.url.query}",
        "icon": "https://www.v2ex.com/favicon.ico",
        "favicon": "https://www.v2ex.com/favicon.ico",
        "items": items,
    }
    headers = {"Authorization": f"Bearer {token}"}
    notifications: list[Notification] = []
    async with httpx.AsyncClient(headers=headers) as client:
        url = "https://www.v2ex.com/api/v2/notifications"
        params = {"p": page}
        resp = await client.get(url, params=params)
        if resp.is_error:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        notifications = [Notification.model_validate(x) for x in resp.json()["result"]]

    for item in notifications:
        _url = get_url_from_notification_text(item.text)
        assert url, item.text
        payload = {
            "author": {},
            "url": _url,
            "title": item.text,
            "id": f"{item.id}",
            "date_published": get_date_string_for_shanghai(item.created),
            "content_html": item.payload_rendered,
        }
        items.append(JSONFeedItem.model_validate(payload))
    return feed


def get_url_from_notification_text(text: str) -> str | None:
    document = Soup(text, "lxml")
    for tag in document.select("a"):
        href = tag.get("href")
        if isinstance(href, str) and href.startswith("/t/"):
            return f"https://www.v2ex.com{href}"
    return None
