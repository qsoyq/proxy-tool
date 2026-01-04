import logging
import random
import urllib.parse
from typing import List

import httpx
from bs4 import BeautifulSoup as soup
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field


class CountryCodeSchema(BaseModel):
    name: str = Field(..., description='名称, 如中国')
    code: str = Field(..., description='代码, 如CN')


class CountryCodeResSchema(BaseModel):
    data: list[CountryCodeSchema]


router = APIRouter(tags=['Utils'], prefix='/tool')

logger = logging.getLogger(__file__)


@router.get('/eat', summary='今天吃什么')
def eat(choices: List[str] = Query(..., description='选择列表, 随机返回一个')):
    select = random.choice(choices)
    meituanwaimai = urllib.parse.quote(f'meituanwaimai://waimai.meituan.com/search?query={select}')
    meituanwaimai_href = f'https://p.19940731.xyz/api/network/url/redirect?url={meituanwaimai}'

    eleme = f'eleme://search?keyword={select}'
    eleme_href = f'https://p.19940731.xyz/api/network/url/redirect?url={eleme}'

    dianping = f'dianping://searchshoplist?keyword={select}'
    dianping_href = f'https://p.19940731.xyz/api/network/url/redirect?url={dianping}'
    body = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title></title>
        <style>
            .container {{
                text-align: center; /* 居中对齐 */
                margin-top: 50px; /* 上边距 */
            }}
            .main-text {{
                font-size: 24px; /* 大一点的文本 */
            }}
            .link {{
                font-size: 14px; /* 小一点的链接文本 */
                display: inline-block; /* 使链接在一行显示 */
                margin: 0 10px; /* 左右间距 */
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <p class="main-text">今天吃 {select} !</p>
            <a href="{meituanwaimai_href}" class="link">点击跳转到美团外卖</a>
            <br>
            <br>
            <a href="{eleme_href}" class="link">点击跳转到饿了么</a>
            <br>
            <br>
            <a href="{dianping_href}" class="link">点击跳转到大众点评</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=body, headers={'content-type': 'text/html; charset=UTF-8'})


@router.get('/countrycode/freejson', response_model=CountryCodeResSchema)
def countrycode():
    """数据来源: http://www.freejson.com/countrycode.html"""
    url = 'http://www.freejson.com/countrycode.html'
    res = httpx.get(url, verify=False)
    res.raise_for_status()

    document = soup(res.text, 'lxml')
    tbody = document.select_one('tbody')
    ret = []
    more = {'尼尔利亚': 'NG', '台湾': 'TW'}
    mapping = {}
    if tbody:
        trs = tbody.select('tr')
        if trs:
            trs = trs[1:]
            for tr in trs:
                tds = tr.select('td')
                _, name, code, _, _ = tds
                if name.text and code.text and code.text != '\xa0':
                    mapping[name.text] = code.text
    mapping.update(more)
    ret = [{'name': name, 'code': code} for name, code in mapping.items()]
    return ret
