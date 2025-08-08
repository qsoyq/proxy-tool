import datetime
import logging
import asyncio
import dateparser
import pytz
import httpx
from fastapi import APIRouter, Request, Response, Query
import feedgen.feed


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


@router.get("/ipx", summary="Loon插件RSS订阅")
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
            updated = datetime.datetime.now()

        entry = fg.add_entry()
        entry.id(f"{name}-{homepage}-{date}")
        entry.title(name)
        entry.content(item.get("desc", ""))
        entry.published(updated)
        entry.link(href=href)
    rss_xml = fg.rss_str(pretty=True)
    return Response(content=rss_xml, media_type="application/xml")
