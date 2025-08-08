from datetime import datetime
from dateutil import parser
from pydantic import BaseModel


class BilibiliRoomInfoScheme(BaseModel):
    uid: int
    room_id: int
    title: str | None = None
    description: str | None = None
    live_status: int | None = None
    live_time: str | None = None
    user_cover: str | None = None
    keyframe: str | None = None

    @property
    def room_link(self):
        return f"https://live.bilibili.com/{self.room_id}"

    @property
    def pub_date(self) -> datetime | None:
        assert self.live_time
        # 鬼知道 bilibili 的接口为什么会返回这种字符串
        if self.live_time == "0000-00-00 00:00:00":
            return None
        return parser.parse(self.live_time)

    @property
    def is_alive(self) -> bool:
        return self.live_status == 1

    def if_push(self, last_pub_date: datetime | int | str | None) -> bool:
        if last_pub_date is None:
            return True

        if self.pub_date is None:
            return False

        if isinstance(last_pub_date, str):
            last_pub_date = parser.parse(last_pub_date)

        if isinstance(last_pub_date, int):
            return int(self.pub_date.timestamp()) > last_pub_date

        if isinstance(last_pub_date, datetime):
            return int(self.pub_date.timestamp()) > int(last_pub_date.timestamp())


class BilibiliAnchorInRoomScheme(BaseModel):
    uid: int
    uname: str
    face: str | None = None


class LiveRoomResponseSchema(BaseModel):
    userInfo: BilibiliAnchorInRoomScheme
    roomInfo: BilibiliRoomInfoScheme
    isAlive: bool
    pubDate: datetime | None = None
    roomLink: str


class LiveRoomListRes(BaseModel):
    list: list[LiveRoomResponseSchema]


live_room_list_success_example = {
    "list": [
        {
            "userInfo": {
                "uid": 3494368814041403,
                "uname": "莓泥小酱",
                "face": "https://i2.hdslb.com/bfs/face/98c9bbc2edbd32e9873941b9af9cddb985622386.jpg",
            },
            "roomInfo": {
                "uid": 3494368814041403,
                "room_id": 30167396,
                "title": "【歌杂】小唱一晚！",
                "description": "",
                "live_status": 1,
                "live_time": "2025-04-22 02:11:38",
                "user_cover": "https://i0.hdslb.com/bfs/live/new_room_cover/ca7fc707cc2edda2707ab27ff0458e5e82e87d5e.jpg",
                "keyframe": "https://i0.hdslb.com/bfs/live-key-frame/keyframe04220340000030167396pocyax.jpg",
            },
            "isAlive": True,
            "pubDate": "2025-04-22T02:11:38",
            "roomLink": "https://live.bilibili.com/30167396",
        }
    ]
}

get_live_room_list_responses: dict[int | str, dict[str, object]] = {
    200: {
        "description": "200 Successful Response",
        "content": {"application/json": {"example": live_room_list_success_example}},
    }
}
