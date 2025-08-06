import logging
import asyncio
from itertools import chain
import dateparser
import httpx
from fastapi import APIRouter, Request, Response, Query
from bs4 import BeautifulSoup as soup
from bs4 import Tag
import feedgen.feed
from schemas.rss.telegram import TelegramChannalMessage


router = APIRouter(tags=["Utils"], prefix="/rss/telegram")

logger = logging.getLogger(__file__)


def format_telegram_message_text(tag: Tag) -> str:
    return soup(str(tag).replace("<br/>", "\n"), "lxml").getText()


async def get_channel_messages(channelName: str) -> list[TelegramChannalMessage]:
    headers = {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    messages = []
    try:
        async with httpx.AsyncClient(headers=headers) as client:
            url = f"https://t.me/s/{channelName}"
            res = await client.get(url)
            res.raise_for_status()
        pass
    except Exception as e:
        logger.warning(f"[Telegarm Channel RSS] get_channel_messages error: {e}")

    document = soup(res.text, "lxml")
    img_css = "body > header > div > div.tgme_header_info > a.tgme_header_link > i > img"
    head_tag = document.select_one(img_css)
    if head_tag:
        head = head_tag.attrs["src"]
    tgme_widget_message = document.select("body > main > div > section > div .tgme_widget_message")
    for widget in tgme_widget_message:
        title = text = ""
        _arr = widget.attrs["data-post"].split("/")  # type: ignore
        username, msgid = _arr[0], _arr[1]
        textTag = widget.select_one(".js-message_text")
        if textTag:
            title_tag = widget.select_one(".js-message_text > b")  # type: ignore
            if title_tag:
                title = title_tag.get_text()
            text = format_telegram_message_text(widget.select_one(".js-message_text"))  # type: ignore
            if not title and text:
                title = text.split("\n")[0]
        updated = (
            widget.select_one("div[class='tgme_widget_message_footer compact js-message_footer']")
            .select_one("span[class='tgme_widget_message_meta']")  # type: ignore
            .select_one("time")  # type: ignore
        ).attrs["datetime"]  # type: ignore
        msg = TelegramChannalMessage(
            head=head, msgid=msgid, channelName=channelName, username=username, title=title, text=text, updated=updated
        )
        messages.append(msg)
    return messages


def make_feed_entry_by_telegram_message(
    fg: feedgen.feed.FeedGenerator, message: TelegramChannalMessage
) -> feedgen.feed.FeedEntry:
    entry: feedgen.feed.FeedEntry = fg.add_entry()
    entry.id(message.msgid)
    entry.title(message.title)
    entry.content(message.text)
    entry.published(dateparser.parse(message.updated))
    entry.link(href=f"https://t.me/{message.channelName}/{message.msgid}")
    return entry


@router.get("/channel", summary="Telegram Channel RSS Subscribe")
async def channel(req: Request, channels: list[str] = Query(..., description="channel name")):
    """Telegram Channel RSS Subscribe"""
    host = req.url.hostname
    fg = feedgen.feed.FeedGenerator()
    fg.id("Telegram Channel RSS Subscribe")
    fg.title("Telegram Channel RSS Subscribe")
    fg.subtitle("Telegram Channel RSS Subscribe")
    fg.author({"name": "qsssssssss", "email": "support@19940731.xyz"})
    fg.link(href="https://docs.19940731.xyz", rel="alternate")
    fg.logo("https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Telegram.png")
    fg.link(href=f"https://{host}/rss/telegram/channel", rel="self")
    fg.language("zh-CN")
    tasks = await asyncio.gather(*[get_channel_messages(channelName) for channelName in channels])
    for item in chain(*tasks):
        feed = make_feed_entry_by_telegram_message(fg, item)
        fg.add_entry(feed)
    rss_xml = fg.rss_str(pretty=True)

    return Response(content=rss_xml, media_type="application/xml")
