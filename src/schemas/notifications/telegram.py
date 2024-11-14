import httpx
from pydantic import BaseModel, Field


class TelegramPushMessage(BaseModel):
    """https://core.telegram.org/bots/api#sendmessage"""

    bot_id: str
    chat_id: str
    text: str

    def push(self) -> httpx.Response:
        url = f"https://api.telegram.org/bot{self.bot_id}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": self.text}
        res = httpx.post(url, json=payload)
        res.raise_for_status()
        return res


class TelegramPushMessageText(BaseModel):
    text: str = Field(..., min_length=1, max_length=4096)
    parse_mode: str | None = Field(None, description="见: https://core.telegram.org/bots/api#formatting-options")


class TelegramPushMessagePhoto(BaseModel):
    photo: str
    caption: str | None


class TelegramPushMessageMediaDetail(BaseModel):
    type: str = Field("photo")
    media: str = Field(...)
    caption: str | None


class TelegramPushMessageV3(BaseModel):
    """https://core.telegram.org/bots/api#sendmessage"""

    bot_id: str
    chat_id: str
    message: TelegramPushMessageText | None
    photo: TelegramPushMessagePhoto | None
    media: list[TelegramPushMessageMediaDetail] | None

    def push(self):
        raise NotImplementedError("TelegramPushMessageV3 不支持 push 方法")

    def push_text(self) -> httpx.Response:
        url = f"https://api.telegram.org/bot{self.bot_id}/sendMessage"
        assert self.message
        payload = {"chat_id": self.chat_id, "text": self.message.text}
        if self.message.parse_mode:
            payload["parse_mode"] = self.message.parse_mode

        res = httpx.post(url, json=payload)
        res.raise_for_status()
        return res

    def push_photo(self) -> httpx.Response:
        url = f"https://api.telegram.org/bot{self.bot_id}/sendPhoto"
        assert self.photo
        payload = {"chat_id": self.chat_id, "photo": self.photo.photo}
        if self.photo.caption:
            payload["caption"] = self.photo.caption
        res = httpx.post(url, json=payload)
        res.raise_for_status()
        return res

    def push_media(self) -> httpx.Response:
        url = f"https://api.telegram.org/bot{self.bot_id}/sendMediaGroup"
        assert self.media
        payload = {"chat_id": self.chat_id, "media": [x.dict() for x in self.media]}
        res = httpx.post(url, json=payload)
        res.raise_for_status()
        return res
