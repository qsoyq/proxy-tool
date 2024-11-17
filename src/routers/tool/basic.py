import urllib.parse
import logging
from typing import List
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

import random

router = APIRouter(tags=["tool"], prefix="/tool")

logger = logging.getLogger(__file__)


@router.get("/eat", summary="今天吃什么")
def eat(choices: List[str] = Query(..., description="选择列表, 随机返回一个")):
    select = random.choice(choices)
    meituanwaimai = urllib.parse.quote(f"meituanwaimai://waimai.meituan.com/search?query={select}")
    meituanwaimai_href = f"https://p.19940731.xyz/api/network/url/redirect?url={meituanwaimai}"

    eleme = f"eleme://search?keyword={select}"
    eleme_href = f"https://p.19940731.xyz/api/network/url/redirect?url={eleme}"

    dianping = f"dianping://searchshoplist?keyword={select}"
    dianping_href = f"https://p.19940731.xyz/api/network/url/redirect?url={dianping}"
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
    return HTMLResponse(content=body, headers={"content-type": "text/html; charset=UTF-8"})
