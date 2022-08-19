import base64
import urllib.parse

import httpx
import oss2
import yaml

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from pydantic import HttpUrl

from models import ClashModel, ClashProxyModel

router = APIRouter(tags=["clash"], prefix='/clash')


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
    auth = oss2.Auth(oss_access_key, oss_access_secret)
    bucket = oss2.Bucket(auth, oss_endpoint, oss_bucket_name)

    url = f'https://{oss_bucket_name}.{oss_endpoint}/{oss_key}'
    res = httpx.get(url)
    doc = yaml.safe_load(res.text)

    node = ClashProxyModel(name=name, server=server, port=port, cipher=cipher, password=password, type='ss')
    doc['proxies'].append(node.dict())

    clash = ClashModel(**doc)
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
    doc['proxy-groups'] = proxy_groups

    data = yaml.dump(doc)
    bucket.put_object(oss_key, data)

    return PlainTextResponse("Success")
