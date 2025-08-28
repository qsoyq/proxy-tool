import time
import logging
import traceback
from typing import Any, Awaitable, Callable
from asyncio import Lock
from collections import defaultdict

import httpx
from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from pydantic import BaseModel, model_validator, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

app = FastAPI()

logger = logging.getLogger(__file__)


class CachedItem(BaseModel):
    timestamp: float | None = Field(None, description="秒级时间戳")
    name: str
    path: str
    methods: list[str]
    error: str

    @model_validator(mode="after")
    def set_timestamp(cls, values):
        if values.timestamp is None:
            values.timestamp = time.time()

        return values


def add_middleware(app: FastAPI):
    app.add_middleware(SentryCacheMiddleware)


class SentryCacheMiddleware(BaseHTTPMiddleware):
    TTL = 3600 * 12
    LOCK = Lock()
    collections: dict[str, list[CachedItem]] = defaultdict(list)

    @staticmethod
    async def expire_all():
        for k in SentryCacheMiddleware.collections.keys():
            await SentryCacheMiddleware.expire_key(k)

    @staticmethod
    async def expire_key(key: str):
        async with SentryCacheMiddleware.LOCK:
            deadline = time.time() - SentryCacheMiddleware.TTL
            SentryCacheMiddleware.collections[key] = [
                x for x in SentryCacheMiddleware.collections[key] if x.timestamp and x.timestamp >= deadline
            ]

    @staticmethod
    async def get_errors():
        await SentryCacheMiddleware.expire_all()
        async with SentryCacheMiddleware.LOCK:
            return SentryCacheMiddleware.collections

    @staticmethod
    async def add_error(route: APIRoute, exc: Exception):
        async with SentryCacheMiddleware.LOCK:
            error = traceback.format_exception(exc)
            payload: dict[str, Any] = {
                "name": route.name,
                "path": route.path,
                "methods": route.methods,
                "error": f"{type(exc)} - {error}",
            }
            item = CachedItem(**payload)
            SentryCacheMiddleware.collections[route.name].insert(0, item)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        try:
            response = await call_next(request)
        except httpx.HTTPStatusError as e:
            logging.warning(f"[httpx.HTTPStatusError]: {e}")
            return Response(content=e.response.text, status_code=e.response.status_code)
        except Exception as e:
            route = request.scope.get("route")
            if route:
                await SentryCacheMiddleware.add_error(route, e)
            raise e
        return response
