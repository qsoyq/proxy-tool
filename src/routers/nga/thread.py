import logging
import asyncio

from fastapi import APIRouter, Query, Header
from schemas.nga.thread import OrderByEnum, Threads, GetForumSectionsRes, GetThreadsV2Res, GetNGASmiles
from utils import NgaToolkit  # type: ignore


router = APIRouter(tags=["Utils"], prefix="/nga")

logger = logging.getLogger(__file__)

url = "https://bbs.nga.cn/thread.php?fid=-7&lite=js"


@router.get("/threads", summary="查询NGA帖子列表", response_model=Threads)
async def threads(
    fid: int | None = Query(None, description="分区ID"),
    favor: int | None = Query(None, description="收藏夹ID"),
    uid: str = Header(..., description="ngaPassportUid, 验签"),
    cid: str = Header(..., description="ngaPassportCid, 验签"),
    order_by: OrderByEnum = Query("lastpostdesc", description="排序规则"),
    if_include_child_node: bool | None = Query(None, description="当查询分区帖子时, 时候包含子分区的帖子"),
    page: int = Query(1, description="页"),
):
    return await NgaToolkit.get_threads(
        uid, cid, order_by, fid=fid, favor=favor, if_include_child_node=if_include_child_node, page=page
    )


@router.get("/threads/v2", summary="批量查询NGA多分区/收藏夹帖子列表", response_model=GetThreadsV2Res)
async def threads_v2(
    fid_li: list[int] | None = Query(None, description="分区ID", alias="fid"),
    favor_li: list[int] | None = Query(None, description="收藏夹ID", alias="favor"),
    uid: str = Header(..., description="ngaPassportUid, 验签"),
    cid: str = Header(..., description="ngaPassportCid, 验签"),
    order_by: OrderByEnum = Query("lastpostdesc", description="排序规则"),
    if_include_child_node: bool | None = Query(None, description="当查询分区帖子时, 是否包含子分区的帖子"),
    page: int = Query(1, description="页"),
):
    data = []
    if fid_li:
        tasks = [NgaToolkit.get_threads(uid, cid, order_by, fid=fid) for fid in fid_li]
        res = await asyncio.gather(*tasks)
        for index, threads in enumerate(res):
            if not threads:
                continue
            data.append({"fid": fid_li[index], "favor": None, "threads": threads.threads})

    if favor_li:
        tasks = [NgaToolkit.get_threads(uid, cid, order_by, favor=favor) for favor in favor_li]
        res = await asyncio.gather(*tasks)
        for index, threads in enumerate(res):
            if not threads:
                continue
            data.append({"fid": None, "favor": favor_li[index], "threads": threads.threads})

    return {"data": data}


@router.get("/sections", summary="查询NGA分区信息", response_model=GetForumSectionsRes)
async def sections():
    return await NgaToolkit.get_sections()


@router.get("/smiles", summary="查询NGA表情信息", response_model=GetNGASmiles)
def smiles():
    smiles = NgaToolkit.get_smiles()
    return {"data": smiles}
