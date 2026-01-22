import logging
from typing import cast

from fastapi import APIRouter, Path, Query
from schemas.f50 import GetSmsListRes
from utils.f50 import SMS

router = APIRouter(tags=['Utils'], prefix='/tool/f50')

logger = logging.getLogger(__file__)


@router.get('/sms/{password}', summary='F50查询短信列表', response_model=GetSmsListRes)
async def sms_list(
    password: str = Path(..., description='编码后的字符串'),
    number: str | None = Query(None, description='按照号码过滤'),
):
    sms = SMS(password)
    await sms.login()
    messages = await sms.get_sms_list()

    messages.sort(key=lambda x: -cast(int, x.timestamp))
    if number is not None:
        messages = [x for x in messages if x.number == number]
    return {'messages': messages}
