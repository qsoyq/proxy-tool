from dateutil import parser
from bs4 import BeautifulSoup
import logging
import httpx
from pydantic import BaseModel, Field
from fastapi import APIRouter, Header


class Topic(BaseModel):
    id: str
    title: str
    last_touched: int
    lastTouchedStr: str = Field(..., description="最后回复时间, 日期字符串, 如 2024-04-27 05:00:42 +08:00")


class GetTopicsRes(BaseModel):
    topics: list[Topic]


router = APIRouter(tags=["v2ex.my"], prefix="/v2ex/my")

logger = logging.getLogger(__file__)


def get_topics(session_key: str) -> list[Topic]:
    topics = []
    url = "https://www.v2ex.com/my/topics"
    res = httpx.get(url, cookies={"A2": session_key})
    res.raise_for_status()
    soup = BeautifulSoup(res.text)
    items = soup.find_all("div", class_="cell item")
    for item in items:
        link = item.find("a", class_="topic-link")
        title = link.text
        tid = link.attrs["id"].split("-")[-1]
        lastTouchedStr = item.find("span", class_="topic_info").find("span").attrs["title"]
        last_touched = int(parser.parse(lastTouchedStr).timestamp())
        topics.append(Topic(id=tid, title=title, lastTouchedStr=lastTouchedStr, last_touched=last_touched))
    return topics


@router.get("/topics", response_model=GetTopicsRes)
def my_topics(session_key: str = Header(..., alias="A2", description="session, 对应 v2ex 网页请求中的 Cookie.A2字段")):
    return {"topics": get_topics(session_key)}
