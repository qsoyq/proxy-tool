import logging
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, RedirectResponse

from schemas import ErrorDetail
from schemas.notifications import (PushMessage, PushMessages, PushMessagesV3,
                                   PushMessageV3)

router = APIRouter(tags=['Basic'], prefix='/notifications')
logger = logging.getLogger(__file__)


@router.post('/push', summary='消息推送')
def push(messages: PushMessages):
    details = []
    for i, message in enumerate(messages.messages):
        loc = ['body', 'messages', i]
        try:
            current = ''
            if message.telegram:
                current = 'telegram'
                message.telegram.push()
            if message.gmail:
                current = 'gmail'
                message.gmail.push()
            if message.bark:
                current = 'bark'
                message.bark.push()
        except Exception as e:
            logger.warning(e, exc_info=True)
            loc.append(current)
            details.append({'type': 'value_error', 'loc': loc, 'message': f'{e}'})
    if details:
        return JSONResponse(content={'detail': details}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
    return {}


@router.post('/push/v2', summary='消息推送v2')
def push_v2(messages: PushMessages):
    def handle_message(index: int, message: PushMessage) -> ErrorDetail | None:
        detail = None
        loc = ['body', 'messages', index]
        try:
            current = ''
            if message.telegram:
                current = 'telegram'
                message.telegram.push()
            if message.gmail:
                current = 'gmail'
                message.gmail.push()
            if message.bark:
                current = 'bark'
                message.bark.push()
        except Exception as e:
            logger.warning(e, exc_info=True)
            loc.append(current)
            detail = ErrorDetail(**{'type': 'value_error', 'loc': loc, 'message': f'{e}'})
        return detail

    with ThreadPoolExecutor(thread_name_prefix='notifications.push.') as executor:
        arguments = [range(len(messages.messages)), messages.messages]
        results = executor.map(handle_message, *arguments)
    details = [x for x in results if x]
    if details:
        return JSONResponse(content={'detail': details}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
    return {}


@router.post('/push/v3', summary='消息推送v3')
def push_v3(messages: PushMessagesV3):
    def handle_message(index: int, message: PushMessageV3) -> ErrorDetail | None:
        detail = None
        loc = ['body', 'messages', index]
        try:
            current = ''
            if message.telegram:
                current = 'telegram'
                if message.telegram.message:
                    current = 'telegram.message'
                    message.telegram.push_text()
                if message.telegram.photo:
                    current = 'telegram.photo'
                    message.telegram.push_photo()
                if message.telegram.media:
                    current = 'telegram.media'
                    message.telegram.push_media()
            if message.gmail:
                current = 'gmail'
                message.gmail.push()
            if message.bark:
                current = 'bark'
                message.bark.push()
            if message.gotify:
                current = 'gotify'
                message.gotify.push()
            if message.apple:
                current = 'apple'
                message.apple.push()
        except Exception as e:
            logger.warning(e, exc_info=True)
            loc.append(current)
            detail = ErrorDetail(**{'type': 'value_error', 'loc': loc, 'message': f'{e}'})
        return detail

    with ThreadPoolExecutor(thread_name_prefix='notifications.push.') as executor:
        arguments = [range(len(messages.messages)), messages.messages]
        results = executor.map(handle_message, *arguments)
    details = [x for x in results if x]
    if details:
        return JSONResponse(
            content={'detail': [x.dict() for x in details]}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR
        )
    return {}


@router.get('/oauth2/google/refresh_token', include_in_schema=False)
def redirect_to_refresh_token(client_id: str = Query(...)):
    """返回 Google OAuth2 授权获取 RefreshToken 的页面"""
    url = f'https://accounts.google.com/o/oauth2/auth?client_id={client_id}&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://mail.google.com/'
    return RedirectResponse(url)
