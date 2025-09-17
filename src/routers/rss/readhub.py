import re
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException
from bs4 import BeautifulSoup as Soup, Tag
from schemas.rss.jsonfeed import JSONFeed, JSONFeedItem
from responses import PrettyJSONResponse


router = APIRouter(tags=["RSS"], prefix="/rss/readhub")

logger = logging.getLogger(__file__)


def parseArticle(article: Tag, date_published: str) -> dict:
    linkTag = article.select_one("a")
    contentTag = article.select_one("p")
    assert linkTag, article
    assert contentTag, article

    title = linkTag.getText()
    url = f'https://readhub.cn{linkTag.attrs["href"]}'
    content_html = str(contentTag)
    return {
        "id": f"readhub-daily-{title}",
        "title": title,
        "url": url,
        "content_html": content_html,
        "date_published": date_published,
    }


@router.get("/daily", summary="无码科技每日早报", response_model=JSONFeed, response_class=PrettyJSONResponse)
def daily(req: Request):
    """无码科技每日早报"""
    host = req.url.hostname
    items: list[JSONFeedItem] = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "无码科技每日早报",
        "description": "",
        "home_page_url": "https://readhub.cn/daily",
        "feed_url": f"{req.url.scheme}://{host}{req.url.path}?{req.url.query}",
        "icon": "https://readhub.cn/favicon.ico",
        "favicon": "https://readhub.cn/favicon.ico",
        "items": items,
    }

    url = "https://www.readhub.cn/daily"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    res = httpx.get(url, headers=headers, verify=False)
    if res.is_error:
        raise HTTPException(res.status_code, f"fetch readhub daily error: {res.text}")

    document = Soup(res.text, "lxml")
    dateTag = document.select_one("div > span")
    assert dateTag, document
    date_published = dateTag.getText()
    if re.match(r"\d{4}.\d{2}.\d{2}", date_published):
        date_published = f"{date_published.replace('.', '-')}T00:00:00+08:00"

    items = [JSONFeedItem(**(parseArticle(article, date_published))) for article in document.select("article")]
    feed["items"] = items
    return feed
