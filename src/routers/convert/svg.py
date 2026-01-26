import io
import logging

import cairosvg
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from schemas.adapter import HttpUrl

router = APIRouter(tags=["Utils"], prefix="/convert/svg")

logger = logging.getLogger(__file__)


@router.get("/png", summary="svg2png")
async def convert_svg_to_png(url: HttpUrl, download: bool = Query(False, description="是否下载文件")):
    # 使用 cairosvg 将 SVG 转换为 PNG
    png_content = cairosvg.svg2png(url=url)
    if not isinstance(png_content, bytes):
        raise HTTPException(status_code=500, detail="Format conversion failed.")
    # 返回 PNG 文件
    response = StreamingResponse(
        io.BytesIO(png_content),
        media_type="image/png",
    )
    if download:
        response.headers["Content-Disposition"] = "attachment; filename=converted.png"
    return response
