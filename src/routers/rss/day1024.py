import logging
from typing import Any
import dateparser
import httpx
from fastapi import APIRouter, Request, Response, HTTPException
from pydantic import BaseModel, Field
import feedgen.feed
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


@router.get("/newest/v1", summary="1024.day 新贴 RSS 订阅", deprecated=True, include_in_schema=False)
def rss(req: Request):
    """1024.day 新鲜出炉 rss 订阅"""
    host = req.url.hostname
    port = req.url.port
    if port is None:
        port = 80 if req.url.scheme == "http" else 443

    url = "https://1024.day/api/discussions?include=user%2ClastPostedUser%2Ctags%2Ctags.parent%2CfirstPost&sort=-createdAt&page%5Boffset%5D=0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    res = httpx.get(url, headers=headers, verify=False)
    res.raise_for_status()

    fg = feedgen.feed.FeedGenerator()
    fg.id("https://1024.day/?sort=newest")
    fg.title("1024.day 新鲜出炉")
    fg.subtitle("新鲜出炉的帖子")
    fg.author({"name": "qsssssssss", "email": "support@19940731.xyz"})
    fg.link(href="https://1024.day/?sort=newest", rel="alternate")
    fg.logo("https://1024.day/favicon.ico")
    fg.link(href=f"https://{host}:{port}/api/rss/1024.day/newest", rel="self")
    fg.language("zh-CN")
    data = res.json()
    for item in data.get("data", []):
        _id = item["id"]
        payload = item["attributes"]
        payload["id"] = _id
        post = Post.model_construct(**payload)
        entry = fg.add_entry()
        entry.id(post.id)
        entry.title(post.title)
        entry.content(post.subscription or "")
        entry.published(dateparser.parse(post.createdAt))
        entry.link(href=post.shareUrl)

    rss_xml = fg.rss_str(pretty=True)
    return Response(content=rss_xml, media_type="application/xml")


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
        "feed_url": f"{req.url.scheme}://{host}/api/rss/1024.day/newest",
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
        return HTTPException(res.status_code, f"fetch 1024.day error: {res.text}")

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
        _payload["id"] = f"t6-{_payload['id']}"
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
