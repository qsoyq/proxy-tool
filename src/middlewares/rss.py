import json
from typing import Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from responses import PrettyJSONResponse

app = FastAPI()


def add_middleware(app: FastAPI):
    app.add_middleware(FeedFilterMiddleware)


class FeedFilterMiddleware(BaseHTTPMiddleware):
    BLOCK_TAG = ["#广告", "#互推"]
    BLOCK_CONTENT = ("TG必备的搜索引擎，极搜帮你精准找到，想要的群组、频道、音乐 、视频", "https://hongxingdl.com")

    def filter_by_block(self, item: dict):
        tags = item["tags"] or []
        for block in FeedFilterMiddleware.BLOCK_TAG:
            if block in tags:
                return False
        for block in FeedFilterMiddleware.BLOCK_CONTENT:
            if item["content_html"] and block in item["content_html"]:
                return False
            if item["content_text"] and block in item["content_text"]:
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
