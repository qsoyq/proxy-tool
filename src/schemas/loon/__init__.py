from enum import Enum
from typing import Any

from pydantic import BaseModel


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
