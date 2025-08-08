from enum import Enum
import logging
import json
import httpx
from pydantic import BaseModel, Field
from fastapi import APIRouter, Query, Header
from datetime import datetime
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, Future


class ForumSectionIndex(BaseModel):
    fid: int = Field(description="版面id 或当前子板面的父版面 id")
    name: str
    stid: int | None = Field(None, description="部分分区子板面的id")
    info: str | None = Field(None)
    icon: str | None = Field(None, description="分区对应的logo")


class GetForumSectionsRes(BaseModel):
    sections: list[ForumSectionIndex] = Field([])


class OrderByEnum(str, Enum):
    lastpostdesc = "lastpostdesc"
    postdatedesc = "postdatedesc"


class Thread(BaseModel):
    tid: int
    fid: int
    fname: str | None = Field(None, description="fid 对应的分区名称")
    icon: str | None = Field(None, description="主题对应的分区logo")
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


class ThreadsGroup(BaseModel):
    fid: int | None = None
    favor: int | None = None
    threads: list[Thread]


class GetThreadsV2Res(BaseModel):
    data: list[ThreadsGroup]


router = APIRouter(tags=["Utils"], prefix="/nga")

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
    if_include_child_node: bool | None = None,
    page: int = 1,
) -> Threads:
    url = "https://bbs.nga.cn/thread.php"

    headers = {"user-agent": UA}
    cookies = {
        "ngaPassportUid": uid,
        "ngaPassportCid": cid,
    }

    params: dict[str, str | int] = {
        "__output": 11,  # 返回 json 格式
        "page": page,
    }

    if fid is not None:
        params["fid"] = fid
    if favor is not None:
        params["favor"] = favor

    if order_by is not None:
        params["order_by"] = str(order_by.value)

    res = httpx.get(url, params=params, cookies=cookies, headers=headers, verify=False)
    res.raise_for_status()
    body = json.loads(res.text)
    threads = Threads(threads=[Thread(**t) for t in body["data"].get("__T", [])])

    if fid and not if_include_child_node:
        threads.threads = [t for t in threads.threads if t.fid == fid]

    sections = get_sections()
    # nga 混用了 fid 和 stid 的概念, 当存在 stid 时, stid 即请求对应的 fid
    sections_dict = {(x.stid or x.fid): x for x in sections.sections}

    for t in threads.threads:
        t.postdateStr = datetime.fromtimestamp(t.postdate).strftime(r"%Y-%m-%d %H:%M:%S")
        t.lastpostStr = datetime.fromtimestamp(t.lastpost).strftime(r"%Y-%m-%d %H:%M:%S")
        t.url = f"https://bbs.nga.cn/read.php?tid={t.tid}"
        t.ios_app_scheme_url = f"nga://opentype=2?tid={t.tid}&"
        t.ios_open_scheme_url = f"https://proxy-tool.19940731.xyz/api/network/url/redirect?url={t.ios_app_scheme_url}"
        section = sections_dict.get(t.fid)
        if section:
            t.fname = section.name
            t.icon = section.icon
    return threads


@router.get("/threads", summary="查询NGA帖子列表", response_model=Threads)
def threads(
    fid: int | None = Query(None, description="分区ID"),
    favor: int | None = Query(None, description="收藏夹ID"),
    uid: str = Header("", description="ngaPassportUid, 验签"),
    cid: str = Header("", description="ngaPassportCid, 验签"),
    order_by: OrderByEnum = Query(..., description="排序规则"),
    if_include_child_node: bool | None = Query(None, description="当查询分区帖子时, 时候包含子分区的帖子"),
    page: int = Query(1, description="页"),
):
    return get_threads(
        uid, cid, order_by, fid=fid, favor=favor, if_include_child_node=if_include_child_node, page=page
    )


@router.get("/threads/v2", summary="批量查询NGA多分区/收藏夹帖子列表", response_model=GetThreadsV2Res)
def threads_v2(
    fid_li: list[int] | None = Query(None, description="分区ID", alias="fid"),
    favor_li: list[int] | None = Query(None, description="收藏夹ID", alias="favor"),
    uid: str = Header("", description="ngaPassportUid, 验签"),
    cid: str = Header("", description="ngaPassportCid, 验签"),
    order_by: OrderByEnum = Query(..., description="排序规则"),
    if_include_child_node: bool | None = Query(None, description="当查询分区帖子时, 是否包含子分区的帖子"),
    page: int = Query(1, description="页"),
):
    data = []
    with ThreadPoolExecutor() as executor:
        tasks: dict[int, Future[Threads]] = {}
        for fid in fid_li or []:
            t = executor.submit(
                get_threads,
                uid,
                cid,
                order_by,
                fid=fid,
                favor=None,
                if_include_child_node=if_include_child_node,
                page=page,
            )
            tasks[fid] = t
        for fid, t in tasks.items():
            threads = t.result()
            data.append({"fid": fid, "favor": None, "threads": threads.threads})

        tasks = {}
        for favor in favor_li or []:
            t = executor.submit(
                get_threads,
                uid,
                cid,
                order_by,
                fid=None,
                favor=favor,
                if_include_child_node=if_include_child_node,
                page=page,
            )
            tasks[favor] = t
        for favor, t in tasks.items():
            threads = t.result()
            data.append({"fid": None, "favor": favor, "threads": threads.threads})

    return {"data": data}


@router.get("/sections", summary="查询NGA分区信息", response_model=GetForumSectionsRes)
def sections():
    return get_sections()


@lru_cache()
def get_sections() -> GetForumSectionsRes:
    """获取论坛分区信息"""
    sections = []
    url = "https://img4.nga.178.com/proxy/cache_attach/bbs_index_data.js"
    resp = httpx.get(url, verify=False)
    resp.raise_for_status()
    data = json.loads(resp.text[33:])
    for section in data["data"]["0"]["all"].values():
        for item in section["content"].values():
            for detail in item["content"].values():
                id_ = detail.get("stid") or detail["fid"]
                icon = f"https://img4.nga.178.com/proxy/cache_attach/ficon/{id_}u.png"
                sections.append(
                    ForumSectionIndex(
                        fid=detail["fid"],
                        name=detail["name"],
                        stid=detail.get("stid"),
                        info=detail.get("info"),
                        icon=icon,
                    )
                )
    return GetForumSectionsRes(sections=sections)
