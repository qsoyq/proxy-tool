import httpx
import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter

router = APIRouter(tags=["checkin"], prefix="/api/checkin/flyairport")

logger = logging.getLogger(__file__)


class FlyairportCheckinReq(BaseModel):
    email: str
    key: str
    uid: str
    expire_in: str = Field(..., description="秒时间戳")


class FlyairportCheckinRes(BaseModel):
    ret: int = Field(0)
    msg: str = Field("")


@router.post("/", summary="flyairport 机场签到", response_model=FlyairportCheckinRes)
def _checkin(payload: FlyairportCheckinReq):
    """签到领取流量"""
    url = "https://flyairport.top/user/checkin"
    cookies = payload.dict()
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    resp = httpx.post(url, cookies=cookies, headers={"User-Agent": ua})
    resp.raise_for_status()
    return resp.json()
