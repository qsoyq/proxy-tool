import logging
from http import HTTPStatus

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, RedirectResponse
from concurrent.futures import ThreadPoolExecutor
from schemas import ErrorDetail
from schemas.notifications import PushMessage, PushMessageV3, PushMessages, PushMessagesV3

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
        return JSONResponse(
            content={"detail": [x.dict() for x in details]}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR
        )
    return {}


@router.get("/oauth2/google/refresh_token")
def redirect_to_refresh_token(client_id: str = Query(...)):
    """返回 Google OAuth2 授权获取 RefreshToken 的页面"""
    url = f"https://accounts.google.com/o/oauth2/auth?client_id={client_id}&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://mail.google.com/"
    return RedirectResponse(url)
