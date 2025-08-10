import warnings
import logging
import urllib.parse
import asyncio
import contextvars
from itertools import chain
import dateparser
import httpx
from fastapi import APIRouter, Request, Response, Query
from pydantic import HttpUrl
from bs4 import BeautifulSoup as soup
from bs4 import Tag
import feedgen.feed
from schemas.rss.telegram import TelegramChannalMessage
from responses import PrettyJSONResponse
from schemas.rss.jsonfeed import JSONFeed


URLScheme = contextvars.ContextVar("URLScheme", default=True)

router = APIRouter(tags=["RSS"], prefix="/rss/telegram")

logger = logging.getLogger(__file__)


class TelegramToolkit:
    @staticmethod
    def format_telegram_message_text(tag: Tag) -> str:
        return soup(str(tag).replace("<br/>", "\n"), "lxml").getText()

    @staticmethod
    def generate_img_tag(url, alt_text=""):
        return f'<img src="{url}" alt="{alt_text}">'

    @staticmethod
    async def fetch_telegram_messages(channelName: str) -> httpx.Response | None:
        headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }

        try:
            async with httpx.AsyncClient(headers=headers) as client:
                url = f"https://t.me/s/{channelName}"
                res = await client.get(url)
                res.raise_for_status()
                return res
        except Exception as e:
            logger.warning(f"[Telegarm Channel RSS] get_channel_messages error: {e}")
        return None

    @staticmethod
    def get_head_by_document(document: soup) -> str:
        img_css = "body > header > div > div.tgme_header_info > a.tgme_header_link > i > img"
        head_tag = document.select_one(img_css)
        return str(head_tag.attrs["src"]) if head_tag else ""

    @staticmethod
    def get_author_name_by_document(document: soup) -> str:
        channelInfoHeaderTitle = document.select_one("div[class='tgme_channel_info_header_title'] > span")
        return channelInfoHeaderTitle.text if channelInfoHeaderTitle else ""

    @staticmethod
    def get_text_outer_html_by_widget(widget: Tag) -> str | None:
        textTag = widget.select_one(".js-message_text")
        if textTag:
            return str(textTag)
        return None

    @staticmethod
    def get_title_by_widget(widget: Tag) -> str:
        title = text = ""
        textTag = widget.select_one(".js-message_text")
        if textTag:
            title_tag = widget.select_one(".js-message_text > b")
            if title_tag:
                title = title_tag.get_text()
            msg = widget.select_one(".js-message_text")
            if msg:
                text = TelegramToolkit.format_telegram_message_text(msg)
            if not title and text:
                title = text.split("\n")[0]
        return title

    @staticmethod
    def get_text_content_by_widget(widget: Tag) -> str:
        textTag = widget.select_one(".js-message_text")
        if textTag:
            msg = widget.select_one(".js-message_text")
            if msg:
                text = TelegramToolkit.format_telegram_message_text(msg)
                return text or ""
        return ""

    @staticmethod
    def get_username_by_widget(widget: Tag) -> str:
        return str(widget.attrs["data-post"]).split("/")[0]

    @staticmethod
    def get_msgid_by_widget(widget: Tag) -> str:
        return str(widget.attrs["data-post"]).split("/")[1]

    @staticmethod
    def get_published_by_widget(widget: Tag) -> str:
        footer = widget.select_one("div[class='tgme_widget_message_footer compact js-message_footer']")
        if footer:
            meta = footer.select_one("span[class='tgme_widget_message_meta']")
            if meta:
                t = meta.select_one("time")
                return str(t.attrs["datetime"]) if t else ""
        return ""

    @staticmethod
    def get_photos_by_widget(widget: Tag) -> list[HttpUrl]:
        messagePhotos = widget.select("a.js-message_photo")  # 图片组
        if not messagePhotos:
            messagePhotos = widget.select("a.tgme_widget_message_photo_wrap")  # 单张图片消息
        photoUrls: list[HttpUrl] = []
        for p in messagePhotos:
            if not isinstance(p.attrs["style"], str):
                continue
            backgroundImage = {k: v for k, v in (item.split(":", 1) for item in p.attrs["style"].split(";"))}.get(
                "background-image", None
            )
            if backgroundImage:
                backgroundImage = backgroundImage[5:-2]
                photoUrls.append(HttpUrl(backgroundImage))
        return photoUrls

    @staticmethod
    async def get_channel_messages(channelName: str) -> list[TelegramChannalMessage]:
        """

        通过网页 https://t.me/s/{channelName} 提取信息

        视频内容无法单独拷贝出来在页面上播放

        提取文本标签后, 在外部单独构造图片标签附加到 html 内容上
        """
        res = await TelegramToolkit.fetch_telegram_messages(channelName)
        if not res:
            return []

        messages = []
        document = soup(res.text, "lxml")
        head = TelegramToolkit.get_head_by_document(document)
        authorName = TelegramToolkit.get_author_name_by_document(document)

        tgme_widget_message = document.select("div.tgme_widget_message")
        for widget in tgme_widget_message:
            try:
                title = TelegramToolkit.get_title_by_widget(widget)
                text = TelegramToolkit.get_text_content_by_widget(widget)
                username = TelegramToolkit.get_username_by_widget(widget)
                msgid = TelegramToolkit.get_msgid_by_widget(widget)
                published = TelegramToolkit.get_published_by_widget(widget)
                contentHtml = TelegramToolkit.get_text_outer_html_by_widget(widget)
                photoUrls = TelegramToolkit.get_photos_by_widget(widget)
            except Exception as e:
                logger.warning(f"[TelegramToolkit] get channel message error: {e}\nwidget: {widget}")
                continue
            if contentHtml:
                pass

            msg = TelegramChannalMessage(
                head=head,
                msgid=msgid,
                channelName=channelName,
                username=username,
                title=title,
                text=text,
                updated=published,
                authorName=authorName,
                contentHtml=contentHtml,
                photoUrls=photoUrls,
            )
            messages.append(msg)
        return messages

    @staticmethod
    def make_feed_entry_by_telegram_message(
        fg: feedgen.feed.FeedGenerator, message: TelegramChannalMessage
    ) -> feedgen.feed.FeedEntry:
        warnings.warn(
            "make_feed_entry_by_telegram_message is deprecated and will be removed in future versions.",
            DeprecationWarning,
            stacklevel=2,
        )
        urlscheme = URLScheme.get()
        entry: feedgen.feed.FeedEntry = fg.add_entry()
        entry.id(message.msgid)
        entry.title(message.title)
        entry.content(message.text)
        entry.published(dateparser.parse(message.updated))
        if urlscheme:
            qs = urllib.parse.urlencode({"url": f"tg://resolve?domain={message.username}&post={message.msgid}&single"})
            url = f"https://p.19940731.xyz/api/network/url/redirect?{qs}"
            entry.link(href=url)
        else:
            entry.link(href=f"https://t.me/{message.channelName}/{message.msgid}")
        return entry


