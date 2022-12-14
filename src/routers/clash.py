import base64
import logging
import socket
import urllib.parse

from typing import List

import httpx
import oss2
import yaml

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from pydantic import HttpUrl

from models import ClashModel, ClashProxyModel

router = APIRouter(tags=["clash"], prefix='/clash')

logger = logging.getLogger(__file__)


@router.get("/subscribe")
async def clash2subscribe(clash_url: HttpUrl = Query(..., description="clash 订阅地址")):
    cli = httpx.AsyncClient()
    res = await cli.get(clash_url)
    doc = yaml.safe_load(res.text)
    clash = ClashModel(**doc)

    proxies = []
    for proxy in clash.proxies:
        # 目前仅支持 ss 类型的代理
        if proxy.type != 'ss':
            continue

        encoded = base64.urlsafe_b64encode(f"{proxy.cipher}:{proxy.password}@{proxy.server}:{proxy.port}".encode()
                                           ).decode()
        name = base64.urlsafe_b64encode(f"{proxy.name}".encode()).decode()
        name = urllib.parse.quote(proxy.name)
        share_uri = f"ss://{encoded}#{name}"
        proxies.append(share_uri)
    return PlainTextResponse("\n".join(proxies))


@router.get('/1r')
async def one_r(url: HttpUrl = Query(..., description="clash 订阅地址")):
    """覆盖一元机场的配置文件

    添加规则
        `- DOMAIN,adservice.google.com,DIRECT`
        `- DOMAIN-SUFFIX,g.doubleclick.net,DIRECT`

    """
    cli = httpx.AsyncClient()
    # 在一元机场需要在 ua 添加 clash, 响应内容才会是 yaml 格式的配置文件
    res = await cli.get(url, headers={"user-agent": 'clash'})
    content_disposition = res.headers.get('content-disposition')
    logger.debug(res.text)
    doc = yaml.safe_load(res.text)
    rules: List[str] = doc.get('rules', [])

    add_rules = ('DOMAIN,adservice.google.com,DIRECT', 'DOMAIN-SUFFIX,g.doubleclick.net,DIRECT')
    for rule in add_rules[::-1]:
        rules.insert(0, rule)

    content = yaml.safe_dump(doc, allow_unicode=True)
    headers = {}
    if content_disposition:
        headers['content-disposition'] = content_disposition
    return PlainTextResponse(content=content, headers=headers)


@router.get("/proxy/add")
def proxy_add(
    name: str = Query(...),
    port: int = Query(23333),
    cipher: str = Query('aes-256-cfb'),
    password: str = Query(...),
    server: str = Query(...,
                        description='代理的节点'),
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
    node = ClashProxyModel(name=name, server=server, port=port, cipher=cipher, password=password, type='ss')

    url = f'https://{oss_bucket_name}.{oss_endpoint}/{oss_key}'
    res = httpx.get(url)
    doc = yaml.safe_load(res.text)
    doc['proxies'].append(node.dict())
    clash = ClashModel(**doc)

    doc['proxy-groups'] = make_proxy_groups(clash)

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


def make_proxy_groups(clash: ClashModel) -> list[dict]:
    proxies = ["auto"] + [proxy.name for proxy in clash.proxies]

    auto_proxies = [proxy.name for proxy in clash.proxies]
    proxy_groups = [
        {
            "name": 'proxies',
            'type': 'select',
            'proxies': proxies
        },
        {
            "name": 'auto',
            'type': 'url-test',
            'proxies': auto_proxies,
            'url': 'https://www.v2ex.com/generate_204',
            'interval': 600
        },
    ]
    return proxy_groups
