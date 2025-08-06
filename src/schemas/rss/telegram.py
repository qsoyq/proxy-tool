from pydantic import BaseModel


class TelegramChannalMessage(BaseModel):
    head: str
    msgid: str
    channelName: str
    username: str
    title: str
    text: str
    updated: str
