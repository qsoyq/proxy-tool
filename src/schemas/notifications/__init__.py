from pydantic import BaseModel

import schemas.notifications.apple as apple_
import schemas.notifications.bark as bark_
import schemas.notifications.gmail as gmail_
import schemas.notifications.gotify as gotify_
import schemas.notifications.telegram as telegram_


class PushMessage(BaseModel):
    telegram: telegram_.TelegramPushMessage | None = None
    gmail: gmail_.GmailPushMessage | None = None
    bark: bark_.BarkPushMessage | None = None


class PushMessageV3(BaseModel):
    telegram: telegram_.TelegramPushMessageV3 | None = None
    gmail: gmail_.GmailPushMessage | None = None
    bark: bark_.BarkPushMessage | None = None
    gotify: gotify_.GotifyPushMessage | None = None
    apple: apple_.ApplePushMessage | None = None


class PushMessages(BaseModel):
    messages: list[PushMessage]


class PushMessagesV3(BaseModel):
    messages: list[PushMessageV3]
