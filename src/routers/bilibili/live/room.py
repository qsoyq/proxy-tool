import html
import re
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
)

router = APIRouter(tags=["bilibili.live"], prefix="/bilibili/live/room")

logger = logging.getLogger(__file__)
room_thread_executor = ThreadPoolExecutor()


def remove_html_tags(text: str):
    # 定义一个正则表达式，用于匹配HTML标签
    html_tags_re = re.compile(r"<[^>]+>")
    # 使用sub方法替换掉所有HTML标签为空字符串
    return html_tags_re.sub("", text)


def getLiveRoomInfo(roomId: str):
    url = "https://api.live.bilibili.com/room/v1/Room/get_info"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    }
    params = {"room_id": roomId, "from": "room"}
    resp = httpx.get(url, params=params, headers=headers, verify=False)
    resp.raise_for_status()
    data = resp.json().get("data")
    assert data, resp.text
    return BilibiliRoomInfoScheme(**data)


def getAnchorInRoom(roomId: str) -> BilibiliAnchorInRoomScheme:
    "https://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room?roomid="
    url = "https://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": f"https://live.bilibili.com/{roomId}",
    }
    params = {"roomid": roomId}
    resp = httpx.get(url, params=params, headers=headers)
    resp.raise_for_status()
    data = resp.json().get("data")
    assert data, resp.text
    return BilibiliAnchorInRoomScheme(**data["info"])


def getRoomById(roomId: str) -> LiveRoomResponseSchema:
    roomInfo = getLiveRoomInfo(roomId)
    userInfo = getAnchorInRoom(roomId)
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


@router.get("/list", summary="查询直播间列表信息", response_model=LiveRoomListRes)
def room_list(rooms: List[int] = Query(..., description="直播间 id 列表")):
    li = list(room_thread_executor.map(getRoomById, map(str, rooms)))
    # for roomId in rooms:
    #     li.append(getRoomById(str(roomId)))
    return {"list": li}


@router.get("/{roomId}", summary="查询直播间信息", response_model=LiveRoomResponseSchema)
def room(roomId: int = Query(..., description="直播间 id")):
    return getRoomById(str(roomId))
