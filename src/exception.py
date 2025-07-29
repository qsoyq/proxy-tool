import logging
from fastapi import Request, FastAPI
from fastapi.responses import Response
from httpx import TimeoutException
from requests.exceptions import Timeout

logger = logging.getLogger(__file__)


def register_exception_handler(app: FastAPI):
    app.add_exception_handler(TimeoutException, httpx_timeout_exception_handler)  # type: ignore
    app.add_exception_handler(Timeout, httpx_timeout_exception_handler)  # type: ignore


def httpx_timeout_exception_handler(request: Request, exc: TimeoutException) -> Response:
    req = getattr(exc, "_request", None)
    logger.warning(f"[Gateway Timeout] from: {request.url}, to: {exc.request.url if req else None}")
    return Response(
        content="Gateway timeout",
        status_code=504,
    )
