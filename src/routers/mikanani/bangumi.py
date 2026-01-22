import logging
from concurrent.futures import ThreadPoolExecutor

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Path, Query
from fastapi.responses import PlainTextResponse
from schemas.mikanani import mikanani_bangumi_torrent_responses

executor = ThreadPoolExecutor()
router = APIRouter(tags=['Utils'], prefix='/mikanani/bangumi')
logger = logging.getLogger(__file__)


@router.get('/{bangumi_id}/torrent', summary='蜜柑计划磁链', responses=mikanani_bangumi_torrent_responses)
async def torrent(filter_words: str | None = Query(None), bangumi_id: int = Path(...)):
    """根据正则过滤, 然后导出网页中的磁链

    如: https://mikanani.me/Home/Bangumi/3585
    """
    url = f'https://mikanani.me/Home/Bangumi/{bangumi_id}'
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        text = resp.text

    soup = BeautifulSoup(text, 'lxml')
    links = []
    for item in soup.select('#sk-container > div.central-container > table > tbody > tr > td'):
        a = item.select_one('a')
        if a is None:
            continue
        if filter_words and filter_words not in a.text:
            continue
        link = item.select_one('a.js-magnet.magnet-link')
        if link:
            magnet_link = link.attrs['data-clipboard-text']
            if magnet_link:
                links.append(str(magnet_link))
    return PlainTextResponse('\n'.join(links))
