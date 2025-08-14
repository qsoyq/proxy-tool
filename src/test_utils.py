import os
from utils import AsyncSSLClientContext, NgaToolkit  # type:ignore


import pytest


@pytest.mark.asyncio
async def test_async_ssl_client_context():
    for host in ("www.baidu.com", "www.tencent.com", "www.youtube.com", "www.google.com"):
        client = AsyncSSLClientContext(host, verify=False)
        cert = await client.get_peer_certificate()
        assert cert, cert


@pytest.mark.asyncio
@pytest.mark.nga_delay
async def test_nga_fetch_thread_detail():
    url = "https://bbs.nga.cn/read.php?tid=44834023"
    cid, uid = os.getenv("ngaPassportCid"), os.getenv("ngaPassportUid")
    assert cid and uid, "env ngaPassportCid or ngaPassportUid not exists"
    res = await NgaToolkit.fetch_thread_detail(url, cid, uid)
    assert res
    assert res.authorUrl
    assert res.content_html


def test_nga_content_html_format():
    content_html = "[img]./mon_202508/13/-d1rcQ1ah-attnK1cT3cSp3-og.jpg[/img]<hr>[img]./mon_202508/13/-d1rcQ1ah-attnK1cT3cSp3-og.jpg[/img]"
    assert (
        NgaToolkit.format_content_html(content_html)
        == """<img src="https://img.nga.178.com/attachments/mon_202508/13/-d1rcQ1ah-attnK1cT3cSp3-og.jpg"></img><hr><img src="https://img.nga.178.com/attachments/mon_202508/13/-d1rcQ1ah-attnK1cT3cSp3-og.jpg"></img>"""
    )

    content_html = "[b]Example[/b]"
    assert NgaToolkit.format_content_html(content_html) == "<b>Example</b>"

    content_html = "[url]https://www.baidu.com[/url]"
    assert NgaToolkit.format_content_html(content_html) == '<a href="https://www.baidu.com">https://www.baidu.com</a>'

    content_html = """[quote][pid=835413507,44807971,1]Reply[/pid] <b>Post by [uid=61543543]valaroma123[/uid] (2025-08-09 21:20):</b><br/><br/>配料表看上去还行 还有推荐的吗<br/>[/quote]"""
    assert (
        NgaToolkit.format_content_html(content_html)
        == "<blockquote><br/><br/>配料表看上去还行 还有推荐的吗<br/></blockquote><br>"
    )

    content_html = """[quote][pid=796442878,42541816,1]Reply[/pid] <b>Post by [uid=60162862]Z1264[/uid] (2024-11-23 21:22):</b><br/>台山，都斛海鲜街，住宿51期间200+，海鲜品种多便宜[/quote]"""
    assert (
        NgaToolkit.format_content_html(content_html)
        == "<blockquote><br/>台山，都斛海鲜街，住宿51期间200+，海鲜品种多便宜</blockquote><br>"
    )
