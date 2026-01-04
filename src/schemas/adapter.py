from typing import Annotated

from pydantic import AnyHttpUrl, BeforeValidator, TypeAdapter

HttpUrlTypeAdapter = TypeAdapter(AnyHttpUrl)
HttpUrl = Annotated[
    str,
    BeforeValidator(lambda value: HttpUrlTypeAdapter.validate_python(value) and value),
]

KeyValuePairStr = Annotated[
    str,
    BeforeValidator(lambda value: '=' in value and value),
]
