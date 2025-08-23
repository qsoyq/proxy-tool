import logging
from typing import Any
import httpx
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from schemas.rss.jsonfeed import JSONFeed, JSONFeedItem, JSONFeedAuthor
from responses import PrettyJSONResponse


router = APIRouter(tags=["RSS"], prefix="/rss/1024.day")

logger = logging.getLogger(__file__)


class User(BaseModel):
    id: str
    avatarUrl: str | None = Field(None)
    displayName: str | None = Field(None)
    username: str | None = Field(None)


class Post(BaseModel):
    id: str
    title: str
    subscription: str | None = Field(None)
    createdAt: str
    shareUrl: str


@router.get("/newest", summary="1024.day 新贴 RSS 订阅", response_model=JSONFeed, response_class=PrettyJSONResponse)
def jsonfeed(req: Request):
    """1024.day 新鲜出炉 rss 订阅

    jsonfeed 格式
    """
    host = req.url.hostname
    items: list[JSONFeedItem] = []
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "1024.day",
        "description": "新鲜出炉",
        "home_page_url": "https://1024.day",
        "feed_url": f"{req.url.scheme}://{host}{req.url.path}?{req.url.query}",
        "icon": "https://1024.day/favicon.ico",
        "favicon": "https://1024.day/favicon.ico",
        "items": items,
    }

    url = "https://1024.day/api/discussions?include=user%2ClastPostedUser%2Ctags%2Ctags.parent%2CfirstPost&sort=-createdAt&page%5Boffset%5D=0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    res = httpx.get(url, headers=headers, verify=False)
    if res.is_error:
        raise HTTPException(res.status_code, f"fetch 1024.day error: {res.text}")

    data = res.json()

    users = {
        x["id"]: User(
            id=x["id"],
            avatarUrl=x["attributes"]["avatarUrl"],
            displayName=x["attributes"]["displayName"],
            username=x["attributes"]["username"],
        )
        for x in data["included"]
        if x["type"] == "users"
    }

    for item in data["data"]:
        _id = item["id"]
        payload = item["attributes"]
        payload["id"] = _id
        post = Post.model_construct(**payload)
        _payload: dict[str, Any] = {
            "id": f"{post.id}",
            "title": post.title,
            "content_html": post.subscription or "",
            "url": post.shareUrl,
            "date_published": post.createdAt,
        }
        u = users.get(item["relationships"]["user"]["data"]["id"])
        if u:
            _payload["author"] = JSONFeedAuthor(
                **{
                    "url": f"https://1024.day/u/{u.username}",
                    "name": u.displayName,
                    "avatar": u.avatarUrl,
                }
            )
        items.append(JSONFeedItem(**_payload))
    return feed
