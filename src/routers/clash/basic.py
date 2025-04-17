import asyncio
import logging
import socket


import httpx
import yaml

from fastapi import APIRouter, Query
from fastapi.responses import Response

from models import ClashModel

router = APIRouter(tags=["Proxy"], prefix="/clash")

logger = logging.getLogger(__file__)


@router.head("/timeout/{timeout}", include_in_schema=False)
@router.get("/timeout/{timeout}")
async def timeout(timeout: float | None = Query(None, description="可控的阻塞时间")):
    if timeout is not None:
        await asyncio.sleep(timeout)
    return ""


@router.get("/subscribe", summary="Clash订阅转换")
@router.head("/subscribe", include_in_schema=False)
def subscribe(
    user_agent: str = Query(
        "Stash/3.1.0 Clash/1.9.0",
    ),
    url: str = Query(..., description="订阅链接"),
    additional_prefix: str | None = Query(None, description="为代理节点添加前缀", alias="additional-prefix"),
    proxy_provider: bool = Query(False, description="是否只返回节点", alias="proxy-provider"),
    benchmark_url: str | None = Query(
        None, description="延迟测试连接, 如: http://cp.cloudflare.com/", alias="benchmark-url"
    ),
    benchmark_timeout: float | None = Query(1, description="延迟测试超时，单位: 秒", alias="benchmark-timeout"),
):
    headers = {}
    if user_agent is not None:
        headers["user-agent"] = user_agent
    resp = httpx.get(url, headers=headers)
    resp.raise_for_status()
    # 订阅信息字段
    headers = {}
    for field in (
        "profile-update-interval",
        "profile-web-page-url",
        "subscription-userinfo",
    ):
        if field in resp.headers:
            headers[field] = resp.headers[field]
    content = resp.text
    if additional_prefix:
        dom = yaml.safe_load(content)
        for x in dom.get("proxies", []):
            x["name"] = additional_prefix + x["name"]
        content = yaml.safe_dump(dom, allow_unicode=True)

    if benchmark_url:
        dom = yaml.safe_load(content)
        for x in dom.get("proxies", []):
            x["benchmark-url"] = benchmark_url
        content = yaml.safe_dump(dom, allow_unicode=True)

    if benchmark_timeout:
        dom = yaml.safe_load(content)
        for x in dom.get("proxies", []):
            x["benchmark-timeout"] = benchmark_timeout
        content = yaml.safe_dump(dom, allow_unicode=True)

    if proxy_provider:
        dom = yaml.safe_load(content)
        content = yaml.safe_dump({"proxies": dom["proxies"]}, allow_unicode=True)
    headers["content-type"] = "text/plain;charset=utf-8"
    return Response(content=content, status_code=resp.status_code, headers=headers)


def check_server_format(addr: str) -> bool:
    try:
        socket.inet_aton(addr)
    except socket.error:
        try:
            socket.gethostbyname(addr)
        except socket.gaierror:
            return False
    return True


def make_proxy_groups(clash: ClashModel, interval: int = 300) -> list[dict]:
    proxies = ["auto"] + [proxy.name for proxy in clash.proxies]

    auto_proxies = [proxy.name for proxy in clash.proxies]
    proxy_groups: list[dict] = [
        {"name": "proxies", "type": "select", "proxies": proxies},
        {
            "name": "auto",
            "type": "url-test",
            "proxies": auto_proxies,
            "url": "https://www.gstatic.com/generate_204",
            "interval": interval,
        },
    ]
    return proxy_groups
