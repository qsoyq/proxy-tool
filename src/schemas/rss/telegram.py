from pydantic import BaseModel, Field
from schemas.adapter import HttpUrl


class TelegramChannalMessage(BaseModel):
    head: str | None = Field(None)
    msgid: str
    channelName: str
    username: str
    title: str
    text: str
    updated: str
    authorName: str | None = Field(None)
    contentHtml: str | None = Field(None)
    photoUrls: list[HttpUrl] | None = Field(None)
    tags: list[str] = Field([])
