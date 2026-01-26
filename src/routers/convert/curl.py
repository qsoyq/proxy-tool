import logging

from fastapi import APIRouter, Body
from fastapi.responses import PlainTextResponse
from utils.basic import CurlParser

router = APIRouter(tags=["Utils"], prefix="/convert/curl")

logger = logging.getLogger(__file__)


@router.post("/stash", summary="curl2stash")
async def convert_curl_to_stash(
    content: str = Body(
        ..., media_type="text/plain", description="curl 命令参数", examples=["curl -X GET https://httpbin.org/get"]
    ),
):
    detail = CurlParser(content).parse()
    converted = detail.to_stash()
    return PlainTextResponse(converted)


@router.post("/httpx", summary="curl2httpx")
async def convert_curl_to_httpx(
    content: str = Body(
        ..., media_type="text/plain", description="curl 命令参数", examples=["curl -X GET https://httpbin.org/get"]
    ),
):
    detail = CurlParser(content).parse()
    converted = detail.to_httpx()
    return PlainTextResponse(converted)
