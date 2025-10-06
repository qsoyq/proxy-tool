import logging
from typing import Any, cast
import httpx
from fastapi import APIRouter, Query, Path, HTTPException, Request
from schemas.github.notifications import NotificationSchema
from schemas.rss.jsonfeed import JSONFeedItem
from utils.cache import RandomTTLCache
from asyncache import cached


router = APIRouter(tags=["RSS"], prefix="/rss/github/notifications")

logger = logging.getLogger(__file__)


@router.get(
    "/user/{token}",
    summary="Github Repo Notifications RSS",
)
async def notifications(
    req: Request,
    token: str = Path(..., description="Github User API Token, Personal access tokens (classic)"),
    all_: bool = Query(False, description="If true, show notifications marked as read.", alias="all"),
    participating: bool = Query(
        False,
        description="If true, only shows notifications in which the user is directly participating or mentioned.",
    ),
    since: str | None = Query(
        None,
        description="Only show results that were last updated after the given time. This is a timestamp in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ.",
    ),
    before: str | None = Query(
        None,
        description="Only show results that were last updated after the given time. This is a timestamp in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ.",
    ),
    per_page: int = Query(50, ge=1, le=50),
    page: int = Query(1, ge=1),
):
    """
    参数详见文档: https://docs.github.com/en/rest/activity/notifications?apiVersion=2022-11-28#list-notifications-for-the-authenticated-user

    This endpoint does not work with GitHub App user access tokens, GitHub App installation access tokens, or fine-grained personal access tokens.
    """
    host = req.url.hostname
    items: list[JSONFeedItem] = await fetch_feeds(token, all_, participating, since, before, per_page, page)
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "Github User Notifications",
        "description": "",
        "home_page_url": "https://github.com/notifications",
        "feed_url": f"{req.url.scheme}://{host}{req.url.path}?{req.url.query}",
        "icon": "https://github.com/favicon.ico",
        "favicon": "https://github.com/favicon.ico",
        "items": items,
    }

    return feed


@cached(RandomTTLCache(4096, 300))
async def fetch_feeds(
    token: str,
    all_: bool,
    participating: bool,
    since: str | None,
    before: str | None,
    per_page: int,
    page: int,
) -> list[JSONFeedItem]:
    items = []

    url = "https://api.github.com/notifications"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    headers["Authorization"] = f"Bearer {token}"

    params = {
        "per_page": per_page,
        "page": page,
        "all": all_,
        "participating": participating,
        "since": since,
        "before": before,
    }
    params = {k: v for k, v in params.items() if v is not None}
    async with httpx.AsyncClient(headers=headers) as client:
        res = await client.get(url, params=params)
        if res.is_error:
            raise HTTPException(status_code=res.status_code, detail=res.text)
        notifications: list[NotificationSchema] = [NotificationSchema(**x) for x in res.json()]

    for notification in notifications:
        url = get_url_by_notification(notification)
        payload: dict[str, Any] = {
            "id": f"github-notifications-{notification.id}",
            "url": url,
            "title": notification.subject.title,
            "content_text": "",
            "date_published": notification.updated_at,
            "date_modified": notification.updated_at,
            "author": {
                "url": notification.repository.owner.html_url,
                "name": notification.repository.owner.login,
                "avatar": notification.repository.owner.avatar_url,
            },
        }
        items.append(JSONFeedItem(**payload))
    return items


def get_url_by_notification(notification: NotificationSchema) -> str:
    match notification.subject.type:
        case "Release":
            _, _, _, _, owner, repo, _, releaseid = notification.subject.url.split("/")
            return f"https://github.com/{owner}/{repo}/releases"
        case "Issue":
            _, _, _, _, owner, repo, _, issueid = notification.subject.url.split("/")
            return f"https://github.com/{owner}/{repo}/issues/{issueid}"
        case "PullRequest":
            _, _, _, _, owner, repo, _, pullid = notification.subject.url.split("/")
            return f"https://github.com/{owner}/{repo}/pull/{pullid}"

    return cast(str, notification.url)
