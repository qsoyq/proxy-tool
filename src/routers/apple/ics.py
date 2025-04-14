import re
import logging
import httpx
import dateparser
from fastapi import APIRouter, Query, Path
from fastapi.responses import PlainTextResponse
from datetime import datetime, timedelta
from ics import Calendar, Event
from ics.alarm.display import DisplayAlarm
from schemas.github.issues import GithubIssueState, GithubIssueSort, GithubIssueDirection, GithubIssue


router = APIRouter(tags=["Utils"], prefix="/apple")

logger = logging.getLogger(__file__)


def github_issues_to_calendar(issues: list[GithubIssue]) -> list[Event]:
    events = []
    pattern = re.compile(r"\(@(.*)\)")
    for issue in issues:
        e = Event()
        result = re.search(pattern, issue.title)
        if not result:
            continue
        datetime_str = result.group(1)
        end = dateparser.parse(datetime_str)
        begin = end
        if not begin or not end:
            logger.warning(f"Invalid begin or end: {issue.html_url}")
            continue
        e.begin = begin
        e.end = end
        e.name = issue.title
        e.description = issue.body
        e.url = issue.html_url
        e.uid = str(issue.id)
        events.append(e)
        logger.info(f"{e}")
    return events


@router.get("/ics/calander", summary="Apple日历订阅示例")
def calander():
    tomorrow = datetime.now() + timedelta(days=1)
    c = Calendar()
    e = Event()
    e.name = "My cool event"
    e.description = "A meaningful description"
    e.begin = tomorrow.replace(hour=4, minute=0, second=0, microsecond=0)
    e.end = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
    e.alarms = [DisplayAlarm(timedelta(minutes=-10))]
    c.events.add(e)

    return PlainTextResponse(c.serialize())


@router.get("/ics/github/repos/{owner}/{repo}/issues", summary="Github Repo Issues To Apple Calendar")
async def github_repo_issues(
    token: str = Query(..., description="Github API Token"),
    owner: str = Path(..., description="Github Repo Owner"),
    repo: str = Path(..., description="Github Repo Name"),
    milestone: str | int | None = Query(None),
    assignee: str | None = Query(None),
    type_: str | None = Query(None, alias="type"),
    creator: str | None = Query(None),
    mentioned: str | None = Query(None),
    labels: str | None = Query(None),
    state: GithubIssueState | None = Query(None),
    sort: GithubIssueSort | None = Query(None),
    direction: GithubIssueDirection | None = Query(None),
    per_page: int | None = Query(None, ge=1, le=100),
    page: int | None = Query(None, ge=1),
):
    """
    参数详见文档: https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#list-repository-issues

    Issue 标题必须包含如 `(@2025-04-18T18:00:00+0800)` 表示截止时间的字符串内容, 否则无法解析为日历事件
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    params = {
        "milestone": milestone,
        "assignee": assignee,
        "type": type_,
        "creator": creator,
        "mentioned": mentioned,
        "labels": labels,
        "state": state,
        "sort": sort,
        "direction": direction,
        "per_page": per_page,
        "page": page,
    }

    params = {k: v for k, v in params.items() if v is not None}
    async with httpx.AsyncClient(headers=headers) as client:
        res = await client.get(url, params=params)
        if res.is_error:
            return PlainTextResponse(res.text, status_code=res.status_code)
        issues = res.json()
        if not issues:
            return PlainTextResponse("No related issue found.", status_code=404)
        github_issues = [GithubIssue(**issue) for issue in issues]

    events = github_issues_to_calendar(github_issues)

    c = Calendar()
    for e in events:
        c.events.add(e)
    return PlainTextResponse(c.serialize())
