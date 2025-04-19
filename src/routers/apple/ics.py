import re
import logging
import httpx
import dateparser
import asyncio
from bs4 import BeautifulSoup
from fastapi import APIRouter, Query, Path
from fastapi.responses import PlainTextResponse
from datetime import datetime, timedelta, timezone
from ics import Calendar, Event
from ics.alarm.display import DisplayAlarm
from schemas.github.issues import GithubIssueState, GithubIssueSort, GithubIssueDirection, GithubIssue
from settings import AppSettings


router = APIRouter(tags=["Utils"], prefix="/apple")

logger = logging.getLogger(__file__)

fetch_vlrgg_match_time_semaphore = asyncio.Semaphore(AppSettings().ics_fetch_vlrgg_match_time_semaphore)
vlrgg_match_time_memo: dict[str, int] = {}


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
        logger.debug(f"[github_issues_to_calendar]: {e}")
    return events


def get_cached_vlrgg_match_time(url: str) -> datetime | None:
    global vlrgg_match_time_memo

    cached = vlrgg_match_time_memo.get(url)
    if cached:
        cached_match_datetime = datetime.fromtimestamp(cached).astimezone(timezone.utc)
        now = datetime.now().astimezone(timezone.utc)
        max_datetime = now + timedelta(hours=6)
        min_datetime = now - timedelta(hours=6)
        if min_datetime < cached_match_datetime < max_datetime:
            logger.debug(f"[get_cached_vlrgg_match_time]: skip for {url}")
            return None
        else:
            logger.debug(f"[get_cached_vlrgg_match_time]: cache hit for {url}, {cached}")
            return cached_match_datetime
    logger.debug(f"[get_cached_vlrgg_match_time]: cache miss for {url}")
    return None


async def fetch_vlrgg_event_match_time(url: str) -> tuple[str, datetime | None]:
    cached = get_cached_vlrgg_match_time(url)
    if cached:
        return (url, cached)

    async with fetch_vlrgg_match_time_semaphore:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            document = BeautifulSoup(resp.text, "lxml")
            texts = [x.text.strip() for x in document.select("div[class='moment-tz-convert']")]
            datetimestr = " ".join(texts)
            logger.debug(f"[VLRGG Event Match Time]: {datetimestr} - {url}")
            match_datetime = dateparser.parse(datetimestr)
            if match_datetime:
                vlrgg_match_time_memo[url] = int(match_datetime.timestamp())
            return (url, dateparser.parse(datetimestr))  # type: ignore


async def add_vlrgg_event_march_time(events: list[Event]):
    url_to_match_time = {}
    results = await asyncio.gather(*[fetch_vlrgg_event_match_time(e.url) for e in events if e.url])
    for result in results:
        url, datetime = result
        url_to_match_time[url] = datetime

    for e in events:
        match_datetime = url_to_match_time.get(e.url)
        if match_datetime:
            e.begin = e.end = match_datetime.astimezone(timezone.utc)
        else:
            logger.warning(f"can't parse match time: {e.name} - {e.url}")
        logger.debug(f"[Valorant Matches]: {e.name} - {e.begin} - {e.end}")


async def vlrgg_event_to_calendar(vlrgg_event: str) -> list[Event]:
    events = []
    async with httpx.AsyncClient() as client:
        url = f"https://www.vlr.gg/event/matches/{vlrgg_event}/"
        resp = await client.get(url)
        document = BeautifulSoup(resp.text, "lxml")
        wf_title = document.select_one('h1[class="wf-title"]').text.strip()  # type: ignore
        wf_card_list = document.select('div[class="wf-card"]')
        for wf_card in wf_card_list:
            for item in wf_card.select("a"):
                match_url = f'https://www.vlr.gg{item["href"]}'
                teams = []
                for team in item.select("div[class='match-item-vs-team-name']"):
                    team_text = team.select_one("div[class='text-of']")
                    if team_text:
                        teams.append(team_text.text.strip())

                e = Event()
                e.name = f'{" vs ".join(teams)}'
                e.description = f"{wf_title}"
                e.url = match_url
                events.append(e)
    await add_vlrgg_event_march_time(events)
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
    per_page: int = Query(100, ge=1, le=100),
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
    github_issues = []
    async with httpx.AsyncClient(headers=headers) as client:
        while True:
            res = await client.get(url, params=params)
            if res.is_error:
                return PlainTextResponse(res.text, status_code=res.status_code)
            issues = list(res.json())
            github_issues.extend([GithubIssue(**issue) for issue in issues])
            if len(issues) < per_page:
                break

    events = github_issues_to_calendar(github_issues)

    c = Calendar()
    for e in events:
        c.events.add(e)
    return PlainTextResponse(c.serialize())


@router.get("/ics/vlrgg/event/matches", summary="Valorant 赛事订阅")
async def vlrgg(events: list[str] = Query(..., description="赛事ID")):
    """赛程数据源自: https://www.vlr.gg/events"""
    results = await asyncio.gather(*[vlrgg_event_to_calendar(event) for event in events])
    c = Calendar()
    for result in results:
        c.events |= set(result)
    return PlainTextResponse(c.serialize())
