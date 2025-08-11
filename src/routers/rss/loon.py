import logging
import asyncio
from datetime import datetime

import pytz
import feedgen.feed
import dateparser
import httpx

from fastapi import APIRouter, Request, Response, Query
from schemas.rss.jsonfeed import JSONFeed
from responses import PrettyJSONResponse

router = APIRouter(tags=["RSS"], prefix="/rss/loon")
logger = logging.getLogger(__file__)


async def get_ipx_info(url: str, useragent: str) -> dict:
    meta = {}
    headers = {"User-Agent": useragent}
    async with httpx.AsyncClient(headers=headers, verify=False) as client:
        resp = await client.get(url)
        if resp.is_error:
            logger.warning(f"[Loon Ipx] fetch ipx error: {resp.text}")
            return {}

        for line in resp.text.split("\n"):
            line = line.strip()
            if line.startswith("#!"):
                key, value = line[2:].split("=", 1)
                meta[key] = value
        meta["href"] = url
    logger.debug(f"[Loon Ipx] metainfo {url} {meta}")
    return meta


@router.get("/ipx/v1", summary="Loon插件RSS订阅", include_in_schema=False)
async def ipx(
    req: Request,
    url_list: list[str] = Query(...),
    ua: str = Query("StashCore/2.7.1 Stash/2.7.1 Clash/1.11.0", description="访问插件地址时使用的 user-agent"),
):
    """订阅 loon 插件更新

    - 根据 date 字段提取发布时间
    """
    host = req.url.hostname

    ret = await asyncio.gather(*[get_ipx_info(url, useragent=ua) for url in url_list])

    fg = feedgen.feed.FeedGenerator()
    fg.id("https://docs.19940731.xyz")
    fg.title("Loon 插件更新订阅")
    fg.subtitle("RSS订阅")
    fg.author({"name": "qsssssssss", "email": "support@19940731.xyz"})
    fg.link(href="https://docs.19940731.xyz", rel="alternate")
    fg.logo("https://docs.19940731.xyz/assets/images/favicon.png")
    fg.link(href=f"https://{host}/api/rss/loon/ipx", rel="self")
    fg.language("zh-CN")
    timezone = pytz.timezone("Asia/Shanghai")

    for item in ret:
        name, homepage, date, href = item.get("name"), item.get("homepage", ""), item.get("date"), item["href"]
        if not name or not date:
            continue
        dt = dateparser.parse(date)
        if dt:
            updated = timezone.localize(dt)
        else:
            updated = datetime.now()

        entry = fg.add_entry()
        entry.id(f"{name}-{homepage}-{date}")
        entry.title(name)
        entry.content(item.get("desc", ""))
        entry.published(updated)
        entry.link(href=href)
    rss_xml = fg.rss_str(pretty=True)
    return Response(content=rss_xml, media_type="application/xml")


@router.get("/ipx", summary="Loon插件RSS订阅", response_model=JSONFeed, response_class=PrettyJSONResponse)
async def ipx_jsonfeed(
    req: Request,
    url_list: list[str] = Query(...),
    ua: str = Query("StashCore/2.7.1 Stash/2.7.1 Clash/1.11.0", description="访问插件地址时使用的 user-agent"),
):
    """订阅 loon 插件更新

    - 根据 date 字段提取发布时间
    """
    host = req.url.hostname
    ret = await asyncio.gather(*[get_ipx_info(url, useragent=ua) for url in url_list])
    items: list = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "Loon 插件更新订阅",
        "description": "",
        "home_page_url": "https://docs.19940731.xyz",
        "feed_url": f"{req.url.scheme}://{host}{req.url.path}?{req.url.query}",
        "icon": "https://nsloon.app/img/favicon.png",
        "favicon": "https://nsloon.app/img/favicon.png",
        "items": items,
    }

    timezone = pytz.timezone("Asia/Shanghai")
    for item in ret:
        name, homepage, date, href = item.get("name"), item.get("homepage", ""), item.get("date"), item["href"]
        icon, author, desc = item.get("icon", ""), item.get("author", ""), item.get("desc", "")
        if not name or not date:
            continue
        if isinstance(date, str):
            date = dateparser.parse(date)
            if date:
                date = timezone.localize(date).strftime("%Y-%m-%dT%H:%M:%S%z")
        payload = {
            "id": f"{name}-{homepage}-{date}",
            "title": f"{name}",
            "url": href,
            "date_published": date,
            "content_text": desc,
            "author": {"avatar": icon, "url": homepage, "name": author},
        }
        items.append(payload)
    return feed
