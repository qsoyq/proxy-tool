import httpx
from pydantic import BaseModel, Field


class GotifyPushMessageDetail(BaseModel):
    """https://redocly.github.io/redoc/?url=%20https://raw.githubusercontent.com/gotify/server/v2.5.0/docs/spec.json#tag/message/operation/createMessage"""

    title: str | None = None
    message: str
    priority: int = Field(0, description="https://github.com/gotify/android?tab=readme-ov-file#message-priorities")
    extra: dict | None = None


class GotifyPushMessage(BaseModel):
    """https://redocly.github.io/redoc/?url=%20https://raw.githubusercontent.com/gotify/server/v2.5.0/docs/spec.json#tag/message/operation/createMessage"""

    token: str
    detail: GotifyPushMessageDetail
    click_url: str | None = Field(None, description="点击通知后打开的 url")

    def push(self) -> httpx.Response:
        url = f"https://gotify.19940731.xyz/message?token={self.token}"
        payload = self.detail.dict()
        if self.click_url:
            if not self.detail.extra:
                payload["extras"] = {}
            payload.setdefault("extras", {}).setdefault("client::notification", {}).setdefault("click", {}).setdefault(
                "url", self.click_url
            )
        res = httpx.post(url, json=payload)
        res.raise_for_status()
        return res
