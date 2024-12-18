import logging
from fastapi import APIRouter, Body
from fastapi.responses import PlainTextResponse
from utils import CurlParser

router = APIRouter(tags=["convert.curl"], prefix="/convert/curl")

logger = logging.getLogger(__file__)


@router.post("/stash", summary="Convert curl to stash")
async def convert_curl_to_stash(
    content: str = Body(
        ..., media_type="text/plain", description="curl 命令参数", example="curl -X GET https://httpbin.org/get"
    ),
):
    detail = CurlParser(content).parse()
    converted = detail.to_stash()
    return PlainTextResponse(converted)


@router.post("/httpx", summary="Convert curl to python httpx")
async def convert_curl_to_httpx(
    content: str = Body(
        ..., media_type="text/plain", description="curl 命令参数", example="curl -X GET https://httpbin.org/get"
    ),
):
    detail = CurlParser(content).parse()
    converted = detail.to_httpx()
    return PlainTextResponse(converted)
