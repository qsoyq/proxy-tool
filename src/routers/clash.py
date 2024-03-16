import asyncio
import base64
import logging
import socket
import urllib.parse

from typing import List

import httpx
import oss2
import yaml
import yaml.scanner

from fastapi import APIRouter, Header, Query
from fastapi.responses import PlainTextResponse
from pydantic import HttpUrl

from models import ClashModel, ClashProxyModel

router = APIRouter(tags=["clash"], prefix="/clash")

logger = logging.getLogger(__file__)


@router.get("/timeout/{timeout}")
@router.head("/timeout/{timeout}")
async def timeout_(timeout: float):
    await asyncio.sleep(timeout)
    return ""


@router.get("/timeout")
@router.head("/timeout")
async def timeout(timeout: float | None = Query(None, description="可控的阻塞时间")):
    if timeout is not None:
        await asyncio.sleep(timeout)
    return ""


@router.get("/subscribe")
async def clash2subscribe(clash_url: HttpUrl = Query(..., description="clash 订阅地址")):
    cli = httpx.AsyncClient()
    res = await cli.get(str(clash_url))
    doc = yaml.safe_load(res.text)
    clash = ClashModel(**doc)

    proxies = []
    for proxy in clash.proxies:
        share_uri = ""
        # 目前仅支持 ss 类型的代理
        if proxy.type == "ss":
            server = f"{proxy.cipher}:{proxy.password}@{proxy.server}:{proxy.port}".encode()
            encoded = base64.urlsafe_b64encode(server).decode()
            name = urllib.parse.quote(proxy.name)
            share_uri = f"ss://{encoded}#{name}"

        if proxy.type == "clash":
            share_uri = ""

        if share_uri:
            proxies.append(share_uri)
    content = base64.b64encode(("\r\n".join(proxies) + "\r\n").encode())
    return PlainTextResponse(content)


