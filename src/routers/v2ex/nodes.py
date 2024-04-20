import logging
from datetime import datetime
import httpx
from pydantic import BaseModel, Field
from fastapi import APIRouter, Query, Header, Path


class BaseTopic(BaseModel):
    id: int
    title: str
    content: str
    content_rendered: str
    syntax: int
    url: str
    replies: int
    last_reply_by: str
    created: int
    last_modified: int
    last_touched: int


class Topic(BaseTopic):
    createdStr: str | None = Field(None)
    lastModifiedStr: str | None = Field(None)
    lastTouchedStr: str | None = Field(None)


class Node(BaseModel):
    id: int
    url: str
    name: str
    title: str
    header: str
    footer: str
    avatar: str
    topics: int = Field(..., description="主题数量")
    created: int
    last_modified: int


class GetTopicsRes(BaseModel):
    topics: list[Topic]
    node: Node


class GetNodeRes(BaseModel):
    node: Node


router = APIRouter(tags=["v2ex.nodes"], prefix="/v2ex/nodes")

logger = logging.getLogger(__file__)


def get_node(node: str, token: str) -> Node:
    url = f"https://www.v2ex.com/api/v2/nodes/{node}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = httpx.get(url, headers=headers)
    resp.raise_for_status()
    assert resp.json()["success"], resp.text
    return Node(**resp.json()["result"])


def get_topics(node: str, token: str, page: int = 1) -> list[Topic]:
    url = f"https://www.v2ex.com/api/v2/nodes/{node}/topics"
    headers = {"Authorization": f"Bearer {token}"}
    resp = httpx.get(url, params={"p": page}, headers=headers)
    resp.raise_for_status()
    assert resp.json()["success"], resp.text
    topics = [Topic(**x) for x in resp.json()["result"]]
    for topic in topics:
        topic.createdStr = datetime.fromtimestamp(topic.created).strftime(r"%Y-%m-%d %H:%M:%S")
        topic.lastModifiedStr = datetime.fromtimestamp(topic.last_modified).strftime(r"%Y-%m-%d %H:%M:%S")
        topic.lastTouchedStr = datetime.fromtimestamp(topic.last_touched).strftime(r"%Y-%m-%d %H:%M:%S")
    return topics


@router.get("/{node}", response_model=GetNodeRes)
def node(
    node: str = Path(..., description="节点名词， 如 python、gts"),
    token: str = Header(..., alias="Authorization"),
):
    return {"node": get_node(node, token)}


@router.get("/{node}/topics", response_model=GetTopicsRes)
def topics(
    node: str = Path(..., description="节点名词， 如 python、gts"),
    p: int = Query(1, description="分页"),
    token: str = Header(..., alias="Authorization"),
):
    return {"topics": get_topics(node, token, page=p), "node": get_node(node, token)}