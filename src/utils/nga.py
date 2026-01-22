import html
import json
import logging
import re
from datetime import datetime
from functools import cache

import httpx
import js2py
from asyncache import cached
from bs4 import BeautifulSoup as Soup
from cachetools import TTLCache
from fastapi import HTTPException
from pydantic import BaseModel, Field
from schemas.nga.thread import (
    ForumSectionIndex,
    GetForumSectionsRes,
    NGASmile,
    OrderByEnum,
    Thread,
    Threads,
)
from utils.bs4 import select_one_by

logger = logging.getLogger(__name__)


class NgaToolkit:
    class NgaThreadHtml(BaseModel):
        raw: str | None = Field(None)
        authorHead: str | None = Field(None)
        authorName: str | None = Field(None)
        authorUrl: str | None = Field(None)
        content_html: str | None = Field(None)

        def as_author(self) -> dict:
            author = {}
            if self.authorHead:
                author['avatar'] = self.authorHead
            if self.authorName:
                author['name'] = self.authorName
            if self.authorUrl:
                author['url'] = self.authorUrl
            return author

    @staticmethod
    async def get_threads(
        uid: str | None = None,
        cid: str | None = None,
        order_by: OrderByEnum | None = OrderByEnum.lastpostdesc,
        *,
        fid: int | None = None,
        favor: int | None = None,
        if_include_child_node: bool | None = None,
        page: int = 1,
    ) -> Threads:
        url = 'https://bbs.nga.cn/thread.php'
        UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1'
        headers = {'user-agent': UA}
        cookies = {}
        if uid:
            cookies['ngaPassportUid'] = uid
        if cid:
            cookies['ngaPassportCid'] = cid

        params: dict[str, str | int] = {
            '__output': 11,  # 返回 json 格式
            'page': page,
        }

        if fid is not None:
            params['fid'] = fid
        if favor is not None:
            params['favor'] = favor

        if order_by is not None:
            params['order_by'] = str(order_by.value)
        async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
            res = await client.get(url, params=params, cookies=cookies, headers=headers)

        if res.is_error:
            logger.warning(f'[NgaToolkit] get threads error: {res.status_code} {res.text}')
            raise HTTPException(status_code=res.status_code, detail=res.text)

        body = json.loads(res.text)
        t_li = [t for t in body['data'].get('__T', [])]
        for t in t_li:
            if t.get('icon') == 0:
                t['icon'] = None
        threads = Threads(threads=[Thread(**t) for t in t_li])

        if fid and not if_include_child_node:
            threads.threads = [t for t in threads.threads if t.fid == fid]

        sections = await NgaToolkit.get_sections()

        # nga 混用了 fid 和 stid 的概念, 当存在 stid 时, stid 即请求对应的 fid
        sections_dict = {(x.stid or x.fid): x for x in sections.sections}

        for t in threads.threads:
            t.postdateStr = datetime.fromtimestamp(t.postdate).strftime(r'%Y-%m-%d %H:%M:%S')
            t.lastpostStr = datetime.fromtimestamp(t.lastpost).strftime(r'%Y-%m-%d %H:%M:%S')
            t.url = f'https://bbs.nga.cn/read.php?tid={t.tid}'
            t.ios_app_scheme_url = f'nga://opentype=2?tid={t.tid}&'
            t.ios_open_scheme_url = (
                f'https://proxy-tool.19940731.xyz/api/network/url/redirect?url={t.ios_app_scheme_url}'
            )
            section = sections_dict.get(t.fid)
            if section:
                t.fname = section.name
                t.icon = section.icon
        return threads

    @staticmethod
    @cached(TTLCache(1024, 86400))
    async def get_sections() -> GetForumSectionsRes:
        """获取论坛分区信息"""
        sections = []
        url = 'https://img4.nga.178.com/proxy/cache_attach/bbs_index_data.js'
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        data = json.loads(resp.text[33:])
        for section in data['data']['0']['all'].values():
            for item in section['content'].values():
                for detail in item['content'].values():
                    id_ = detail.get('stid') or detail['fid']
                    icon = f'https://img4.nga.178.com/proxy/cache_attach/ficon/{id_}u.png'
                    sections.append(
                        ForumSectionIndex(
                            fid=detail['fid'],
                            name=detail['name'],
                            stid=detail.get('stid'),
                            info=f'{detail.get("info")}',
                            icon=icon,
                        )
                    )
        return GetForumSectionsRes(sections=sections)

    @staticmethod
    @cached(TTLCache(1024, 86400 * 3))
    def get_smiles() -> list[NGASmile]:
        data = []
        with httpx.Client(verify=False) as client:
            injection = r"""
            __NUKE = {
                addCss: function(){}
            }
            __COLOR = {}
            commonui = {}
            __SCRIPTS = {
                asyncLoad: function(){}
            }
            _$ = {}
            __COOKIE = {
                getMiscCookie: function(){}
            }
            __GP = {}
            """
            url = 'https://img4.nga.178.com/common_res/js_bbscode_core.js'
            res = client.get(url)
            if res.is_error:
                logger.warning(f"can't fetch nga smiles: {res.text}")
                raise HTTPException(status_code=res.status_code, detail=res.text)
            js_code = res.text
            js_code = js_code.replace(
                r"""ubbcode.continueCharProc.reg = /[\xb7\x7e\x40\x23\x25\x26\x2a\x2b\x7c\x2d\x3d\x60\x7e\x21\x40\x23\x24\x25\x5e\x26\x2a\x28\x29\x5f\x2b\x7b\x7d\x7c\x3a\x22\x3c\x3e\x3f\x2d\x3d\x5b\x5d\x5c\x3b\x27\x2c\x2e\x2f\uff01\uffe5\u2026\u2026\uff08\uff09\u2014\u2014\uff5b\uff5d\uff1a\u201c\uff1f\u300b\u300a\u3010\u3011\u3001\uff1b\u2018\uff0c\u3002\u3001]{24,}/g""",
                '',
            )
            ctx = js2py.EvalJs()  # type: ignore
            ctx.execute(f'{injection}{js_code}')
            smiles = ctx.ubbcode.smiles.to_dict()
            for category in smiles.keys():
                for code, detail in smiles[category].items():
                    if code == '_______name':
                        continue
                    _category = '' if category == '0' else category
                    name = f'[s:{_category}:{code}]'
                    url = f'https://img4.nga.178.com/ngabbs/post/smile/{detail}'
                    tag = f"""<img src="{url}">"""
                    data.append(NGASmile(name=name, url=url, tag=tag))
            logger.info('get nga smiles done.')
        return data

    @staticmethod
    @cached(TTLCache(4096, 86400))
    async def fetch_thread_detail(url: str, cid: str, uid: str) -> NgaThreadHtml | None:
        cookies = {
            'ngaPassportUid': uid,
            'ngaPassportCid': cid,
        }
        async with httpx.AsyncClient(cookies=cookies, verify=False, follow_redirects=True) as client:
            res = await client.get(url)
            if res.is_error:
                logger.warning(f'[NgaToolkit] fetch_thread_detail error: {res.status_code} {res.text}')
                return None

        document = Soup(res.text, 'lxml')
        head = NgaToolkit.get_author_head_by_document(document)
        name = NgaToolkit.get_author_name_by_document(document)
        authorUrl = NgaToolkit.get_author_url_by_document(document)
        content_html = NgaToolkit.get_content_html_by_document(document)
        if content_html:
            content_html = NgaToolkit.format_content_html(content_html)
        return NgaToolkit.NgaThreadHtml(
            authorHead=head,
            authorName=name,
            authorUrl=authorUrl,
            content_html=content_html,
            raw=res.text,
        )

    @staticmethod
    def format_content_html(content: str) -> str:
        def replace_img_tags(text: str) -> str:
            pattern = r'\[img\]\.(/mon.*?)\[/img\]'
            replaced_text = re.sub(pattern, r'<img src="https://img.nga.178.com/attachments\1"></img>', text)

            pattern = r'\[img\]\./\.(/mon.*?)\[/img\]'
            replaced_text = re.sub(pattern, r'<img src="https://img.nga.178.com/attachments\1"></img>', replaced_text)

            pattern = r'\[img\](http.*?)\[/img\]'
            replaced_text = re.sub(pattern, r'<img src="https://img.nga.178.com/attachments\1"></img>', replaced_text)
            return replaced_text

        def replace_b_tags(text: str) -> str:
            pattern = r'\[b\](.*?)\[/b\]'
            replaced_text = re.sub(pattern, r'<b>\1</b>', text)
            return replaced_text

        def replace_url_tags(text: str) -> str:
            replaced_text = text

            # [《古剑奇谭4》本周公布,知名爆料人再出手,宣布本周公布实机PV,并称是国产单机新的希望,腾讯倾力打造] [url]https://www.bilibili.com/video/BV1iBbtzwEB4/?share_source=copy_web&amp;vd_source=960c9e75740363e0be00644ec66610fe[/url]
            # pattern = r"\[(.+?)\]\s\[url\](.*?)\[/url\]"
            pattern = r'\[(?!url\])(?!/url\])(.*?)\] \[url\](.*?)\[/url\]'
            replaced_text = re.sub(pattern, r'<a href="\2">\1</a>', replaced_text)

            pattern = r'\[url=(.*?)\](.*?)\[/url\]'
            replaced_text = re.sub(pattern, r'<a href="\1">\2</a>', replaced_text)

            pattern = r'\[url\](.*?)\[/url\]'
            replaced_text = re.sub(pattern, r'<a href="\1">\1</a>', replaced_text)
            return replaced_text

        def replace_quote_tags(text: str) -> str:
            pattern = r'\[quote\].*?<b>.*?</b>(<br/>)*(.*?)\[/quote\]'
            replaced_text = re.sub(pattern, r'<blockquote>\2</blockquote><br>', text)

            pattern = r'\[quote\](.*?)\[/quote\]'
            replaced_text = re.sub(pattern, r'<blockquote>\1</blockquote>', replaced_text)
            return replaced_text

        def replace_color_tags(text: str) -> str:
            pattern = r'\[color(.*?)\](.*?)\[/color\]'
            replaced_text = re.sub(pattern, r'\2', text)
            return replaced_text

        def replace_size_tags(text: str) -> str:
            pattern = r'\[size(.*?)\]'
            replaced_text = re.sub(pattern, r'', text)

            pattern = r'\[/size]'
            replaced_text = re.sub(pattern, r'', replaced_text)
            return replaced_text

        def replace_collapse_tags(text: str) -> str:
            pattern = r'\[collapse=(.*?)\](.*?)\[/collapse\]'
            replaced_text = re.sub(pattern, r'<details><summary>\1</summary>\2</details>', text)

            pattern = r'\[collapse\](.*?)\[/collapse\]'
            replaced_text = re.sub(
                pattern, r'<details><summary>点击显示隐藏的内容</summary>\1</details>', replaced_text
            )
            return replaced_text

        def replace_align_tags(text: str) -> str:
            pattern = r'\[align=(.*?)\](.*?)\[/align\]'
            replaced_text = re.sub(pattern, r"""<span style="text-align:\1">\2</span>""", text)
            return replaced_text

        def replace_emoji_tags(text: str) -> str:
            smiles = get_smiles()
            results = re.findall(r'\[s:.*?:.*?\]', text)
            if not results:
                return text
            for code in results:
                tag = smiles.get(code)
                if tag:
                    text = text.replace(code, tag)
            return text

        def replace_del_tags(text: str) -> str:
            pattern = r'\[del\](.*?)\[/del\]'
            replaced_text = re.sub(pattern, r'<del>\1</del>', text)
            return replaced_text

        def replace_video_tags(text: str) -> str:
            pattern = r'\[flash=video\]\.(.*?)\[/flash\]'
            replaced_text = re.sub(pattern, r'<video src="https://img.nga.178.com/attachments\1"></video>', text)
            return replaced_text

        def replace_audio_tags(text: str) -> str:
            pattern = r'\[flash=audio\]\.(.*?)\[/flash\]'
            replaced_text = re.sub(
                pattern,
                r'<audio controls><source src="https://img.nga.178.com/attachments\1" type="audio/mp3" /></audio>',
                text,
            )
            return replaced_text

        def replace_album_tags(text: str) -> str:
            def _replace_album(match) -> str:
                summary = match.group(1)
                content = match.group(2)
                content = re.sub(
                    r'\.(/mon.*?)\.(jpg|png|jpeg)',
                    r'<img src="https://img.nga.178.com/attachments\1.\2"></img>',
                    content,
                )
                text = f"""<details><summary>{summary}</summary>{content}</details>"""
                return text

            pattern = r'\[album=(.*?)\](.*?)\[/album\]'
            replaced_text = re.sub(pattern, _replace_album, text)
            return replaced_text

        @cache
        def get_smiles() -> dict:
            data = NgaToolkit.get_smiles()
            return {s.name: s.tag for s in data}

        if not content:
            return content
        content = html.unescape(content)
        content = replace_emoji_tags(content)
        content = replace_img_tags(content)
        content = replace_b_tags(content)
        content = replace_quote_tags(content)
        content = replace_color_tags(content)
        content = replace_size_tags(content)
        content = replace_collapse_tags(content)
        content = replace_align_tags(content)
        content = replace_del_tags(content)
        content = replace_url_tags(content)
        content = replace_video_tags(content)
        content = replace_audio_tags(content)
        content = replace_album_tags(content)

        return content

    @staticmethod
    def get_author_head_by_document(document: Soup) -> str | None:
        head = document.select_one('table.forumbox.postbox>tbody>tr>td.c1>span>img')
        if head:
            return str(head.attrs['src'])
        return None

    @staticmethod
    def get_author_name_by_document(document: Soup) -> str | None:
        a = document.select_one('table.forumbox.postbox>tbody>tr>td.c1>span>div>a')
        if a:
            return str(a.text)
        return None

    @staticmethod
    def get_author_url_by_document(document: Soup) -> str | None:
        tag = document.select_one('a#postauthor0.author')
        if tag:
            return f"https://bbs.nga.cn/{tag.attrs['href']}"
        return None

    @staticmethod
    def get_content_html_by_document(document: Soup) -> str | None:
        subject = select_one_by(document, 'table>tr>p.postcontent')
        tagComments = [tag.select_one('span.postcontent') for tag in document.select('table>tr')]
        if not tagComments:
            # 好像存在两种情况? 都写上试试
            tagComments = [tag.select_one('span.postcontent') for tag in document.select('table>tbody>tr')]
        comments = [str(x) for x in tagComments if x]
        content_li = []
        if subject:
            content_li.append(str(subject))

        content_li.extend(comments)
        content_html = '<hr>'.join(content_li)
        return content_html
