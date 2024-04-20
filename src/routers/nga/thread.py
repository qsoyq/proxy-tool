from enum import Enum
import logging
import json
import httpx
from pydantic import BaseModel, Field
from fastapi import APIRouter, Query, Header
from datetime import datetime


class OrderByEnum(str, Enum):
    lastpostdesc = "lastpostdesc"
    postdatedesc = "postdatedesc"


class Thread(BaseModel):
    tid: int
    fid: int
    subject: str
    postdate: int
    lastpost: int
    lastpostStr: str | None = Field(None)
    postdateStr: str | None = Field(None)
    url: str | None = Field(None, description="帖子网页链接")
    ios_app_scheme_url: str | None = Field(None)
    ios_open_scheme_url: str | None = Field(None, description="通过 http 重定向打开 app")


class Threads(BaseModel):
    threads: list[Thread]


router = APIRouter(tags=["nga.thread"], prefix="/nga")

logger = logging.getLogger(__file__)

url = "https://bbs.nga.cn/thread.php?fid=-7&lite=js"

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1"


def get_threads(
    uid: str,
    cid: str,
    order_by: OrderByEnum | None = OrderByEnum.lastpostdesc,
    *,
    fid: int | None = None,
    favor: int | None = None,
) -> Threads:
    url = "https://bbs.nga.cn/thread.php"

    headers = {"user-agent": UA}
    cookies = {
        "ngaPassportUid": uid,
        "ngaPassportCid": cid,
    }

    params: dict[str, str | int] = {
        "__output": 11,  # 返回 json 格式
    }

    if fid is not None:
        params["fid"] = fid
    if favor is not None:
        params["favor"] = favor

    if order_by is not None:
        params["order_by"] = str(order_by.value)

    res = httpx.get(url, params=params, cookies=cookies, headers=headers)
    res.raise_for_status()
    body = json.loads(res.text)
    threads = Threads(threads=[Thread(**t) for t in body["data"]["__T"]])
    for t in threads.threads:
        t.postdateStr = datetime.fromtimestamp(t.postdate).strftime(r"%Y-%m-%d %H:%M:%S")
        t.lastpostStr = datetime.fromtimestamp(t.lastpost).strftime(r"%Y-%m-%d %H:%M:%S")
        t.url = f"https://bbs.nga.cn/read.php?tid={t.tid}"
        t.ios_app_scheme_url = f"nga://opentype=2?tid={t.tid}&"
        t.ios_open_scheme_url = f"https://proxy-tool.19940731.xyz/api/network/url/redirect?url={t.ios_app_scheme_url}"
    return threads


@router.get("/threads", response_model=Threads)
def threads(
    fid: int | None = Query(None, description="分区ID"),
    favor: int | None = Query(None, description="收藏夹ID"),
    uid: str = Header("", description="ngaPassportUid, 验签"),
    cid: str = Header("", description="ngaPassportCid, 验签"),
    order_by: OrderByEnum = Query(..., description="排序规则"),
):
    return get_threads(uid, cid, order_by, fid=fid, favor=favor)
