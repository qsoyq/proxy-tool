import logging

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["Utils"], prefix="/network/url")

logger = logging.getLogger(__file__)


@router.get("/redirect", summary="链接重定向")
def redirect(
    url: str = Query(..., description="待重定向的参数"),
):
    """返回重定向到传递的参数"""
    return RedirectResponse(url)
