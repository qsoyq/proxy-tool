import logging
from typing import Any, cast
import httpx
import markdown
from fastapi import APIRouter, Query, Path, HTTPException, Request
from schemas.github.releases import ReleaseSchema, AuthorSchema, AssetSchema
from schemas.rss.jsonfeed import JSONFeed, JSONFeedItem
from responses import PrettyJSONResponse
from utils.cache import RandomTTLCache
from asyncache import cached


router = APIRouter(tags=["RSS"], prefix="/rss/github/releases")

logger = logging.getLogger(__file__)


@router.get(
    "/repos/{owner}/{repo}",
    summary="Github Repo Releases RSS",
    response_model=JSONFeed,
    response_class=PrettyJSONResponse,
)
async def releases_list(
    req: Request,
    token: str | None = Query(None, description="Github API Token"),
    owner: str = Path(..., description="Github Repo Owner"),
    repo: str = Path(..., description="Github Repo Name"),
    per_page: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
):
    """
    参数详见文档: https://docs.github.com/en/rest/releases/releases#list-releases
    """
    host = req.url.hostname
    items: list[JSONFeedItem] = await fetch_feeds(owner, repo, token, per_page, page)
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": f"{owner}/{repo}",
        "description": "",
        "home_page_url": f"https://github.com/{owner}/{repo}",
        "feed_url": f"{req.url.scheme}://{host}{req.url.path}?{req.url.query}",
        "icon": f"https://github.com/{owner}.png",
        "favicon": f"https://github.com/{owner}.png",
        "items": items,
    }

    return feed


@cached(RandomTTLCache(4096, 300))
async def fetch_feeds(owner: str, repo: str, token: str | None, per_page: int, page: int) -> list[JSONFeedItem]:
    items = []

    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    params = {
        "per_page": per_page,
        "page": page,
    }
    async with httpx.AsyncClient(headers=headers) as client:
        res = await client.get(url, params=params)
        if res.is_error:
            raise HTTPException(status_code=res.status_code, detail=res.text)
        releases_list: list[ReleaseSchema] = [ReleaseSchema.model_construct(**x) for x in res.json()]

    for release in releases_list:
        assert release.author
        release.author = AuthorSchema(**cast(dict, release.author))
        payload: dict[str, Any] = {
            "id": f"github-releases-{owner}-{repo}-{release.id}",
            "url": release.html_url,
            "title": release.name,
            "content_text": release.body or "",
            "date_published": release.published_at,
            "date_modified": release.updated_at,
            "author": {
                "url": release.author.html_url,
                "name": release.author.login,
                "avatar": release.author.avatar_url,
            },
            "attachments": [],
        }
        if payload["content_text"]:
            payload["content_html"] = markdown.markdown(payload.pop("content_text"))

        for _asset in release.assets or []:
            asset = AssetSchema(**cast(dict, _asset))
            attachment = {
                "url": asset.browser_download_url,
                "mime_type": asset.content_type,
                "title": asset.name,
                "size_in_bytes": asset.size,
            }
            payload["attachments"].append(attachment)
        items.append(JSONFeedItem(**payload))
    return items
