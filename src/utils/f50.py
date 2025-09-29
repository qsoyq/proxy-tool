import httpx
from fastapi import HTTPException
from schemas.f50 import Message


class SMS:
    def __init__(
        self,
        password: str,
        host: str = "http://192.168.0.1",
        sessionid: str = "txpgva0w2nc31aru1rh9uvk6h",
    ):
        self._host = host
        self._password = password
        self._sessionid = sessionid

    @property
    def headers(self) -> dict:
        headers = {
            "Cookie": f"JSESSIONID={self._sessionid}",
            "Referer": f"{self._host}/index.html",
        }
        return headers

    async def login(self):
        async with httpx.AsyncClient(headers=self.headers) as client:
            content = f"isTest=false&goformId=LOGIN&password={self._password}"
            url = f"{self._host}/goform/goform_set_cmd_process"
            res = await client.post(url, content=content)
            if res.is_error:
                raise HTTPException(res.status_code, detail=res.text)
            body = res.json()
            assert body.get("result", 0) == 0

    async def get_sms_list(self) -> list[Message]:
        async with httpx.AsyncClient(headers=self.headers) as client:
            url = f"{self._host}/goform/goform_get_cmd_process"
            res = await client.get(url, params={"cmd": "sms_data_total", "page": 0, "data_per_page": 500})
            if res.is_error:
                raise HTTPException(res.status_code, detail=res.text)
            body = res.json()
            assert "messages" in body
        return [Message(**payload) for payload in body["messages"]]
