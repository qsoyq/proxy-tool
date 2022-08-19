import base64
import urllib.parse

import httpx
import yaml

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from pydantic import HttpUrl

from models import ClashModel

router = APIRouter(tags=["clash"], prefix='/clash')


@router.get("/subscribe")
async def clash2subscribe(clash_url: HttpUrl = Query(..., description="clash 订阅地址")):
    cli = httpx.AsyncClient()
    res = await cli.get(clash_url)
    doc = yaml.load(res.text, None)
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
