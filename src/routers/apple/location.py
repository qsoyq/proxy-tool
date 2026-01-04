import logging

from fastapi import APIRouter, Path
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=['Utils'], prefix='/apple')

logger = logging.getLogger(__file__)


@router.get('/location/{code}', summary='返回路径中的地区代码')
def code(code: str = Path(..., description='地区代码， 见 https://www.geonames.org/countries/')):
    return PlainTextResponse(code)
