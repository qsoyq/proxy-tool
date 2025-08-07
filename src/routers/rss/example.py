import logging
import inspect
from fastapi import APIRouter, Response


router = APIRouter(tags=["Utils"], prefix="/rss")

logger = logging.getLogger(__file__)


@router.get("/example", summary="RSS 测试")
def example():
    """测试用"""
    rss_xml = """
        <?xml version='1.0' encoding='UTF-8'?>
        <rss xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
            <channel>
            <title>Example - Title</title>
            <link>https://p.19940731.xyz</link>
            <description>description</description>
            <atom:link href="https://p.19940731.xyz" rel="self"/>
            <docs>http://www.rssboard.org/rss-specification</docs>
            <generator>python-feedgen</generator>
            <image>
                <url>https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/YouTube.png</url>
                <title>Title</title>
                <link>https://p.19940731.xyz</link>
            </image>
            <language>zh-CN</language>
            <lastBuildDate>Thu, 07 Aug 2025 16:51:10 +0000</lastBuildDate>
            <item>
                <title>111</title>
                <link>https://t.me/me888888888888/5484</link>
                <description>
                    ...
                </description>
                <guid isPermaLink="false">111</guid>
                <pubDate>Thu, 07 Aug 2025 06:30: +0000</pubDate>
            </item>
            </channel>
        </rss>
    """

    return Response(content=inspect.cleandoc(rss_xml), media_type="application/xml")
