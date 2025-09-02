from typing import Annotated
from pydantic import TypeAdapter, HttpUrl as _HttpUrl, BeforeValidator


HttpUrlTypeAdapter = TypeAdapter(_HttpUrl)
HttpUrl = Annotated[
    str,
    BeforeValidator(lambda value: HttpUrlTypeAdapter.validate_python(value) and value),
]

KeyValuePairStr = Annotated[
    str,
    BeforeValidator(lambda value: "=" in value and value),
]
