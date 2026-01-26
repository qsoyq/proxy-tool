from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    loc: list = Field([])
    message: str = Field("")
    type: str = Field("")


class ErrorResponse(BaseModel):
    detail: list[ErrorDetail]
