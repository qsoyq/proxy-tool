import html
import re
import asyncio
import logging
import httpx
from typing import List
from fastapi import APIRouter, Query
from concurrent.futures import ThreadPoolExecutor

from schemas.bilibili.live.room import (
    BilibiliRoomInfoScheme,
    BilibiliAnchorInRoomScheme,
    LiveRoomResponseSchema,
    LiveRoomListRes,
    get_live_room_list_responses,
)

router = APIRouter(tags=["Utils"], prefix="/bilibili/live/room")

logger = logging.getLogger(__file__)
room_thread_executor = ThreadPoolExecutor()


def remove_html_tags(text: str):
    # 定义一个正则表达式，用于匹配HTML标签
    html_tags_re = re.compile(r"<[^>]+>")
    # 使用sub方法替换掉所有HTML标签为空字符串
    return html_tags_re.sub("", text)


async def getLiveRoomInfo(roomId: int):
    url = "https://api.live.bilibili.com/room/v1/Room/get_info"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    }
    params = {"room_id": str(roomId), "from": "room"}
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
    data = resp.json().get("data")
    assert data, resp.text
    return BilibiliRoomInfoScheme(**data)


async def getAnchorInRoom(roomId: int) -> BilibiliAnchorInRoomScheme:
    "https://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room?roomid="
    url = "https://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": f"https://live.bilibili.com/{roomId}",
    }
    params = {"roomid": roomId}
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json().get("data")
    assert data, resp.text
    return BilibiliAnchorInRoomScheme(**data["info"])


async def getRoomById(roomId: int) -> LiveRoomResponseSchema:
    roomInfo = await getLiveRoomInfo(roomId)
    userInfo = await getAnchorInRoom(roomId)
    if roomInfo.description:
        roomInfo.description = remove_html_tags(html.unescape(roomInfo.description.replace("<br>", "\n")))

    body = {
        "roomInfo": roomInfo,
        "userInfo": userInfo,
        "isAlive": roomInfo.is_alive,
        "pubDate": roomInfo.pub_date,
        "roomLink": roomInfo.room_link,
    }
    return LiveRoomResponseSchema(**body)


@router.get(
    "/list",
    summary="查询哔哩哔哩直播间列表信息",
    response_model=LiveRoomListRes,
    responses=get_live_room_list_responses,
)
async def room_list(rooms: List[int] = Query(..., description="直播间 id 列表")):
    li = await asyncio.gather(*[getRoomById(roomId) for roomId in rooms])
    return {"list": li}


@router.get("/{roomId}", summary="查询哔哩哔哩直播间信息", response_model=LiveRoomResponseSchema, deprecated=True)
async def room(roomId: int = Query(..., description="直播间 id")):
    return await getRoomById(roomId)
