import logging
from datetime import datetime
import pytz
import feedgen.feed
from fastapi import APIRouter, Request, Response, Query
from routers.apple.ics.gofans import get_gofans_app_records
from schemas.rss.jsonfeed import JSONFeed
from responses import PrettyJSONResponse


router = APIRouter(tags=["RSS"], prefix="/rss/gofans")

logger = logging.getLogger(__file__)


@router.get("/iOS/v1", summary="AppleStore iOS 限免RSS订阅", include_in_schema=False)
async def ios(
    req: Request,
    limit: int = Query(20),
    page: int = Query(1),
):
    """数据源自: https://gofans.cn/"""
    host = req.url.hostname
    port = req.url.port
    if port is None:
        port = 80 if req.url.scheme == "http" else 443
    kind = 2
    resp = await get_gofans_app_records(limit, page, kind)

    fg = feedgen.feed.FeedGenerator()
    fg.id("https://gofans.cn/")
    fg.title("AppStore应用限免")
    fg.subtitle("新鲜出炉的帖子")
    fg.author({"name": "qsssssssss", "email": "support@19940731.xyz"})
    fg.link(href="https://gofans.cn/", rel="alternate")
    fg.logo("https://gofans.cn/favicon.ico")
    fg.link(href=f"https://{host}:{port}/api/rss/gofans/iOS", rel="self")
    fg.language("zh-CN")

    data = resp.json()
    timezone = pytz.timezone("Asia/Shanghai")

    for item in data.get("data", []):
        description = f"""
            {item['original_price']} => {item['price']}
            ✨{item['rating']}
            {item['description']}
        """
        description = "\n".join([x.strip() for x in description.split("\n")])
        updated = timezone.localize(datetime.fromtimestamp(item["updated_at"]))
        entry = fg.add_entry()
        entry.id(str(item["app_id"]))
        entry.title(f'应用限免: {item["name"]}')
        entry.content(description)
        entry.published(updated)
        entry.link(href=f"https://gofans.cn/app/{item['uuid']}")

    rss_xml = fg.rss_str(pretty=True)
    return Response(content=rss_xml, media_type="application/xml")


@router.get("/macOS/v1", summary="AppleStore macOS 限免RSS订阅", include_in_schema=False)
async def macOS(
    req: Request,
    limit: int = Query(20),
    page: int = Query(1),
):
    """数据源自: https://gofans.cn/"""
    host = req.url.hostname
    port = req.url.port
    if port is None:
        port = 80 if req.url.scheme == "http" else 443
    kind = 1
    resp = await get_gofans_app_records(limit, page, kind)

    fg = feedgen.feed.FeedGenerator()
    fg.id("https://gofans.cn/")
    fg.title("AppStore应用限免")
    fg.subtitle("新鲜出炉的帖子")
    fg.author({"name": "qsssssssss", "email": "support@19940731.xyz"})
    fg.link(href="https://gofans.cn/", rel="alternate")
    fg.logo("https://gofans.cn/favicon.ico")
    fg.link(href=f"https://{host}:{port}/api/rss/gofans/iOS", rel="self")
    fg.language("zh-CN")

    data = resp.json()
    timezone = pytz.timezone("Asia/Shanghai")

    for item in data.get("data", []):
        description = f"""
            {item['original_price']} => {item['price']}
            ✨{item['rating']}
            {item['description']}
        """
        description = "\n".join([x.strip() for x in description.split("\n")])
        updated = timezone.localize(datetime.fromtimestamp(item["updated_at"]))
        entry = fg.add_entry()
        entry.id(str(item["app_id"]))
        entry.title(f'应用限免: {item["name"]}')
        entry.content(description)
        entry.published(updated)
        entry.link(href=f"https://gofans.cn/app/{item['uuid']}")

    rss_xml = fg.rss_str(pretty=True)
    return Response(content=rss_xml, media_type="application/xml")


@router.get(
    "/iOS", response_model=JSONFeed, summary="GoFans App Store iOS 限免RSS订阅", response_class=PrettyJSONResponse
)
async def ios_jsonfeed(
    req: Request,
    limit: int = Query(20),
    page: int = Query(1),
):
    """GoFans App Store iOS 限免RSS订阅"""

    host = req.url.hostname
    kind = 2
    resp = await get_gofans_app_records(limit, page, kind)
    data = resp.json()

    items: list = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "GoFans iOS 应用限免",
        "description": "AppStore iOS 应用限免订阅",
        "home_page_url": "https://gofans.cn/",
        "feed_url": f"{req.url.scheme}://{host}{req.url.path}?{req.url.query}",
        "icon": "https://gofans.cn/favicon.ico",
        "favicon": "https://gofans.cn/favicon.ico",
        "items": items,
    }

    timezone = pytz.timezone("Asia/Shanghai")
    for item in data.get("data", []):
        description = f"""
            {item['original_price']} => {item['price']}
            ✨{item['rating']}
            {item['description']}
        """
        description = "\n".join([x.strip() for x in description.split("\n")])
        updated = timezone.localize(datetime.fromtimestamp(item["updated_at"])).strftime("%Y-%m-%dT%H:%M:%S%z")
        url = f"https://gofans.cn/app/{item['uuid']}"
        payload = {
            "url": url,
            "title": f'iOS应用限免: {item["name"]}',
            "id": f'iOS-{item["app_id"]}',
            "date_published": updated,
            "content_text": description or "",
            "author": {
                "avatar": item["icon"],
                "url": url,
                "name": item["name"],
            },
        }
        items.append(payload)
    return feed


@router.get(
    "/macOS", response_model=JSONFeed, summary="GoFans App Store macOS 限免RSS订阅", response_class=PrettyJSONResponse
)
async def macOS_jsonfeed(
    req: Request,
    limit: int = Query(20),
    page: int = Query(1),
):
    """GoFans App Store macOS 限免RSS订阅"""

    host = req.url.hostname
    kind = 1
    resp = await get_gofans_app_records(limit, page, kind)
    data = resp.json()

    items: list = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "GoFans macOS 应用限免",
        "description": "AppStore macOS 应用限免订阅",
        "home_page_url": "https://gofans.cn/",
        "feed_url": f"{req.url.scheme}://{host}{req.url.path}?{req.url.query}",
        "icon": "https://gofans.cn/favicon.ico",
        "favicon": "https://gofans.cn/favicon.ico",
        "items": items,
    }

    timezone = pytz.timezone("Asia/Shanghai")
    for item in data.get("data", []):
        description = f"""
            {item['original_price']} => {item['price']}
            ✨{item['rating']}
            {item['description']}
        """
        description = "\n".join([x.strip() for x in description.split("\n")])
        updated = timezone.localize(datetime.fromtimestamp(item["updated_at"])).strftime("%Y-%m-%d %H:%M:%S%Z")
        url = f"https://gofans.cn/app/{item['uuid']}"
        payload = {
            "url": url,
            "title": f'macOS应用限免: {item["name"]}',
            "id": f'macOS-{item["app_id"]}',
            "date_published": updated,
            "content_text": description or "",
            "author": {
                "avatar": item["icon"],
                "url": url,
                "name": item["name"],
            },
        }
        items.append(payload)
    return feed
