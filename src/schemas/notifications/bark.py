from enum import Enum
import httpx
from pydantic import BaseModel, Field


class BarkPushLevel(str, Enum):
    active = "active"
    timeSensitive = "timeSensitive"
    passive = "passive"


class BarkPushMessage(BaseModel):
    """https://github.com/Finb/bark-server/blob/master/docs/API_V2.md
    ```
    level:
        active:默认值,系统会立即亮屏显示通知。
        timeSensitive:时效性通知,可在专注状态下显示通知。
        passive: 仅将通知添加到通知列表,不会亮屏提醒。
    ```
    """

    device_key: str = Field(..., description="bark token, The key for each device")

    title: str
    body: str
    level: BarkPushLevel = Field(BarkPushLevel.active, description="'active', 'timeSensitive', or 'passive'")

    category: str | None = Field(None, description="Reserved field, no use yet")

    badge: int | None = Field(
        None,
        description="The number displayed next to App icon ([Apple Developer](https://developer.apple.com/documentation/usernotifications/unnotificationcontent/1649864-badge))",
    )
    automaticallyCopy: str | None = Field(None, description="Must be 1")
    _copy: str | None = Field(None, description="The value to be copied", alias="copy")
    sound: str | None = Field(None, description="Value from [here](https://github.com/Finb/Bark/tree/master/Sounds)")
    icon: str | None = Field(None, description="An url to the icon, available only on iOS 15 or later")
    group: str | None = Field(None, description="The group of the notification")
    isArchive: str | None = Field(None, description="Value must be 1. Whether or not should be archived by the app")
    url: str | None = Field(None, description="Url that will jump when click notification")
    endpoint: str = Field("https://api.day.app/push", description="服务端请求地址")

    def push(self) -> httpx.Response:
        payload = self.dict(exclude={"endpoint"})
        payload = {k: v for k, v in payload.items() if v is not None}
        resp = httpx.post(self.endpoint, json=payload)
        resp.raise_for_status()
        return resp
