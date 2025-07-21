import logging
import dateparser
import httpx
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field
import feedgen.feed


router = APIRouter(tags=["Utils"], prefix="/rss/1024.day")

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


@router.get("/newest")
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
        post = Post.construct(**payload)
        entry = fg.add_entry()
        entry.id(post.id)
        entry.title(post.title)
        entry.content(post.subscription or "")
        entry.published(dateparser.parse(post.createdAt))
        entry.link(href=post.shareUrl)

    rss_xml = fg.rss_str(pretty=True)
    return Response(content=rss_xml, media_type="application/xml")
