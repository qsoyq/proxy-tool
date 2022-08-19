from pydantic import BaseModel


class ClashProxyModel(BaseModel):
    name: str
    server: str
    port: int
    type: str
    cipher: str
    password: str


class ClashModel(BaseModel):
    proxies: list[ClashProxyModel]
