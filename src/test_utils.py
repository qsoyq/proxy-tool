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


def test_nga_content_html_reformat():
    content_html = "[img]./mon_202508/13/-d1rcQ1ah-attnK1cT3cSp3-og.jpg[/img]<hr>[img]./mon_202508/13/-d1rcQ1ah-attnK1cT3cSp3-og.jpg[/img]"
    assert (
        NgaToolkit.format_content_html(content_html)
        == """<img src="https://img.nga.178.com/attachments/mon_202508/13/-d1rcQ1ah-attnK1cT3cSp3-og.jpg"></img><hr><img src="https://img.nga.178.com/attachments/mon_202508/13/-d1rcQ1ah-attnK1cT3cSp3-og.jpg"></img>"""
    )
