import re
import logging
import xmltodict
import httpx
from fastapi import APIRouter, Query
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()
router = APIRouter(tags=["mikanani.rss"], prefix="/mikanani/rss")
logger = logging.getLogger(__file__)


@router.get("/")
def subscribe(token: str = Query(...)):
    url = "https://mikanani.me/RSS/MyBangumi"
    resp = httpx.get(url, params={"token": token})
    resp.raise_for_status()
    body = xmltodict.parse(resp.text)
    items = body["rss"]["channel"].get("item", [])
    if items:
        items = list(executor.map(add_image_url, items))
        body["rss"]["channel"]["item"] = items
    return body


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


def get_image_url(link: str) -> str | None:
    pattern = r"url\((.*?)\)"
    res = httpx.get(link)
    res.raise_for_status()
    match = re.search(pattern, res.text)
    if match:
        image_url = match.group(1)
        return image_url.strip("'")
    return None
