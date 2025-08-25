import re
import logging
import xmltodict
import httpx
from functools import lru_cache
from fastapi import APIRouter, Query
from concurrent.futures import ThreadPoolExecutor
from schemas.mikanani import MikananiResSchema, mikanani_rss_subscribe_responses

executor = ThreadPoolExecutor()
router = APIRouter(tags=["Utils"], prefix="/mikanani/rss")
logger = logging.getLogger(__file__)


@router.get(
    "/", summary="蜜柑计划 RSS 订阅", response_model=MikananiResSchema, responses=mikanani_rss_subscribe_responses
)
def subscribe(token: str = Query(...)) -> MikananiResSchema:
    url = "https://mikanani.me/RSS/MyBangumi"
    resp = httpx.get(url, params={"token": token})
    resp.raise_for_status()
    body = xmltodict.parse(resp.text)
    body["rss"]["channel"].setdefault("item", [])

    if isinstance(body["rss"]["channel"]["item"], dict):
        body["rss"]["channel"]["item"] = [body["rss"]["channel"]["item"]]

    body["rss"]["channel"]["item"] = list(executor.map(add_image_url, body["rss"]["channel"]["item"]))
    pattern = re.compile(r"^\[.*?\]\s*|\s*\[.*?\]$")
    for item in body["rss"]["channel"]["item"]:
        title = item["title"]
        item["real_title"] = re.sub(pattern, "", title).strip()
    return MikananiResSchema(**body)


def add_image_url(item: dict) -> dict:
    host = "https://mikanani.me"
    link = item["link"]
    try:
        url = get_image_url(link)
        if url:
            item["image"] = f"{host}{url}"
            logger.debug(f"image: {host}{url}")
    except Exception as e:
        logger.warning(e, exc_info=True)
    return item


@lru_cache
def get_image_url(link: str) -> str | None:
    pattern = r"url\((.*?)\)"
    res = httpx.get(link)
    res.raise_for_status()
    match = re.search(pattern, res.text)
    if match:
        image_url = match.group(1)
        return image_url.strip("'")
    return None
