import logging
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from dateutil import parser
from fastapi import APIRouter, Header, Query
from pydantic import BaseModel, Field


class Topic(BaseModel):
    id: str
    title: str
    last_touched: int
    lastTouchedStr: str = Field(..., description='最后回复时间, 日期字符串, 如 2024-04-27 05:00:42 +08:00')


class GetTopicsRes(BaseModel):
    topics: list[Topic]
    has_next_page: bool = Field(..., description='是否还有下一页')


@dataclass
class GetTopicsData:
    topics: list[Topic]
    has_next_page: bool


router = APIRouter(tags=['Utils'], prefix='/v2ex/my')

logger = logging.getLogger(__file__)


def get_topics(session_key: str, page: int = 1) -> GetTopicsData:
    topics = []
    url = 'https://www.v2ex.com/my/topics'
    res = httpx.get(url, params={'p': page}, cookies={'A2': session_key})
    res.raise_for_status()
    soup = BeautifulSoup(res.text, features='lxml')
    items = soup.find_all('div', class_='cell item')
    ele = soup.select_one('td[title="Next Page"]')
    has_next_page = True if ele and 'disable_now' not in ele.attrs.get('class', []) else False

    for item in items:
        link = item.find('a', class_='topic-link')  # type:ignore
        title = link.text  # type:ignore
        tid = link.attrs['id'].split('-')[-1]  # type:ignore
        lastTouchedStr = str(item.find('span', class_='topic_info').find('span').attrs['title'])  # type:ignore
        last_touched = int(parser.parse(lastTouchedStr).timestamp())
        topics.append(Topic(id=tid, title=title, lastTouchedStr=lastTouchedStr, last_touched=last_touched))
    return GetTopicsData(topics=topics, has_next_page=has_next_page)


@router.get('/topics', summary='V2ex收藏主题列表', response_model=GetTopicsRes)
def my_topics(
    session_key: str = Header(..., alias='A2', description='session, 对应 v2ex 网页请求中的 Cookie.A2字段'),
    page: int = Query(1, alias='p', description='页码'),
):
    res = get_topics(session_key, page)
    return {'topics': res.topics, 'has_next_page': res.has_next_page}
