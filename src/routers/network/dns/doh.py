import logging

import httpx
from fastapi import APIRouter, Query
from schemas.network.dns.doh import DoHResponse
from schemas.adapter import HttpUrl


router = APIRouter(tags=["Utils"], prefix="/network/dns")

logger = logging.getLogger(__file__)


default_doh = "https://1.1.1.1/dns-query"


@router.get("/doh", summary="DNS-Over-Https", response_model=DoHResponse)
def doh(
    url: HttpUrl = Query(default_doh, description="使用的 dns服务https 路径"),
    name: str = Query(..., description="域名"),
):
    """使用 doh 解析域名， 返回对应的 A记录</br>
    https://1.1.1.1/dns-query</br>
    https://223.5.5.5/resolve</br>
    """
    # TODO: 兼容不支持 HTTP JSON API 的 DOH 查询
    headers = {
        "Accept": "application/dns-json",
    }
    resp = httpx.get(str(url), params={"name": name, "type": "A"}, headers=headers)
    resp.raise_for_status()
    logger.debug(f"doh request domain: {name}\nresponse\n{resp.json()}")
    return resp.json()
