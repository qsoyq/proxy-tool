import base64
from datetime import datetime
from pydantic import Field, BaseModel, model_validator


class Message(BaseModel):
    id: str = Field(...)
    content: str = Field(..., description="短信内容, 需要进行 base64 解码")
    tag: str = Field(..., description="0表示收信, 2 表示发信")
    date: str = Field(..., description="原始格式: 25,09,29,07,42,56,+0800")
    number: str = Field(..., description="对方号码", examples=["10086"])
    timestamp: int | None = Field(None, description="时间戳，校验时初始化")

    @model_validator(mode="after")
    def check_content(cls, values):
        try:
            values.content = base64.b64decode(values.content).decode()
        except Exception:
            pass
        return values

    @model_validator(mode="after")
    def check_date(cls, values):
        try:
            date = datetime.strptime(values.date, r"%y,%m,%d,%H,%M,%S,%z")
            values.timestamp = int(date.timestamp())
            values.date = date.strftime("%Y-%m-%dT%H:%M:%S%z")
        except Exception:
            return values

        return values


class GetSmsListRes(BaseModel):
    messages: list[Message]
