from enum import Enum

import httpx
from pydantic import BaseModel, Field


class BarkPushLevel(str, Enum):
    active = 'active'
    timeSensitive = 'timeSensitive'
    passive = 'passive'
    critical = 'critical'


class BarkPushMessage(BaseModel):
    """https://github.com/Finb/bark-server/blob/master/docs/API_V2.md"""

    device_key: str = Field(..., description='bark token, The key for each device')

    title: str
    body: str = Field(..., max_length=1024, description='bark-server 或 APNs 的限制约在 1600 个字符')
    level: BarkPushLevel = Field(
        BarkPushLevel.active, description="'active', 'timeSensitive', or 'passive', or 'critical'"
    )

    category: str | None = Field(None, description='Reserved field, no use yet')

    badge: int | None = Field(
        None,
        description='The number displayed next to App icon ([Apple Developer](https://developer.apple.com/documentation/usernotifications/unnotificationcontent/1649864-badge))',
    )
    automaticallyCopy: str | None = Field(None, description='Must be 1')
    copy_: str | None = Field(None, description='The value to be copied', alias='copy')
    sound: str | None = Field(None, description='Value from [here](https://github.com/Finb/Bark/tree/master/Sounds)')
    icon: str | None = Field(None, description='An url to the icon, available only on iOS 15 or later')
    group: str | None = Field(None, description='The group of the notification')
    isArchive: str | None = Field(None, description='Value must be 1. Whether or not should be archived by the app')
    url: str | None = Field(None, description='Url that will jump when click notification')
    endpoint: str = Field('https://api.day.app/push', description='服务端请求地址')

    def push(self) -> httpx.Response:
        payload = self.dict(exclude={'endpoint'})
        payload = {k: v for k, v in payload.items() if v is not None}
        resp = httpx.post(self.endpoint, json=payload)
        resp.raise_for_status()
        return resp
