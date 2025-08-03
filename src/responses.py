import json
from fastapi.responses import JSONResponse


class PingResponse(JSONResponse):
    def render(self, content: dict) -> bytes:
        return json.dumps(content, indent=4).encode("utf-8")