@router.get("/channel/v1", summary="Telegram Channel RSS Subscribe", include_in_schema=False)
async def channel(
    req: Request,
    channels: list[str] = Query(..., description="channel name"),
    urlscheme: bool = Query(False, description="是否返回 URLScheme 直接跳转到 App"),
):
    """Telegram Channel RSS Subscribe"""
    try:
        token = URLScheme.set(urlscheme)
        host = req.url.hostname
        fg = feedgen.feed.FeedGenerator()
        fg.id("Telegram Channel RSS Subscribe")
        fg.title("Telegram Channel RSS Subscribe")
        fg.subtitle("Telegram Channel RSS Subscribe")
        fg.author({"name": "qsssssssss", "email": "support@19940731.xyz"})
        fg.link(href="https://docs.19940731.xyz", rel="alternate")
        fg.logo("https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Telegram.png")
        fg.link(href=f"https://{host}/api/rss/telegram/channel", rel="self")
        fg.language("zh-CN")
        tasks = await asyncio.gather(*[TelegramToolkit.get_channel_messages(channelName) for channelName in channels])
        for item in chain(*tasks):
            feed = TelegramToolkit.make_feed_entry_by_telegram_message(fg, item)
            fg.add_entry(feed)
        rss_xml = fg.rss_str(pretty=True)
    except Exception as e:
        raise e
    finally:
        URLScheme.reset(token)
    return Response(content=rss_xml, media_type="application/xml")


@router.get(
    "/channel", summary="Telegram Channel RSS Subscribe", response_model=JSONFeed, response_class=PrettyJSONResponse
)
async def channel_jsonfeed(
    req: Request,
    channels: list[str] = Query(..., description="channel name"),
    urlscheme: bool = Query(False, description="是否返回 URLScheme 直接跳转到 App"),
):
    """Telegram Channel RSS Subscribe"""
    try:
        token = URLScheme.set(urlscheme)
        host = req.url.hostname
        items: list = []
        feed = {
            "version": "https://jsonfeed.org/version/1",
            "title": "Telegram Channel RSS Subscribe",
            "description": "",
            "home_page_url": "https://t.me",
            "feed_url": f"{req.url.scheme}://{host}{req.url.path}?{req.url.query}",
            "icon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Telegram.png",
            "favicon": "https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Telegram.png",
            "items": items,
        }
        icon = None
        tasks = await asyncio.gather(*[TelegramToolkit.get_channel_messages(channelName) for channelName in channels])
        for message in chain(*tasks):
            tags = []
            if message.text:
                tags = [x.strip() for x in message.text.replace("\n", " ").split(" ") if x.startswith("#")]

            payload = {
                "id": f"{message.channelName}-{message.msgid}",
                "title": f"{message.title}",
                "url": f"https://t.me/{message.channelName}/{message.msgid}",
                "date_published": message.updated,
                "content_html": message.contentHtml or "",
                "tags": tags,
                "author": {
                    "avatar": message.head,
                    "name": message.channelName,
                    "url": f"https://t.me/{message.channelName}",
                },
            }
            if message.head and icon is None:
                icon = message.head

            if message.photoUrls:
                payload["image"] = message.photoUrls[0]
                payload["banner_image"] = message.photoUrls[0]

                photosOuterHTML = ""
                for url in message.photoUrls:
                    tag = TelegramToolkit.generate_img_tag(url)
                    photosOuterHTML = f"{photosOuterHTML}{tag}"
                payload["content_html"] = f"{photosOuterHTML}{payload['content_html']}"

            items.append(payload)

        if icon is not None:
            feed["icon"] = icon
            feed["favicon"] = icon

    except Exception as e:
        raise e
    finally:
        URLScheme.reset(token)
    return feed
