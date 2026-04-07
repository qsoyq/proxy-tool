from typing import Annotated

from pydantic import BeforeValidator
from pydantic import HttpUrl as PydanticHttpUrl
from pydantic import TypeAdapter

HttpUrlTypeAdapter = TypeAdapter(PydanticHttpUrl)
HttpUrl = Annotated[
    str,
    BeforeValidator(lambda value: HttpUrlTypeAdapter.validate_python(value) and value),
]

KeyValuePairStr = Annotated[
    str,
    BeforeValidator(lambda value: "=" in value and value),
]