@router.get("/1r")
def one_r(
    user_agent: str = Header("", alias="user-agent"),
    url: HttpUrl = Query(..., description="clash 订阅地址"),
    is_clash: bool = Query(False),
    interval: int = Query(60),
):
    """覆盖一元机场的配置文件

    添加规则
        'DOMAIN,adservice.google.com,DIRECT',
        'DOMAIN,obsidian-couchdb.19940731.xyz,DIRECT',
        'DOMAIN,azure-ubuntu.19940731.xyz,DIRECT',
        'DOMAIN-SUFFIX,g.doubleclick.net,DIRECT',
        'DOMAIN-SUFFIX,elemecdn.com,DIRECT',
        'DOMAIN-SUFFIX,qq.com,DIRECT',
        'DOMAIN-SUFFIX,hdslb.com,DIRECT',
        'DOMAIN-SUFFIX,jable.tv,DIRECT',
        'DOMAIN-SUFFIX,mushroomtrack.com,DIRECT',
        'DOMAIN-KEYWORD,slack,DIRECT',
        'DOMAIN-KEYWORD,nga,DIRECT',
        'DOMAIN-SUFFIX,app-measurement.com,一元机场',
        'DOMAIN-SUFFIX,oscp.pki.goog,一元机场',
        'DOMAIN-SUFFIX,beacons.gcp.gvt2.com,一元机场',
        'DOMAIN-SUFFIX,getapp.com,一元机场',
        'DOMAIN-SUFFIX,g2.com,一元机场',
        'DOMAIN-SUFFIX,jsdelivr.com,一元机场',
        'DOMAIN-SUFFIX,ipinfo.io,一元机场',
        'DOMAIN-SUFFIX,your-service-provider,REJECT',

    - 去除带倍率的节点
    - 去除带计量的节点
    """
    # 在一元机场需要在 ua 添加 clash, 响应内容才会是 yaml 格式的配置文件
    logger.debug(f"{user_agent}")

    if is_clash:
        user_agent = "clash"

    headers = {"user-agent": user_agent}
    res = httpx.get(str(url), headers=headers)
    if res.is_error:
        # 使用代理访问一元机场会遭到 cloudflare 的拦截
        res = httpx.get(str(url), headers=headers, proxies={})

    res.raise_for_status()

    # 写入订阅信息
    resp_headers = {}
    resp_headers["subscription-userinfo"] = res.headers.get("subscription-userinfo", "")
    resp_headers["profile-update-interval"] = res.headers.get("profile-update-interval", "")

    content = ""
    if is_clash or "clash" in user_agent.lower():
        try:
            doc = yaml.safe_load(res.text)
        except yaml.scanner.ScannerError:
            # clash 文档识别失败, 直接返回订阅结果
            return PlainTextResponse(res.text)

        rules: List[str] = doc.get("rules", [])
        add_rules = (
            "DOMAIN,adservice.google.com,DIRECT",
            "DOMAIN,obsidian-couchdb.19940731.xyz,DIRECT",
            "DOMAIN,azure-ubuntu.19940731.xyz,DIRECT",
            "DOMAIN-SUFFIX,g.doubleclick.net,DIRECT",
            "DOMAIN-SUFFIX,elemecdn.com,DIRECT",
            "DOMAIN-SUFFIX,qq.com,DIRECT",
            "DOMAIN-SUFFIX,hdslb.com,DIRECT",
            "DOMAIN-SUFFIX,jable.tv,DIRECT",
            "DOMAIN-SUFFIX,mushroomtrack.com,DIRECT",
            "DOMAIN-KEYWORD,slack,DIRECT",
            "DOMAIN-KEYWORD,nga,DIRECT",
            "DOMAIN-SUFFIX,app-measurement.com,一元机场",
            "DOMAIN-SUFFIX,oscp.pki.goog,一元机场",
            "DOMAIN-SUFFIX,beacons.gcp.gvt2.com,一元机场",
            "DOMAIN-SUFFIX,getapp.com,一元机场",
            "DOMAIN-SUFFIX,g2.com,一元机场",
            "DOMAIN-SUFFIX,jsdelivr.com,一元机场",
            "DOMAIN-SUFFIX,ipinfo.io,一元机场",
            "DOMAIN-SUFFIX,your-service-provider,REJECT",
        )
        for rule in add_rules[::-1]:
            rules.insert(0, rule)

        keywords = ("倍率", "计量")
        for keyword in keywords:
            for group in doc["proxy-groups"]:
                group["proxies"] = [x for x in group.get("proxies", []) if keyword not in x]
                if "interval" in group:
                    group["interval"] = interval

            doc["proxies"] = [x for x in doc.get("proxies", []) if keyword not in x["name"]]

        content = yaml.safe_dump(doc, allow_unicode=True)

    else:
        s = urllib.parse.quote_plus("倍率").encode()
        proxies = base64.b64decode(res.text + "===").strip(b"\r\n").split(b"\r\n")
        proxies = [p for p in proxies if s not in p]
        content = base64.b64encode(b"\r\n".join(proxies) + b"\r\n").decode()
        logger.debug(content)

    return PlainTextResponse(content=content, headers=resp_headers)


@router.get("/proxy/add")
def proxy_add(
    name: str = Query(...),
    port: int = Query(23333),
    cipher: str = Query("aes-256-cfb"),
    password: str = Query(...),
    server: str = Query(..., description="代理的节点"),
    oss_access_key: str = Query(...),
    oss_access_secret: str = Query(...),
    oss_endpoint: str = Query(...),
    oss_bucket_name: str = Query(...),
    oss_key: str = Query(...),
):
    server = server.strip()
    if not check_server_format(server):
        return PlainTextResponse("bad server", status_code=400)

    auth = oss2.Auth(oss_access_key, oss_access_secret)
    bucket = oss2.Bucket(auth, oss_endpoint, oss_bucket_name)
    node = ClashProxyModel(name=name, server=server, port=port, cipher=cipher, password=password, type="ss")

    url = f"https://{oss_bucket_name}.{oss_endpoint}/{oss_key}"
    res = httpx.get(url)
    doc = yaml.safe_load(res.text)
    doc["proxies"].append(node.dict())
    clash = ClashModel(**doc)

    doc["proxy-groups"] = make_proxy_groups(clash)

    data = yaml.safe_dump(doc, allow_unicode=True)
    bucket.put_object(oss_key, data)

    return PlainTextResponse("Success")


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
