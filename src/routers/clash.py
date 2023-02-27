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
def one_r(
    url: HttpUrl = Query(...,
                         description="clash 订阅地址"),
    is_clash: bool = Query(False),
    user_agent: str = Header("",
                             alias='user-agent')
):
    """覆盖一元机场的配置文件

    添加规则
        `- DOMAIN,adservice.google.com,DIRECT`
        `- DOMAIN-SUFFIX,g.doubleclick.net,DIRECT`

    - 去除带倍率的临时节点
    """
    # 在一元机场需要在 ua 添加 clash, 响应内容才会是 yaml 格式的配置文件
    logger.debug(f"{user_agent}")
    headers = {}
    _is_clash = bool(is_clash or 'clash' in user_agent.lower())

    if _is_clash:
        headers['user-agent'] = 'clash'

    res = httpx.get(url, headers=headers)
    if res.is_error:
        # 使用代理访问一元机场会遭到 cloudflare 的拦截
        res = httpx.get(url, headers=headers, proxies={})

    res.raise_for_status()

    content = ""
    if _is_clash:
        try:
            doc = yaml.safe_load(res.text)
        except yaml.scanner.ScannerError:
            # clash 文档识别失败, 直接返回订阅结果
            return PlainTextResponse(res.text)

        rules: List[str] = doc.get('rules', [])
        add_rules = (
            'DOMAIN,adservice.google.com,DIRECT',
            'DOMAIN-SUFFIX,g.doubleclick.net,DIRECT',
        )
        for rule in add_rules[::-1]:
            rules.insert(0, rule)

        # 移除 x 倍率节点
        for group in doc['proxy-groups']:
            group['proxies'] = [x for x in group.get('proxies', []) if "倍率" not in x]

        doc['proxies'] = [x for x in doc.get('proxies', []) if "倍率" not in x['name']]
        content = yaml.safe_dump(doc, allow_unicode=True)
        logger.info(doc.get('proxies'))

    else:
        s = urllib.parse.quote_plus("倍率").encode()
        proxies = base64.b64decode(res.text).split(b'\n')
        proxies = [p for p in proxies if s not in p.rsplit(b'#', 1)[-1]]
        content = base64.b64encode(b"\n".join(proxies))
    return PlainTextResponse(content=content)


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
