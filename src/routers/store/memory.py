import logging
import time
from typing import Any

from fastapi import APIRouter, Body, Path
from pydantic import BaseModel


class MemoryState(BaseModel):
    content: Any = None
    created: int
    updated: int


class MemoryScheme(BaseModel):
    state: MemoryState | None = None


router = APIRouter(tags=["Utils"], prefix="/store")
logger = logging.getLogger(__file__)

MEMO: dict[str, MemoryState] = {}


@router.get("/memory/{key}", response_model=MemoryScheme, summary="读取临时缓存")
def memory_get(key: str = Path(...)):
    content = MEMO.get(key)
    return {"state": content}


@router.post("/memory/{key}", summary="写入临时缓存")
def memory_post(
    content: Any = Body(..., embed=True),
    key: str = Path(...),
):
    global MEMO
    current = int(time.time())
    state = MEMO.get(key) or MemoryState(content=content, created=current, updated=current)
    state.content = content
    state.updated = current
    MEMO[key] = state
    return {}
