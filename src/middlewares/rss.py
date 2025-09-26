import re
import json
import logging
from typing import Awaitable, Callable, cast

import httpx
from bs4 import BeautifulSoup as Soup, Tag

from cachetools import cached, FIFOCache
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from responses import PrettyJSONResponse
from schemas.rss.jsonfeed import JSONFeedItem

app = FastAPI()
logger = logging.getLogger(__file__)


def add_middleware(app: FastAPI):
    app.add_middleware(FeedFilterMiddleware)
    app.add_middleware(AddTwitterHTMLFeedMiddleware)
    app.add_middleware(UpdateTelegraphHTMLFeedMiddleware)


class AddTwitterHTMLFeedMiddleware(BaseHTTPMiddleware):
    @cached(FIFOCache(maxsize=1024))
    def make_html_by_url(self, url: str):
        output = []

        resp = httpx.get(url, verify=False)
        document = Soup(resp.text, "lxml")
        images = document.find_all("meta", property="og:image")

        for image in images:
            href = cast(Tag, image)["content"]

            ele = f"<img src='{href}'></img>"
            output.append(ele)
        return "\n".join(output)

    def fixupx_match(self, item: dict):
        feed = JSONFeedItem(**item)

        if feed.content_html:
            p = r"(https://fixupx.com/.*?/status/\d+)"
            result = re.search(p, feed.content_html)
            if result:
                contents = self.make_html_by_url(result.group(1))
                feed.content_html = f"{feed.content_html}<br>{contents}"

        return feed.model_dump()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response | PrettyJSONResponse:
        response = await call_next(request)
        path = request.url.path
        ct = response.headers.get("content-type")
        if ct and ct.startswith("application/json") and path.startswith("/api/rss/"):
            response_body = b""
            async for chunk in response.body_iterator:  # type: ignore
                response_body += chunk
            body = json.loads(response_body)
            headers = dict(response.headers)
            headers.pop("content-length", None)
            if body.get("version") == "https://jsonfeed.org/version/1":
                body["items"] = list(map(self.fixupx_match, body["items"]))
            return PrettyJSONResponse(body, status_code=response.status_code, headers=headers)
        return response


class UpdateTelegraphHTMLFeedMiddleware(BaseHTTPMiddleware):
    @cached(FIFOCache(maxsize=1024))
    def make_html_by_url(self, url: str) -> str:
        res = httpx.get(url)
        doc = Soup(res.text, "lxml")
        return "<br/>".join([str(img) for img in doc.find_all("img")])

    def fixupx_match(self, item: dict):
        feed = JSONFeedItem(**item)

        if feed.content_html:
            document = Soup(feed.content_html, "lxml")
            for tag in document.find_all("a"):
                tag = cast(Tag, tag)
                href = (tag and tag.attrs and tag.attrs["href"]) or None
                if isinstance(href, str) and href.startswith("https://telegra.ph"):
                    extend_img_content = self.make_html_by_url(href)
                    feed.content_html = f"{feed.content_html}{extend_img_content}"
                    logger.debug(f"[UpdateTelegraphHTMLFeedMiddleware] Added img for {href}")
        return feed.model_dump()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response | PrettyJSONResponse:
        response = await call_next(request)
        path = request.url.path
        ct = response.headers.get("content-type")
        if ct and ct.startswith("application/json") and path.startswith("/api/rss/"):
            response_body = b""
            async for chunk in response.body_iterator:  # type: ignore
                response_body += chunk
            body = json.loads(response_body)
            headers = dict(response.headers)
            headers.pop("content-length", None)
            if body.get("version") == "https://jsonfeed.org/version/1":
                body["items"] = list(map(self.fixupx_match, body["items"]))
            return PrettyJSONResponse(body, status_code=response.status_code, headers=headers)
        return response


class FeedFilterMiddleware(BaseHTTPMiddleware):
    BLOCK_TAG = ["#广告", "#互推", "#频道互推", "#群组互推"]
    BLOCK_CONTENT = (
        "TG必备的搜索引擎，极搜帮你精准找到，想要的群组、频道、音乐 、视频",
        "https://hongxingdl.com",
        "搜 蒸蒸日上 概率有5元猫卡",
        "<code>ikelee</code>",
    )

    BLOCK_REGEX_CONTENT = (r"(?i)HostDZire", "预制菜")

    BLOCK_REGEX_TITLE = (r"(?i)HostDZire", "预制菜")

    def filter_by_block(self, item: dict):
        tags = item["tags"] or []
        for tag in FeedFilterMiddleware.BLOCK_TAG:
            if tag in tags:
                logger.debug(f"[FeedFilterMiddleware] skip by block tag matched: {tag}")
                return False

        for block in FeedFilterMiddleware.BLOCK_CONTENT:
            if item["content_html"] and block in item["content_html"]:
                logger.debug(f"[FeedFilterMiddleware] skip by block content matched: {block}")
                return False
            if item["content_text"] and block in item["content_text"]:
                logger.debug(f"[FeedFilterMiddleware] skip by block content matched: {block}")
                return False

        for pattern in FeedFilterMiddleware.BLOCK_REGEX_CONTENT:
            if item["content_html"] and re.search(pattern, item["content_html"]):
                logger.debug(f"[FeedFilterMiddleware] skip by regex content matched: {pattern}")
                return False
            if item["content_text"] and re.search(pattern, item["content_text"]):
                logger.debug(f"[FeedFilterMiddleware] skip by regex content matched: {pattern}")
                return False

        for pattern in FeedFilterMiddleware.BLOCK_REGEX_TITLE:
            if item["title"] and re.search(pattern, item["title"]):
                logger.debug(f"[FeedFilterMiddleware] skip by regex title matched: {pattern}")
                return False
        return True

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response | PrettyJSONResponse:
        response = await call_next(request)
        path = request.url.path
        ct = response.headers.get("content-type")
        if ct and ct.startswith("application/json") and path.startswith("/api/rss/"):
            response_body = b""
            async for chunk in response.body_iterator:  # type: ignore
                response_body += chunk
            body = json.loads(response_body)
            headers = dict(response.headers)
            headers.pop("content-length", None)

            if body.get("version") == "https://jsonfeed.org/version/1":
                body["items"] = list(filter(lambda x: self.filter_by_block(x), body["items"]))

            return PrettyJSONResponse(body, status_code=response.status_code, headers=headers)
        return response
