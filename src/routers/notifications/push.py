from enum import Enum
import tempfile
import yagmail
import logging
import json
import httpx
from pydantic import BaseModel, Field
from http import HTTPStatus

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, RedirectResponse
from concurrent.futures import ThreadPoolExecutor
from schemas import ErrorDetail


class GmailOauth2File(BaseModel):
    email_address: str
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str


class GmailPushMessage(BaseModel):
    to: str | list[str]
    subject: str
    contents: str | list[str]

    sender: str
    password: str | None = Field(None, description="使用密码登录时需要该值")
    oauth2_file: GmailOauth2File | None = Field(
        None,
        description="使用 oauth2 验证时需要该对象. 见 https://github.com/kootenpv/yagmail?tab=readme-ov-file#oauth2",
    )

    def push(self) -> None:
        yag: yagmail.SMTP | None = None
        if self.password:
            yag = yagmail.SMTP(self.sender, self.password)

        elif self.oauth2_file:
            with tempfile.NamedTemporaryFile("w+") as f:
                f.write(json.dumps(self.oauth2_file.dict()))
                f.seek(0)
                yag = yagmail.SMTP(self.sender, oauth2_file=f.name)

        assert yag

        if isinstance(self.contents, str):
            self.contents = [self.contents]

        if isinstance(self.to, str):
            self.to = [self.to]

        for to in self.to:
            yag.send(to=to, subject=self.subject, contents=self.contents)


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


class GotifyPushMessageDetail(BaseModel):
    """https://redocly.github.io/redoc/?url=%20https://raw.githubusercontent.com/gotify/server/v2.5.0/docs/spec.json#tag/message/operation/createMessage"""

    title: str | None
    message: str
    priority: int = Field(0, description="https://github.com/gotify/android?tab=readme-ov-file#message-priorities")
    extra: dict | None


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


class PushMessage(BaseModel):
    telegram: TelegramPushMessage | None
    gmail: GmailPushMessage | None
    bark: BarkPushMessage | None


class PushMessageV3(BaseModel):
    telegram: TelegramPushMessageV3 | None
    gmail: GmailPushMessage | None
    bark: BarkPushMessage | None
    gotify: GotifyPushMessage | None


class PushMessages(BaseModel):
    messages: list[PushMessage]


class PushMessagesV3(BaseModel):
    messages: list[PushMessageV3]


router = APIRouter(tags=["notifications.push"], prefix="/notifications")
logger = logging.getLogger(__file__)


@router.post("/push", summary="消息推送")
def push(messages: PushMessages):
    """推送消息到各平台
    Gmail推送消息对账号密码有要求, 需要开启二步验证后使用应用程序专用密码或使用 OAuth2 令牌.
    """
    details = []
    for i, message in enumerate(messages.messages):
        loc = ["body", "messages", i]
        try:
            current = ""
            if message.telegram:
                current = "telegram"
                message.telegram.push()
            if message.gmail:
                current = "gmail"
                message.gmail.push()
            if message.bark:
                current = "bark"
                message.bark.push()
        except Exception as e:
            logger.warning(e, exc_info=True)
            loc.append(current)
            details.append({"type": "value_error", "loc": loc, "message": f"{e}"})
    if details:
        return JSONResponse(content={"detail": details}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
    return {}


@router.post("/push/v2", summary="消息推送v2")
def push_v2(messages: PushMessages):
    """推送消息到各平台
    Gmail推送消息对账号密码有要求, 需要开启二步验证后使用应用程序专用密码或使用 OAuth2 令牌.

    采用并发处理多条消息
    """

    def handle_message(index: int, message: PushMessage) -> ErrorDetail | None:
        detail = None
        loc = ["body", "messages", index]
        try:
            current = ""
            if message.telegram:
                current = "telegram"
                message.telegram.push()
            if message.gmail:
                current = "gmail"
                message.gmail.push()
            if message.bark:
                current = "bark"
                message.bark.push()
        except Exception as e:
            logger.warning(e, exc_info=True)
            loc.append(current)
            detail = ErrorDetail(**{"type": "value_error", "loc": loc, "message": f"{e}"})
        return detail

    with ThreadPoolExecutor(thread_name_prefix="notifications.push.") as executor:
        arguments = [range(len(messages.messages)), messages.messages]
        results = executor.map(handle_message, *arguments)
    details = [x for x in results if x]
    if details:
        return JSONResponse(content={"detail": details}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
    return {}


@router.post("/push/v3", summary="消息推送v3")
def push_v3(messages: PushMessagesV3):
    """支持Telegram 多种消息类型

    采用并发处理多条消息
    """

    def handle_message(index: int, message: PushMessageV3) -> ErrorDetail | None:
        detail = None
        loc = ["body", "messages", index]
        try:
            current = ""
            if message.telegram:
                current = "telegram"
                if message.telegram.message:
                    current = "telegram.message"
                    message.telegram.push_text()
                if message.telegram.photo:
                    current = "telegram.photo"
                    message.telegram.push_photo()
                if message.telegram.media:
                    current = "telegram.media"
                    message.telegram.push_media()
            if message.gmail:
                current = "gmail"
                message.gmail.push()
            if message.bark:
                current = "bark"
                message.bark.push()
            if message.gotify:
                current = "gotify"
                message.gotify.push()
        except Exception as e:
            logger.warning(e, exc_info=True)
            loc.append(current)
            detail = ErrorDetail(**{"type": "value_error", "loc": loc, "message": f"{e}"})
        return detail

    with ThreadPoolExecutor(thread_name_prefix="notifications.push.") as executor:
        arguments = [range(len(messages.messages)), messages.messages]
        results = executor.map(handle_message, *arguments)
    details = [x for x in results if x]
    if details:
        return JSONResponse(content={"detail": details}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
    return {}


@router.get("/oauth2/google/refresh_token")
def redirect_to_refresh_token(client_id: str = Query(...)):
    """返回 Google OAuth2 授权获取 RefreshToken 的页面"""
    url = f"https://accounts.google.com/o/oauth2/auth?client_id={client_id}&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://mail.google.com/"
    return RedirectResponse(url)
