from typing import Any
from pydantic import BaseModel
from enum import Enum


class ArgumentTypeEnum(str, Enum):
    intput = "input"
    select = "select"
    switch = "switch"


class LoonArgument(BaseModel):
    name: str
    type: str
    desc: str
    tag: str
    default: Any
    values: list[Any]
