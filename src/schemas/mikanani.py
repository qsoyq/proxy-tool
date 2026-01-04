from pydantic import BaseModel, Field


class EnclosureSchema(BaseModel):
    url: str = Field('', alias='@url')
    type_: str = Field('', alias='@type')
    length: str = Field('', alias='@length')


class GUIDSchema(BaseModel):
    text: str = Field('', alias='#text')
    isPermaLink: str = Field('', alias='@isPermaLink')


class TorrentSchema(BaseModel):
    xmlns: str = Field('', alias='@xmlns')
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
    image: str = Field('')
    real_title: str = Field('')


class ChannelSchema(BaseModel):
    title: str
    link: str
    description: str
    item: list[ChannelItemSchema]


class RssSchema(BaseModel):
    version: str = Field(..., alias='@version')
    channel: ChannelSchema


class MikananiResSchema(BaseModel):
    rss: RssSchema


mikanani_bangumi_torrent_success_example = r"""
magnet:?xt=urn:btih:6cbfbda3c0a9abc08cee96d749720c0515c15fe6&tr=http%3a%2f%2ft.nyaatracker.com%2fannounce&tr=http%3a%2f%2ftracker.kamigami.org%3a2710%2fannounce&tr=http%3a%2f%2fshare.camoe.cn%3a8080%2fannounce&tr=http%3a%2f%2fopentracker.acgnx.se%2fannounce&tr=http%3a%2f%2fanidex.moe%3a6969%2fannounce&tr=http%3a%2f%2ft.acg.rip%3a6699%2fannounce&tr=https%3a%2f%2ftr.bangumi.moe%3a9696%2fannounce&tr=udp%3a%2f%2ftr.bangumi.moe%3a6969%2fannounce&tr=http%3a%2f%2fopen.acgtracker.com%3a1096%2fannounce&tr=udp%3a%2f%2ftracker.opentrackr.org%3a1337%2fannounce
magnet:?xt=urn:btih:6241977af98e9175e8147248405d59134358862e&tr=http%3a%2f%2ft.nyaatracker.com%2fannounce&tr=http%3a%2f%2ftracker.kamigami.org%3a2710%2fannounce&tr=http%3a%2f%2fshare.camoe.cn%3a8080%2fannounce&tr=http%3a%2f%2fopentracker.acgnx.se%2fannounce&tr=http%3a%2f%2fanidex.moe%3a6969%2fannounce&tr=http%3a%2f%2ft.acg.rip%3a6699%2fannounce&tr=https%3a%2f%2ftr.bangumi.moe%3a9696%2fannounce&tr=udp%3a%2f%2ftr.bangumi.moe%3a6969%2fannounce&tr=http%3a%2f%2fopen.acgtracker.com%3a1096%2fannounce&tr=udp%3a%2f%2ftracker.opentrackr.org%3a1337%2fannounce
magnet:?xt=urn:btih:c78f6fcccad8d61490336b73c78af0f065198ae2&tr=http%3a%2f%2ft.nyaatracker.com%2fannounce&tr=http%3a%2f%2ftracker.kamigami.org%3a2710%2fannounce&tr=http%3a%2f%2fshare.camoe.cn%3a8080%2fannounce&tr=http%3a%2f%2fopentracker.acgnx.se%2fannounce&tr=http%3a%2f%2fanidex.moe%3a6969%2fannounce&tr=http%3a%2f%2ft.acg.rip%3a6699%2fannounce&tr=https%3a%2f%2ftr.bangumi.moe%3a9696%2fannounce&tr=udp%3a%2f%2ftr.bangumi.moe%3a6969%2fannounce&tr=http%3a%2f%2fopen.acgtracker.com%3a1096%2fannounce&tr=udp%3a%2f%2ftracker.opentrackr.org%3a1337%2fannounce
magnet:?xt=urn:btih:be61f6ed73edc99f64a19a00db6e02708cf3f262&tr=http%3a%2f%2ft.nyaatracker.com%2fannounce&tr=http%3a%2f%2ftracker.kamigami.org%3a2710%2fannounce&tr=http%3a%2f%2fshare.camoe.cn%3a8080%2fannounce&tr=http%3a%2f%2fopentracker.acgnx.se%2fannounce&tr=http%3a%2f%2fanidex.moe%3a6969%2fannounce&tr=http%3a%2f%2ft.acg.rip%3a6699%2fannounce&tr=https%3a%2f%2ftr.bangumi.moe%3a9696%2fannounce&tr=udp%3a%2f%2ftr.bangumi.moe%3a6969%2fannounce&tr=http%3a%2f%2fopen.acgtracker.com%3a1096%2fannounce&tr=udp%3a%2f%2ftracker.opentrackr.org%3a1337%2fannounce
magnet:?xt=urn:btih:819699414862c27397928ca523712e0c39ac6c07&tr=http%3a%2f%2ft.nyaatracker.com%2fannounce&tr=http%3a%2f%2ftracker.kamigami.org%3a2710%2fannounce&tr=http%3a%2f%2fshare.camoe.cn%3a8080%2fannounce&tr=http%3a%2f%2fopentracker.acgnx.se%2fannounce&tr=http%3a%2f%2fanidex.moe%3a6969%2fannounce&tr=http%3a%2f%2ft.acg.rip%3a6699%2fannounce&tr=https%3a%2f%2ftr.bangumi.moe%3a9696%2fannounce&tr=udp%3a%2f%2ftr.bangumi.moe%3a6969%2fannounce&tr=http%3a%2f%2fopen.acgtracker.com%3a1096%2fannounce&tr=udp%3a%2f%2ftracker.opentrackr.org%3a1337%2fannounce
magnet:?xt=urn:btih:99fd9ec63c33646b6ec1156e9f77f906b5cb7bed&tr=http%3a%2f%2ft.nyaatracker.com%2fannounce&tr=http%3a%2f%2ftracker.kamigami.org%3a2710%2fannounce&tr=http%3a%2f%2fshare.camoe.cn%3a8080%2fannounce&tr=http%3a%2f%2fopentracker.acgnx.se%2fannounce&tr=http%3a%2f%2fanidex.moe%3a6969%2fannounce&tr=http%3a%2f%2ft.acg.rip%3a6699%2fannounce&tr=https%3a%2f%2ftr.bangumi.moe%3a9696%2fannounce&tr=udp%3a%2f%2ftr.bangumi.moe%3a6969%2fannounce&tr=http%3a%2f%2fopen.acgtracker.com%3a1096%2fannounce&tr=udp%3a%2f%2ftracker.opentrackr.org%3a1337%2fannounce
magnet:?xt=urn:btih:39c9971cd53eb214a7ace4dec3a14dd0845ce248&tr=http%3a%2f%2ft.nyaatracker.com%2fannounce&tr=http%3a%2f%2ftracker.kamigami.org%3a2710%2fannounce&tr=http%3a%2f%2fshare.camoe.cn%3a8080%2fannounce&tr=http%3a%2f%2fopentracker.acgnx.se%2fannounce&tr=http%3a%2f%2fanidex.moe%3a6969%2fannounce&tr=http%3a%2f%2ft.acg.rip%3a6699%2fannounce&tr=https%3a%2f%2ftr.bangumi.moe%3a9696%2fannounce&tr=udp%3a%2f%2ftr.bangumi.moe%3a6969%2fannounce&tr=http%3a%2f%2fopen.acgtracker.com%3a1096%2fannounce&tr=udp%3a%2f%2ftracker.opentrackr.org%3a1337%2fannounce
magnet:?xt=urn:btih:c35e2a8a93d965f8689473e1bf9b8d61d0a33b4d&tr=http%3a%2f%2ft.nyaatracker.com%2fannounce&tr=http%3a%2f%2ftracker.kamigami.org%3a2710%2fannounce&tr=http%3a%2f%2fshare.camoe.cn%3a8080%2fannounce&tr=http%3a%2f%2fopentracker.acgnx.se%2fannounce&tr=http%3a%2f%2fanidex.moe%3a6969%2fannounce&tr=http%3a%2f%2ft.acg.rip%3a6699%2fannounce&tr=https%3a%2f%2ftr.bangumi.moe%3a9696%2fannounce&tr=udp%3a%2f%2ftr.bangumi.moe%3a6969%2fannounce&tr=http%3a%2f%2fopen.acgtracker.com%3a1096%2fannounce&tr=udp%3a%2f%2ftracker.opentrackr.org%3a1337%2fannounce
"""


