import asyncio
import logging
import socket
from copy import deepcopy
from datetime import datetime
from functools import cache

import httpx
import pytz
import yaml
from fastapi import APIRouter, Path, Query
from fastapi.responses import PlainTextResponse, Response

from models import ClashModel
from settings import RegionCodeTable

router = APIRouter(tags=['Proxy'], prefix='/clash')

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
    proxies = ['auto'] + [proxy.name for proxy in clash.proxies]

    auto_proxies = [proxy.name for proxy in clash.proxies]
    proxy_groups: list[dict] = [
        {'name': 'proxies', 'type': 'select', 'proxies': proxies},
        {
            'name': 'auto',
            'type': 'url-test',
            'proxies': auto_proxies,
            'url': 'https://www.gstatic.com/generate_204',
            'interval': interval,
        },
    ]
    return proxy_groups


def country_code_to_emoji(country_code: str) -> str | None:
    country_code = country_code.upper()
    three_to_two = {
        'USA': 'US',
        'CAN': 'CA',
        'GBR': 'GB',
        'FRA': 'FR',
        'DEU': 'DE',
    }
    if len(country_code) == 3:
        country_code = three_to_two.get(country_code, country_code[:2])
    if len(country_code) != 2:
        return None
    base_code_point = 127397  # U+1F1E6 - U+0041
    code_points = [base_code_point + ord(char) for char in country_code]
    emoji_chars = [chr(cp) for cp in code_points]
    return ''.join(emoji_chars)


@cache
def add_emoji_prefix(name: str) -> str:
    """http://www.freejson.com/countrycode.html"""
    for region, code in RegionCodeTable.items():
        if region in name:
            emoji = country_code_to_emoji(code)
            if emoji and emoji not in name:
                name = name.replace(region, f'{emoji}{region}')
    return name


@router.head('/timeout/{timeout}', include_in_schema=False)
@router.get('/timeout/{timeout}')
async def timeout(timeout: float | None = Path(..., description='可控的阻塞时间')):
    if timeout is not None:
        await asyncio.sleep(timeout)
    return ''


@router.get('/subscribe', summary='Clash订阅转换')
@router.head('/subscribe', include_in_schema=False)
async def subscribe(
    user_agent: str = Query('clash.meta'),
    url: str = Query(..., description='订阅链接'),
    proxy_provider: bool = Query(False, description='是否只返回节点', alias='proxy-provider'),
    sort_by_name: bool = Query(True, description='按名称排序节点', alias='sort-by-name'),
    additional_prefix: str | None = Query(
        None, description='为代理节点添加前缀, 在只返回节点模式下有效', alias='additional-prefix'
    ),
    emoji_additional_prefix: bool = Query(
        True, description='按节点地区添加 emoji 前缀, 在只返回节点模式下有效', alias='emoji-additional-prefix'
    ),
    benchmark_url: str | None = Query(
        None, description='延迟测试连接, 如: http://cp.cloudflare.com/', alias='benchmark-url'
    ),
    benchmark_timeout: float | None = Query(None, description='延迟测试超时，单位: 秒', alias='benchmark-timeout'),
    subscription_remark: str = Query('统计', description='订阅数据统计标识符'),
    add_total_used_remark: bool = Query(True, description='是否添加一个标注流量使用的节点'),
    add_refresh_time_remark: bool = Query(True, description='是否添加一个订阅更新日期的节点'),
    add_expire_remark: bool = Query(True, description='是否添加一个标注过期时间的节点'),
):
    headers = {}
    if user_agent is not None:
        headers['user-agent'] = user_agent
    async with httpx.AsyncClient(headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        # if resp.is_error:
        #     raise HTTPException(status_code=resp.status_code, detail=resp.text)

    # 订阅信息字段
    headers = {}
    for field in (
        'profile-update-interval',
        'profile-web-page-url',
        'subscription-userinfo',
    ):
        if field in resp.headers:
            headers[field] = resp.headers[field]
    subscription = headers.get('subscription-userinfo')
    subscription_meta = {}
    if subscription:
        subscription_meta = {k.strip(): v.strip() for item in subscription.split(';') for k, v in [item.split('=')]}

    content = resp.text
    try:
        document = yaml.safe_load(content)
    except Exception:
        return PlainTextResponse('解析订阅失败，未返回合法的 YAML 格式数据', status_code=400)

    if benchmark_url:
        for x in document.get('proxies', []):
            x['benchmark-url'] = benchmark_url

    if benchmark_timeout:
        for x in document.get('proxies', []):
            x['benchmark-timeout'] = benchmark_timeout

    if proxy_provider:
        if additional_prefix:
            for x in document.get('proxies', []):
                x['name'] = additional_prefix + x['name']
        if emoji_additional_prefix:
            for x in document.get('proxies', []):
                x['name'] = add_emoji_prefix(x['name'])

        document = {'proxies': document['proxies']}

    if sort_by_name:
        document['proxies'] = sorted(document['proxies'], key=lambda x: x['name'])
    if document.get('proxies'):
        try:
            tz = pytz.timezone('Asia/Shanghai')
            if add_expire_remark and subscription_meta.get('expire'):
                remark = (
                    datetime.fromtimestamp(int(subscription_meta['expire']))
                    .astimezone(tz)
                    .strftime('%Y-%m-%d %H:%M:%S CST')
                )
                name = f'{additional_prefix}{subscription_remark}｜expire｜{remark}'
                add_remark_node(document['proxies'], name)

            if add_refresh_time_remark:
                remark = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S CST')
                name = f'{additional_prefix}{subscription_remark}｜update｜{remark}'
                add_remark_node(document['proxies'], name)

            if add_total_used_remark and subscription_meta.get('total'):
                total = float(subscription_meta['total']) / 1024 / 1024 / 1024
                used = float(
                    (int(subscription_meta['upload']) + int(subscription_meta['download'])) / 1024 / 1024 / 1024
                )
                remark = f'{used:.2f}/{total:.2f}GB'
                name = f'{additional_prefix}{subscription_remark}｜{remark}'
                add_remark_node(document['proxies'], name)

        except Exception as e:
            logger.warning(f'[Clash Subscribe] add subscription remark error: {e}')

    content = yaml.safe_dump(document, allow_unicode=True)
    headers['content-type'] = 'text/plain;charset=utf-8'
    return Response(content=content, status_code=resp.status_code, headers=headers)


def add_remark_node(proxies: list, name: str):
    p = deepcopy(proxies[0])
    p['name'] = name
    p['benchmark-disabled'] = True
    proxies.append(p)
