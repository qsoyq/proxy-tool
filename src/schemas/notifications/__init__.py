from pydantic import BaseModel
import schemas.notifications.telegram as telegram
import schemas.notifications.bark as bark
import schemas.notifications.gmail as gmail
import schemas.notifications.gotify as gotify
import schemas.notifications.apple as apple


class PushMessage(BaseModel):
    telegram: telegram.TelegramPushMessage | None
    gmail: gmail.GmailPushMessage | None
    bark: bark.BarkPushMessage | None


class PushMessageV3(BaseModel):
    telegram: telegram.TelegramPushMessageV3 | None
    gmail: gmail.GmailPushMessage | None
    bark: bark.BarkPushMessage | None
    gotify: gotify.GotifyPushMessage | None
    apple: apple.ApplePushMessage | None


class PushMessages(BaseModel):
    messages: list[PushMessage]


class PushMessagesV3(BaseModel):
    messages: list[PushMessageV3]
