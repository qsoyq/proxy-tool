import logging
import httpx
import dateparser
import asyncio
from bs4 import BeautifulSoup
from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from datetime import datetime, timedelta, timezone
from ics import Calendar, Event
from settings import AppSettings


router = APIRouter(tags=["Utils"], prefix="/apple/ics/vlrgg")

logger = logging.getLogger(__file__)

fetch_vlrgg_match_time_semaphore = asyncio.Semaphore(AppSettings().ics_fetch_vlrgg_match_time_semaphore)
vlrgg_match_time_memo: dict[str, int] = {}


def get_cached_vlrgg_match_time(url: str) -> datetime | None:
    global vlrgg_match_time_memo

    cached = vlrgg_match_time_memo.get(url)
    if cached:
        cached_match_datetime = datetime.fromtimestamp(cached).astimezone(timezone.utc)
        now = datetime.now().astimezone(timezone.utc)
        max_datetime = now + timedelta(hours=12)
        min_datetime = now - timedelta(hours=3)
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
            tag = document.select_one("div[class='moment-tz-convert']")
            match_datetime = None
            if tag:
                utc_ts = tag.attrs["data-utc-ts"]
                utc_ts = f"{utc_ts} EDT"
                logger.debug(f"[VLRGG Event Match Time]: {utc_ts} - {url}")
                match_datetime = dateparser.parse(utc_ts)
            if match_datetime:
                vlrgg_match_time_memo[url] = int(match_datetime.timestamp())
            return (url, match_datetime)


async def add_vlrgg_event_march_time(events: list[Event]):
    url_to_match_time = {}
    results = await asyncio.gather(*[fetch_vlrgg_event_match_time(e.url) for e in events if e.url])
    for result in results:
        url, datetime = result
        url_to_match_time[url] = datetime

    for e in events:
        match_datetime = url_to_match_time.get(e.url) if e.url else None
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


@router.get("/event/matches", summary="Valorant 赛事订阅")
async def vlrgg(events: list[str] = Query(["2283"], description="赛事ID")):
    """赛程数据源自: https://www.vlr.gg/events"""
    results = await asyncio.gather(*[vlrgg_event_to_calendar(event) for event in events])
    c = Calendar()
    for result in results:
        c.events |= set(result)
    return PlainTextResponse(c.serialize())
