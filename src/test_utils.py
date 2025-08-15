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
    # img
    content_html = "[img]./mon_202508/13/-d1rcQ1ah-attnK1cT3cSp3-og.jpg[/img]<hr>[img]./mon_202508/13/-d1rcQ1ah-attnK1cT3cSp3-og.jpg[/img]"
    assert (
        NgaToolkit.format_content_html(content_html)
        == """<img src="https://img.nga.178.com/attachments/mon_202508/13/-d1rcQ1ah-attnK1cT3cSp3-og.jpg"></img><hr><img src="https://img.nga.178.com/attachments/mon_202508/13/-d1rcQ1ah-attnK1cT3cSp3-og.jpg"></img>"""
    )

    # b
    content_html = "[b]Example[/b]"
    assert NgaToolkit.format_content_html(content_html) == "<b>Example</b>"

    # url
    content_html = "[url]https://www.baidu.com[/url]"
    assert NgaToolkit.format_content_html(content_html) == '<a href="https://www.baidu.com">https://www.baidu.com</a>'

    # quote
    content_html = """[quote][pid=835413507,44807971,1]Reply[/pid] <b>Post by [uid=61543543]valaroma123[/uid] (2025-08-09 21:20):</b><br/><br/>配料表看上去还行 还有推荐的吗<br/>[/quote]"""
    assert (
        NgaToolkit.format_content_html(content_html)
        == "<blockquote>配料表看上去还行 还有推荐的吗<br/></blockquote><br>"
    )

    content_html = """[quote][pid=796442878,42541816,1]Reply[/pid] <b>Post by [uid=60162862]Z1264[/uid] (2024-11-23 21:22):</b><br/>台山，都斛海鲜街，住宿51期间200+，海鲜品种多便宜[/quote]"""
    assert (
        NgaToolkit.format_content_html(content_html)
        == "<blockquote>台山，都斛海鲜街，住宿51期间200+，海鲜品种多便宜</blockquote><br>"
    )

    # color
    content_html = """[color=red]如果喜欢，尽快保存，拖延一犯，资源不在[/color]"""
    assert NgaToolkit.format_content_html(content_html) == "如果喜欢，尽快保存，拖延一犯，资源不在"

    content_html = """[color=red][size=100%]链接点击折叠<br/><br/>解压不懂怎么搞就看我签名,不显示就点头像进去看就行<br/><br/>如果显示是doro视频，我这改名无用，需要我写的软件(帖内有下载链接)密钥解包后有压缩包，毕竟有些力度不一样[/size]<br/>[/color]"""
    assert (
        NgaToolkit.format_content_html(content_html)
        == "链接点击折叠<br/><br/>解压不懂怎么搞就看我签名,不显示就点头像进去看就行<br/><br/>如果显示是doro视频，我这改名无用，需要我写的软件(帖内有下载链接)密钥解包后有压缩包，毕竟有些力度不一样<br/>"
    )

    # collapse
    content_html = """[collapse=下载链接]测试[/collapse]"""
    assert NgaToolkit.format_content_html(content_html) == "<details><summary>下载链接</summary>测试</details>"

    content_html = """[collapse=下载链接]<br/>[color=red]由于目前的特殊情况，被爆破失效源文件大概率是爆掉的，所以喜欢的话，来不及下载，一定要尽快保存[/color]<br/><br/>密码：我怎能不变态<br/><br/>夸盘下载<br/><br/>链接：[url]https://pan.quark.cn/s/8b4680220c17[/url]<br/>提取码：aSE2<br/>链接：[url]https://pan.quark.cn/s/6a094448783d[/url]<br/>提取码：nxpE<br/><br/><br/><br/>度盘下载<br/><br/>链接: [url]https://pan.baidu.com/s/1Y8J-8mA-8JglgolhvHViNw[/url] 提取码: 575t <br/><br/><br/><br/>专用解包工具(自选网盘下载，只有是doro出击视频才需要这个，其他正常解压)<br/><br/>运行 专用解包工具，在弹窗里选择下载的视频，会自动分包出压缩包，然后再解压压缩包就行，密码照旧<br/><br/>链接: [url]https://pan.baidu.com/s/1JmXs0LGU21VskdunSf84gg[/url] 提取码: rcc7 <br/>链接：[url]https://pan.quark.cn/s/2807a386db46[/url]<br/><br/><br/>[/collapse]"""
    assert (
        NgaToolkit.format_content_html(content_html)
        == """<details><summary>下载链接</summary><br/>由于目前的特殊情况，被爆破失效源文件大概率是爆掉的，所以喜欢的话，来不及下载，一定要尽快保存<br/><br/>密码：我怎能不变态<br/><br/>夸盘下载<br/><br/>链接：<a href="https://pan.quark.cn/s/8b4680220c17">https://pan.quark.cn/s/8b4680220c17</a><br/>提取码：aSE2<br/>链接：<a href="https://pan.quark.cn/s/6a094448783d">https://pan.quark.cn/s/6a094448783d</a><br/>提取码：nxpE<br/><br/><br/><br/>度盘下载<br/><br/>链接: <a href="https://pan.baidu.com/s/1Y8J-8mA-8JglgolhvHViNw">https://pan.baidu.com/s/1Y8J-8mA-8JglgolhvHViNw</a> 提取码: 575t <br/><br/><br/><br/>专用解包工具(自选网盘下载，只有是doro出击视频才需要这个，其他正常解压)<br/><br/>运行 专用解包工具，在弹窗里选择下载的视频，会自动分包出压缩包，然后再解压压缩包就行，密码照旧<br/><br/>链接: <a href="https://pan.baidu.com/s/1JmXs0LGU21VskdunSf84gg">https://pan.baidu.com/s/1JmXs0LGU21VskdunSf84gg</a> 提取码: rcc7 <br/>链接：<a href="https://pan.quark.cn/s/2807a386db46">https://pan.quark.cn/s/2807a386db46</a><br/><br/><br/></details>"""
    )

    content_html = """[collapse]Example[/collapse]"""
    assert (
        NgaToolkit.format_content_html(content_html)
        == """<details><summary>点击显示隐藏的内容</summary>Example</details>"""
    )

    # align
    content_html = """[align=left]需要改后缀名解压，格式ZIP(不是MP4)<br/>统一密码：chuanhuo<br/><br/>由于需要加密分享，解压软件适配一般<br/>电脑(RAR、bandizip)<br/>安卓(RAR、Zarchiver)<br/>解压失败的可以用最下面提供的解压软件[/align]"""
    assert (
        NgaToolkit.format_content_html(content_html)
        == """<span style="text-align:left">需要改后缀名解压，格式ZIP(不是MP4)<br/>统一密码：chuanhuo<br/><br/>由于需要加密分享，解压软件适配一般<br/>电脑(RAR、bandizip)<br/>安卓(RAR、Zarchiver)<br/>解压失败的可以用最下面提供的解压软件</span>"""
    )

    content_html = """[align=right]需要改后缀名解压，格式ZIP(不是MP4)<br/>统一密码：chuanhuo<br/><br/>由于需要加密分享，解压软件适配一般<br/>电脑(RAR、bandizip)<br/>安卓(RAR、Zarchiver)<br/>解压失败的可以用最下面提供的解压软件[/align]"""
    assert (
        NgaToolkit.format_content_html(content_html)
        == """<span style="text-align:right">需要改后缀名解压，格式ZIP(不是MP4)<br/>统一密码：chuanhuo<br/><br/>由于需要加密分享，解压软件适配一般<br/>电脑(RAR、bandizip)<br/>安卓(RAR、Zarchiver)<br/>解压失败的可以用最下面提供的解压软件</span>"""
    )

    content_html = """[align=right]需要改后缀名解压，格式ZIP(不是MP4)<br/>统一密码：chuanhuo<br/><br/>由于需要加密分享，解压软件适配一般<br/>电脑(RAR、bandizip)<br/>安卓(RAR、Zarchiver)<br/>解压失败的可以用最下面提供的解压软件[/align]"""
    assert (
        NgaToolkit.format_content_html(content_html)
        == """<span style="text-align:right">需要改后缀名解压，格式ZIP(不是MP4)<br/>统一密码：chuanhuo<br/><br/>由于需要加密分享，解压软件适配一般<br/>电脑(RAR、bandizip)<br/>安卓(RAR、Zarchiver)<br/>解压失败的可以用最下面提供的解压软件</span>"""
    )

    # emoji
    content_html = "[s:ac:goodjob]"
    assert (
        NgaToolkit.format_content_html(content_html)
        == """<img src="https://img4.nga.178.com/ngabbs/post/smile/ac1.png">"""
    )


@pytest.mark.asyncio
async def test_nga_emoji_replace():
    data = await NgaToolkit.get_smiles()
    smiles = {s.name: s.tag for s in data}
    assert smiles
