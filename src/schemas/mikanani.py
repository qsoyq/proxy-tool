from pydantic import BaseModel, Field


class EnclosureSchema(BaseModel):
    url: str = Field("", alias="@url")
    type_: str = Field("", alias="@type")
    length: str = Field("", alias="@length")


class GUIDSchema(BaseModel):
    text: str = Field("", alias="#text")
    isPermaLink: str = Field("", alias="@isPermaLink")


class TorrentSchema(BaseModel):
    xmlns: str = Field("", alias="@xmlns")
    link: str
    contentLength: str
    pubDate: str


class ChannelItemSchema(BaseModel):
    guid: GUIDSchema
    title: str
    link: str
    description: str
    torrent: TorrentSchema
    enclosure: EnclosureSchema
    image: str = Field("")
    real_title: str = Field("")


class ChannelSchema(BaseModel):
    title: str
    link: str
    description: str
    item: list[ChannelItemSchema]


class RssSchema(BaseModel):
    version: str = Field(..., alias="@version")
    channel: ChannelSchema


class MikananiResSchema(BaseModel):
    rss: RssSchema


mikanani_rss_subscribe_success_example = {
    "rss": {
        "@version": "2.0",
        "channel": {
            "title": "Mikan Project - 我的番组",
            "link": "http://mikanani.me/RSS/MyBangumi?token=token",
            "description": "Mikan Project - 我的番组",
            "item": [
                {
                    "guid": {
                        "@isPermaLink": "false",
                        "#text": "[不当舔狗制作组] 机动战士高达 GQuuuuuuX - 01V2 [AMZN WebRip 1080p HEVC-10bit E-AC-3][简繁内封字幕]",
                    },
                    "link": "https://mikanani.me/Home/Episode/f5a6c93027ddd512c55285bb68e2f5d45cf80fb6",
                    "title": "[不当舔狗制作组] 机动战士高达 GQuuuuuuX - 01V2 [AMZN WebRip 1080p HEVC-10bit E-AC-3][简繁内封字幕]",
                    "description": "[不当舔狗制作组] 机动战士高达 GQuuuuuuX - 01V2 [AMZN WebRip 1080p HEVC-10bit E-AC-3][简繁内封字幕][560.7MB]",
                    "torrent": {
                        "@xmlns": "https://mikanani.me/0.1/",
                        "link": "https://mikanani.me/Home/Episode/f5a6c93027ddd512c55285bb68e2f5d45cf80fb6",
                        "contentLength": "587936576",
                        "pubDate": "2025-04-15T21:38:00",
                    },
                    "enclosure": {
                        "@type": "application/x-bittorrent",
                        "@length": "587936576",
                        "@url": "https://mikanani.me/Download/20250415/f5a6c93027ddd512c55285bb68e2f5d45cf80fb6.torrent",
                    },
                    "image": "https://mikanani.me/images/Bangumi/202504/e33a7226.jpg?width=400&height=560&format=webp",
                    "real_title": "机动战士高达 GQuuuuuuX - 01V2",
                },
            ],
        },
    }
}


mikanani_rss_subscribe_responses: dict[int | str, dict[str, object]] = {
    200: {
        "description": "200 Successful Response",
        "content": {"application/json": {"example": mikanani_rss_subscribe_success_example}},
    }
}
