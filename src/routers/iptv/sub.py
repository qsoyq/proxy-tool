import asyncio
import logging

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=['Utils'], prefix='/iptv')

logger = logging.getLogger(__file__)


async def fetch_iptv_content(url: str, user_agent: str, timeout: float) -> httpx.Response | None:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers={'user-agent': user_agent}, timeout=timeout, follow_redirects=True)
            return resp
        except httpx.TimeoutException as e:
            logger.warning(f'fetch url {url} timeout: {e}')
        except Exception as e:
            logger.warning(f'fetch url {url} error: {e}')
    return None


@router.get('/subscribe', summary='IPTV订阅转换')
def sub(
    user_agent: str = Query('AptvPlayer/1.3.9', description='User-Agent'),
    timeout: float = Query(3, description='单个订阅地址的超时时间'),
    urls: list[str] = Query(..., description='订阅地址'),
):
    content = ''
    texts = []
    for url in urls:
        try:
            resp = httpx.get(url, headers={'user-agent': user_agent}, timeout=timeout)
        except httpx.TimeoutException as e:
            logger.warning(f'fetch url {url} timeout: {e}')
        if resp.is_error:
            logger.warning(f'fetch url {url} error: {resp.status_code}, body: {resp.text}')
        else:
            texts.append(resp.text)
    content = '\n'.join(texts)
    return PlainTextResponse(content)


@router.get('/subscribe/v2', summary='IPTV订阅转换')
async def sub_v2(
    user_agent: str = Query('AptvPlayer/1.3.9', description='User-Agent'),
    timeout: float = Query(10, description='单个订阅地址的超时时间'),
    urls: list[str] = Query(..., description='订阅地址'),
):
    texts = []
    tasks = [fetch_iptv_content(url, user_agent, timeout) for url in urls]
    resp = await asyncio.gather(*tasks)
    for r in resp:
        if r is None:
            continue
        if r.is_error:
            logger.warning(f'fetch url {r.url} error: {r.status_code}, body: {r.text}')
        else:
            texts.append(r.text)
    content = '\n'.join(texts)
    return PlainTextResponse(content)
