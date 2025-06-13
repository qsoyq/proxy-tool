import json
import logging
from datetime import datetime, timedelta
import pytz
import httpx
from bs4 import BeautifulSoup as soup
from fastapi import APIRouter, Path, Request
import feedgen.feed


router = APIRouter(tags=["Utils"], prefix="/rss/nnr")

logger = logging.getLogger(__file__)


@router.get("/traffic/used/day/{ssid}")
def traffic_used_by_day(req: Request, ssid: str = Path(..., description="Cookie, login state")):
    """过去 31d 的流量统计， 见 https://nnr.moe/user/traffic"""
    host = req.url.hostname
    port = req.url.port
    resp = []
    url = "https://nnr.moe/user/traffic"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    cookies = {"ssid": ssid}
    res = httpx.get(url, headers=headers, cookies=cookies)
    res.raise_for_status()

    fg = feedgen.feed.FeedGenerator()
    fg.id("https://nnr.moe/user/traffic")
    fg.title("NNR 流量使用情况")
    fg.subtitle("过去 31d 的流量使用情况")
    fg.author({"name": "qsssssssss", "email": "p@19940731.xyz"})
    fg.link(href="https://nnr.moe/user/traffic", rel="alternate")
    fg.logo("https://nnr.moe/img/logo.svg")
    fg.link(href=f"https://{host}:{port}/api/traffic/used/day/{ssid}", rel="self")
    fg.language("zh-CN")

    document = soup(res.text, "lxml")
    tag = document.select_one("#traffic_data")
    if tag:
        data = json.loads(tag.text)
        ds = data["ds"]
        today = datetime.today()
        timezone = pytz.timezone("Asia/Shanghai")
        today = timezone.localize(today)
        for index, count in enumerate(ds):
            day = today + timedelta(days=index - 31 + 1)
            used = count / 1024 / 1024 / 1024 if count else 0
            resp.append((day, used))
            datestr = day.strftime("%Y.%m.%d")
            entry = fg.add_entry()
            entry.id(f"nnr.traffic.{datestr}")
            entry.title(f"NNR {datestr} 流量使用(GB): {used:.3f}")
            entry.published(day)
            entry.author({"name": "qsssssssss", "email": "p@19940731.xyz"})
            entry.content(f"NNR {datestr} 流量使用(GB): {used:.3f}")

    rss_xml = fg.rss_str(pretty=True)
    return rss_xml
