import json
import logging
from typing import Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from responses import PrettyJSONResponse

app = FastAPI()
logger = logging.getLogger(__file__)


def add_middleware(app: FastAPI):
    app.add_middleware(UsePrettryJSONResponse)


class AddCharsetToJSONMiddleware(BaseHTTPMiddleware):
    content_type: str = 'application/json;charset=utf-8'

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response | JSONResponse:
        response = await call_next(request)
        ct = response.headers.get('content-type')
        if ct and ct.startswith('application/json'):
            response_body = b''
            async for chunk in response.body_iterator:  # type: ignore
                response_body += chunk
            body = json.loads(response_body)
            headers = dict(response.headers)
            headers.pop('content-length', None)
            headers['content-type'] = self.__class__.content_type
            return JSONResponse(body, status_code=response.status_code, headers=headers)
        return response


class UsePrettryJSONResponse(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response | PrettyJSONResponse:
        response = await call_next(request)
        ct = response.headers.get('content-type')
        if ct and ct.startswith('application/json'):
            response_body = b''
            async for chunk in response.body_iterator:  # type: ignore
                response_body += chunk
            body = json.loads(response_body)
            headers = dict(response.headers)
            headers.pop('content-length', None)
            if headers.get('content-type') == 'application/json':
                headers['content-type'] = 'application/json;charset=utf-8'
            return PrettyJSONResponse(body, status_code=response.status_code, headers=headers)
        return response
