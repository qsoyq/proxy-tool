import io
import logging
import cairosvg
from pydantic import BaseModel, Field, HttpUrl
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["convert.svg"], prefix="/convert/svg")

logger = logging.getLogger(__file__)


class XMLConvertRes(BaseModel):
    content: str = Field(..., description="json字符串")


class XMLConvertReq(BaseModel):
    content: str = Field(..., description="xml字符串")


@router.get("/png")
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
