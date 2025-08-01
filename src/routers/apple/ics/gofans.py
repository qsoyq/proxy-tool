import logging
from datetime import datetime
import httpx
from fastapi.responses import PlainTextResponse
from ics import Calendar, Event
from fastapi import HTTPException, APIRouter, Query
import pytz


router = APIRouter(tags=["Utils"], prefix="/apple/ics/gofans")

logger = logging.getLogger(__file__)


async def get_gofans_app_records(limit: int, page: int, kind: int) -> httpx.Response:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://gofans.cn/",
        "Origin": "https://gofans.cn",
    }
    url = "https://api.gofans.cn/v1/web/app_records"
    params = {"limit": limit, "page": page, "kind": kind}
    resp = httpx.get(url, headers=headers, params=params)
    data = resp.json()
    if data.get("code") == 401:
        logger.warning("[Ics.Gofans] Unauthorized")
        raise HTTPException(502, "Unauthorized")
    return resp


async def fetch_gofans_calendar(kind: int, limit: int = 20, page: int = 1) -> list[Event]:
    events: list[Event] = []

    resp = await get_gofans_app_records(limit, page, kind)
    data = resp.json()

    timezone = pytz.timezone("Asia/Shanghai")
    today = timezone.localize(datetime.today())
    today = today.replace(hour=8, minute=0, second=0, microsecond=0)

    for item in data.get("data", []):
        e = Event()
        e.name = item["name"]
        description = f"""
            {item['original_price']} => {item['price']}
            ✨{item['rating']}
            {item['description']}
            """
        description = "\n".join([x.strip() for x in description.split("\n")])
        e.description = description
        e.url = f"https://gofans.cn/app/{item['uuid']}"
        e.begin = e.end = today
        events.append(e)
    return events


@router.get("/iOS", summary="AppleStore iOS 限免日历订阅")
async def ios(
    limit: int = Query(8),
    page: int = Query(1),
):
    """数据源自: https://gofans.cn/"""
    events = await fetch_gofans_calendar(2, limit=limit, page=page)
    c = Calendar()
    c.events = set(events)
    return PlainTextResponse(c.serialize())


@router.get("/macOS", summary="AppleStore macOS 限免日历订阅")
async def macOS(
    limit: int = Query(8),
    page: int = Query(1),
):
    """数据源自: https://gofans.cn/"""
    events = await fetch_gofans_calendar(1, limit=limit, page=page)
    c = Calendar()
    c.events = set(events)
    return PlainTextResponse(c.serialize())
