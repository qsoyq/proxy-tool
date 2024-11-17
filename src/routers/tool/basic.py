import logging
from typing import List
from fastapi import APIRouter, Query, Response

import random

router = APIRouter(tags=["tool"], prefix="/api/tool")

logger = logging.getLogger(__file__)


@router.get("/eat", summary="今天吃什么")
def eat(choices: List[str] = Query(..., description="选择列表, 随机返回一个")):
    return Response(
        content=f"今天吃 {random.choice(choices)} !", headers={"content-type": "text/plain; charset=utf-8"}
    )
