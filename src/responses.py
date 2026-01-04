import json

from fastapi.responses import JSONResponse


class PrettyJSONResponse(JSONResponse):
    media_type = 'application/json;charset=utf-8'

    def render(self, content: dict) -> bytes:
        return json.dumps(content, indent=4, ensure_ascii=False).encode('utf-8')


class PingResponse(PrettyJSONResponse):
    pass
