import html
import re
import logging
import httpx

from fastapi import APIRouter

from schemas.bilibili.live.room import BilibiliRoomInfoScheme, BilibiliAnchorInRoomScheme, LiveRoomResponseSchema

router = APIRouter(tags=["bilibili.live"], prefix="/bilibili/live/room")

logger = logging.getLogger(__file__)


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
    return BilibiliRoomInfoScheme(**resp.json().get("data", {}))


def getAnchorInRoom(roomId: str) -> BilibiliAnchorInRoomScheme:
    "https://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room?roomid="
    url = "https://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": f"https://live.bilibili.com/{roomId}",
    }
    parmas = {"roomid": roomId}
    resp = httpx.get(url, params=parmas, headers=headers)
    resp.raise_for_status()
    return BilibiliAnchorInRoomScheme(**resp.json()["data"]["info"])


@router.get("/{roomId}", response_model=LiveRoomResponseSchema)
def room(roomId):
    roomInfo = getLiveRoomInfo(roomId)
    userInfo = getAnchorInRoom(roomId)
    if roomInfo.description:
        roomInfo.description = remove_html_tags(html.unescape(roomInfo.description.replace("<br>", "\n")))

    return {
        "roomInfo": roomInfo,
        "userInfo": userInfo,
        "isAlive": roomInfo.is_alive,
        "pubDate": roomInfo.pub_date,
        "roomLink": roomInfo.room_link,
    }
