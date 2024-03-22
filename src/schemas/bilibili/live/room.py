from datetime import datetime
from dateutil import parser
from pydantic import BaseModel


class BilibiliRoomInfoScheme(BaseModel):
    uid: int
    room_id: int
    title: str | None
    description: str | None
    live_status: int | None
    live_time: str | None
    user_cover: str | None
    keyframe: str | None

    @property
    def room_link(self):
        return f"https://live.bilibili.com/{self.room_id}"

    @property
    def pub_date(self) -> datetime:
        assert self.live_time
        return parser.parse(self.live_time)

    @property
    def is_alive(self) -> bool:
        return self.live_status == 1

    def if_push(self, last_pub_date: datetime | int | str | None) -> bool:
        if last_pub_date is None:
            return True

        if isinstance(last_pub_date, str):
            last_pub_date = parser.parse(last_pub_date)

        if isinstance(last_pub_date, int):
            return int(self.pub_date.timestamp()) > last_pub_date

        if isinstance(last_pub_date, datetime):
            return int(self.pub_date.timestamp()) > int(last_pub_date.timestamp())


class BilibiliAnchorInRoomScheme(BaseModel):
    uid: int
    uname: str
    face: str | None


class LiveRoomResponseSchema(BaseModel):
    userInfo: BilibiliAnchorInRoomScheme
    roomInfo: BilibiliRoomInfoScheme
    isAlive: bool
    pubDate: datetime
    roomLink: str
