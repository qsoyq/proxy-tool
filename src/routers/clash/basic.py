import asyncio
import logging
import socket


import httpx
import yaml

from fastapi import APIRouter, Query
from fastapi.responses import Response, PlainTextResponse

from models import ClashModel

router = APIRouter(tags=["Proxy"], prefix="/clash")

logger = logging.getLogger(__file__)


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


def country_code_to_emoji(country_code: str) -> str | None:
    # 将代码转为大写
    country_code = country_code.upper()
    three_to_two = {
        "USA": "US",
        "CAN": "CA",
        "GBR": "GB",
        "FRA": "FR",
        "DEU": "DE",
    }
    if len(country_code) == 3:
        country_code = three_to_two.get(country_code, country_code[:2])
    if len(country_code) != 2:
        return None
    base_code_point = 127397  # U+1F1E6 - U+0041
    code_points = [base_code_point + ord(char) for char in country_code]
    emoji_chars = [chr(cp) for cp in code_points]
    return "".join(emoji_chars)


def add_emoji_prefix(name: str) -> str:
    region_table = {
        "香港": "HK",
        "台湾": "TW",
        "美国": "US",
        "日本": "JP",
        "新加坡": "SG",
        "英国": "GB",
        "乌克兰": "UA",
        "以色列": "IL",
        "俄罗斯": "RU",
        "印度": "IN",
        "加拿大": "CA",
        "德国": "DE",
        "土耳其": "TR",
        "尼日利亚": "NG",
        "朝鲜": "KP",
        "意大利": "IT",
        "柬埔寨": "KH",
        "越南": "VN",
        "阿根廷": "AR",
        "葡萄牙": "PT",
        "澳大利亚": "AU",
        "哈萨克斯坦": "KZ",
    }
    for region, code in region_table.items():
        if region in name:
            emoji = country_code_to_emoji(code)
            if emoji and emoji not in name:
                name = name.replace(region, f"{emoji}{region}")
    return name


@router.head("/timeout/{timeout}", include_in_schema=False)
@router.get("/timeout/{timeout}")
async def timeout(timeout: float | None = Query(None, description="可控的阻塞时间")):
    if timeout is not None:
        await asyncio.sleep(timeout)
    return ""


@router.get("/subscribe", summary="Clash订阅转换")
@router.head("/subscribe", include_in_schema=False)
def subscribe(
    user_agent: str = Query("clash.meta"),
    url: str = Query(..., description="订阅链接"),
    proxy_provider: bool = Query(False, description="是否只返回节点", alias="proxy-provider"),
    sort_by_name: bool = Query(True, description="按名称排序节点", alias="sort-by-name"),
    additional_prefix: str | None = Query(
        None, description="为代理节点添加前缀, 在只返回节点模式下有效", alias="additional-prefix"
    ),
    emoji_additional_prefix: bool = Query(
        True, description="按节点地区添加 emoji 前缀, 在只返回节点模式下有效", alias="emoji-additional-prefix"
    ),
    benchmark_url: str | None = Query(
        None, description="延迟测试连接, 如: http://cp.cloudflare.com/", alias="benchmark-url"
    ),
    benchmark_timeout: float | None = Query(None, description="延迟测试超时，单位: 秒", alias="benchmark-timeout"),
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
    document = None
    try:
        document = yaml.safe_load(content)
    except Exception:
        pass
    if not isinstance(document, dict):
        return PlainTextResponse("解析链接失败，未返回合法的 YAML 格式数据", status_code=400)

    if benchmark_url:
        for x in document.get("proxies", []):
            x["benchmark-url"] = benchmark_url

    if benchmark_timeout:
        for x in document.get("proxies", []):
            x["benchmark-timeout"] = benchmark_timeout

    if proxy_provider:
        if additional_prefix:
            for x in document.get("proxies", []):
                x["name"] = additional_prefix + x["name"]
        if emoji_additional_prefix:
            for x in document.get("proxies", []):
                x["name"] = add_emoji_prefix(x["name"])

        document = {"proxies": document["proxies"]}

    if sort_by_name:
        document["proxies"] = sorted(document["proxies"], key=lambda x: x["name"])

    content = yaml.safe_dump(document, allow_unicode=True)
    headers["content-type"] = "text/plain;charset=utf-8"
    return Response(content=content, status_code=resp.status_code, headers=headers)
