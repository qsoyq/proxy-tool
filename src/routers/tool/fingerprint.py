import logging
from typing import cast

from curl_cffi import BrowserType, BrowserTypeLiteral, requests
from fastapi import APIRouter, Query, Response
from schemas.adapter import HttpUrl

router = APIRouter(tags=['Utils'], prefix='/fingerprint')

logger = logging.getLogger(__file__)


@router.get('/', summary='指纹验证测试')
def fingerprint(
    url: HttpUrl = Query(...),
    cookie: str | None = Query(None),
    impersonate: BrowserType = Query(requests.impersonate.DEFAULT_CHROME),
):
    cookies = {}
    if cookie is not None:
        cookies = dict([x.strip().split('=') for x in cookie.split(';') if x != ''])

    res = requests.get(url, cookies=cookies, impersonate=cast(BrowserTypeLiteral, impersonate))
    return Response(res.text, status_code=res.status_code)


@router.get('/browser', summary='浏览器列表')
def browser():
    members = {m.name: m.value for m in BrowserType}
    return {'browser': members}
