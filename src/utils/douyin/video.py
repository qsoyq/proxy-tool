import re
import logging
import httpx


from utils.playwright import AsyncPlaywright
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__file__)

Headless = True


class AsyncDouyinVideoPlaywright(AsyncPlaywright):
    WATCH_URL_PATH = "/aweme/v1/web/aweme/detail/"


class DouyinVideoTool:
    def to_download_url(self, body: dict):
        url = body["aweme_detail"]["video"]["bit_rate"][0]["play_addr"]["url_list"][-1]
        result = urlparse(url)
        video_id = parse_qs(result.query)["video_id"][0]
        return f"{result.scheme}://{result.hostname}{result.path}?video_id={video_id}"

    def get_video_link_from_share_text(self, text: str) -> str | None:
        result = re.search(r"https://v.douyin.com/.*?/", text)
        return result.group() if result else None

    def get_share_url_video_path(self, url: str):
        result = urlparse(url)
        return [x for x in result.path.split("/") if x][-1]

    async def get_location_from_share_text_url(self, url: str) -> str:
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            return res.headers["Location"]
