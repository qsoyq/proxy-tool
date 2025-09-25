import logging
from typing import Any, cast
import httpx
from fastapi import APIRouter, Query, Path, HTTPException, Request
from schemas.github import AuthorSchema
from schemas.github.commits import CommitItemSchema, CommitSchema
from schemas.rss.jsonfeed import JSONFeed, JSONFeedItem
from responses import PrettyJSONResponse
from utils.cache import RandomTTLCache
from asyncache import cached


router = APIRouter(tags=["RSS"], prefix="/rss/github/commits")

logger = logging.getLogger(__file__)


@router.get(
    "/repos/{owner}/{repo}",
    summary="Github Repo Commits RSS",
    response_model=JSONFeed,
    response_class=PrettyJSONResponse,
)
async def commits_list(
    req: Request,
    token: str | None = Query(None, description="Github API Token"),
    owner: str = Path(..., description="Github Repo Owner"),
    repo: str = Path(..., description="Github Repo Name"),
    per_page: int = Query(30, ge=1, le=100),
    page: int = Query(1, ge=1),
):
    """
    参数详见文档: https://docs.github.com/en/rest/commits/commits?apiVersion=2022-11-28
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

    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
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
        commit_list: list[CommitItemSchema] = [CommitItemSchema.model_construct(**x) for x in res.json()]

    for commit in commit_list:
        commit.author = AuthorSchema(**cast(dict, commit.author))
        commit.commit = CommitSchema(**cast(dict, commit.commit))
        assert commit.commit.author
        assert commit.author
        payload: dict[str, Any] = {
            "id": f"github-commits-{owner}-{repo}-{commit.sha}",
            "url": commit.html_url,
            "title": commit.commit.message,
            "content_text": "",
            "date_published": commit.commit.author.date,
            "date_modified": commit.commit.author.date,
            "author": {
                "url": commit.author.html_url,
                "name": commit.author.login,
                "avatar": commit.author.avatar_url,
            },
        }
        items.append(JSONFeedItem(**payload))
    return items