mikanani_rss_subscribe_success_example = {
    'rss': {
        '@version': '2.0',
        'channel': {
            'title': 'Mikan Project - 我的番组',
            'link': 'http://mikanani.me/RSS/MyBangumi?token=token',
            'description': 'Mikan Project - 我的番组',
            'item': [
                {
                    'guid': {
                        '@isPermaLink': 'false',
                        '#text': '[不当舔狗制作组] 机动战士高达 GQuuuuuuX - 01V2 [AMZN WebRip 1080p HEVC-10bit E-AC-3][简繁内封字幕]',
                    },
                    'link': 'https://mikanani.me/Home/Episode/f5a6c93027ddd512c55285bb68e2f5d45cf80fb6',
                    'title': '[不当舔狗制作组] 机动战士高达 GQuuuuuuX - 01V2 [AMZN WebRip 1080p HEVC-10bit E-AC-3][简繁内封字幕]',
                    'description': '[不当舔狗制作组] 机动战士高达 GQuuuuuuX - 01V2 [AMZN WebRip 1080p HEVC-10bit E-AC-3][简繁内封字幕][560.7MB]',
                    'torrent': {
                        '@xmlns': 'https://mikanani.me/0.1/',
                        'link': 'https://mikanani.me/Home/Episode/f5a6c93027ddd512c55285bb68e2f5d45cf80fb6',
                        'contentLength': '587936576',
                        'pubDate': '2025-04-15T21:38:00',
                    },
                    'enclosure': {
                        '@type': 'application/x-bittorrent',
                        '@length': '587936576',
                        '@url': 'https://mikanani.me/Download/20250415/f5a6c93027ddd512c55285bb68e2f5d45cf80fb6.torrent',
                    },
                    'image': 'https://mikanani.me/images/Bangumi/202504/e33a7226.jpg?width=400&height=560&format=webp',
                    'real_title': '机动战士高达 GQuuuuuuX - 01V2',
                },
            ],
        },
    }
}


mikanani_rss_subscribe_responses: dict[int | str, dict[str, object]] = {
    200: {
        'description': '200 Successful Response',
        'content': {'application/json': {'example': mikanani_rss_subscribe_success_example}},
    }
}

mikanani_bangumi_torrent_responses: dict[int | str, dict[str, object]] = {
    200: {
        'description': '200 Successful Response',
        'content': {'text/plain': {'example': mikanani_bangumi_torrent_success_example}},
    }
}
