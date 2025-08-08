import json
from fastapi.responses import JSONResponse


class PrettyJSONResponse(JSONResponse):
    def render(self, content: dict) -> bytes:
        return json.dumps(content, indent=4).encode("utf-8")


class PingResponse(PrettyJSONResponse):
    pass
