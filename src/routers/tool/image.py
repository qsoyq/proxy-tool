import logging

import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["Utils"], prefix="/tool")

logger = logging.getLogger(__file__)


@router.get("/image/random", summary="随机图片", name="random_image")
async def random_image():
    """数据来源: https://random.img.ibytebox.com/

    https://www.nodeseek.com/post-428917-1
    """
    url = "https://random.img.ibytebox.com/?format=json&image_format=webp"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        body = res.json()
        return RedirectResponse(body["image"]["original_url"])
