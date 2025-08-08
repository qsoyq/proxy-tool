import json
import logging
from datetime import datetime, timedelta
import pytz
import cloudscraper
from bs4 import BeautifulSoup as soup
from fastapi import APIRouter, Path, Request, Response, Query
from fastapi.responses import JSONResponse
import feedgen.feed


router = APIRouter(tags=["RSS"], prefix="/rss/nnr")

logger = logging.getLogger(__file__)


@router.get("/traffic/used/day/{ssid}", summary="NNR 日流量 RSS 订阅")
def traffic_used_by_day(
    req: Request,
    ssid: str = Path(..., description="Cookie, login state"),
    with_today: bool = Query(False, description="是否包含今日统计数据，默认不包含"),
):
    """过去 31d 的流量统计， 见 https://nnr.moe/user/traffic"""
    host = req.url.hostname
    port = req.url.port
    if port is None:
        port = 80 if req.url.scheme == "http" else 443

    url = "https://nnr.moe/user/traffic"
    cookies = {"ssid": ssid}
    scraper = cloudscraper.create_scraper()
    resp = scraper.get(url, cookies=cookies)

    if resp.is_redirect:
        return JSONResponse({"msg": "ssid has been expired"}, status_code=400)

    if not resp.ok:
        return JSONResponse({"msg": resp.text}, status_code=resp.status_code)

    fg = feedgen.feed.FeedGenerator()
    fg.id("https://nnr.moe/user/traffic")
    fg.title("NNR 流量使用情况")
    fg.subtitle("过去 31d 的流量使用情况")
    fg.author({"name": "qsssssssss", "email": "support@19940731.xyz"})
    fg.link(href="https://nnr.moe/user/traffic", rel="alternate")
    fg.logo("https://p.19940731.xyz/api/convert/svg/png?url=https%3A%2F%2Fnnr.moe%2Fimg%2Flogo.svg&download=false")
    fg.link(href=f"https://{host}:{port}/api/traffic/used/day/{ssid}", rel="self")
    fg.language("zh-CN")

    document = soup(resp.text, "lxml")
    tag = document.select_one("#traffic_data")
    if tag:
        data = json.loads(tag.text)
        ds = data["ds"]
        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        timezone = pytz.timezone("Asia/Shanghai")
        today = timezone.localize(today)
        for index, count in enumerate(ds):
            day = today + timedelta(days=index - 31 + 1)
            used = count / 1024 / 1024 / 1024 if count else 0
            datestr = day.strftime("%Y.%m.%d")

            if day == today:
                if not with_today:
                    continue
                entry = fg.add_entry()
                now = datetime.now()
                entry.id(f"nnr.traffic.{now.strftime('%Y.%m.%d.%H')}")
            else:
                entry = fg.add_entry()
                entry.id(f"nnr.traffic.{datestr}")
            entry.title(f"NNR {datestr} 流量使用")
            entry.content(f"共使用(GB): {used:.3f}")
            entry.published(day)
            entry.author({"name": "qsssssssss", "email": "p@19940731.xyz"})
            entry.link(href="https://nnr.moe/user/traffic")

    rss_xml = fg.rss_str(pretty=True)
    return Response(content=rss_xml, media_type="application/xml")
