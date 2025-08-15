import re
import time
import ssl
import asyncio
import types
import textwrap
import json
import shlex
import contextvars
import warnings
import logging
import urllib.parse

from datetime import datetime, timezone
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import NameOID
from functools import reduce, partial, cache
from typing import Callable

from dataclasses import dataclass, asdict


import dateparser
import httpx
import js2py

from fastapi import HTTPException
from pydantic import HttpUrl, BaseModel, Field
from bs4 import BeautifulSoup as Soup, Tag
import feedgen
import feedgen.feed
from asyncache import cached
from cachetools import TTLCache
from schemas.network.ssl import SSLCertSchema
from schemas.nga.thread import OrderByEnum, Threads, Thread, GetForumSectionsRes, ForumSectionIndex, NGASmile
from schemas.rss.telegram import TelegramChannalMessage


logger = logging.getLogger(__file__)


def select_one_by(document: Soup | Tag, selector: str):
    try:
        cur = document
        for query in selector.split(">"):
            tag = cur.select_one(query)
            if tag is None:
                return None
            cur = tag
        return cur
    except AttributeError:
        return None


def optional_chain(obj, keys: str):
    def get_value(obj, key: str):
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key)

    try:
        return reduce(get_value, keys.split("."), obj)
    except (AttributeError, KeyError):
        return None


class CurlParserException(BaseException):
    pass


class ArgumentAlreadyException(CurlParserException):
    pass


class ArgumentValueNotExistsException(CurlParserException):
    pass


@dataclass
class CurlDetail:
    url: str
    body: str | None
    headers: dict
    method: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    def to_stash(self) -> str:
        """生成的http 请求代码参考
        https://raw.githubusercontent.com/qsoyq/shell/main/config/stash/script/loglog.js loglog.HttpClientloglog.HttpClient
        """
        body = self.body or ""
        template = f"""
        let url = '{self.url}'
        let res = await {self.method.lower()}({{ url, body: '{body}', headers: {json.dumps(self.headers)}}})
        if (res.error || res.response.status >= 400) {{
            console.log(`[Error] request error: ${{res.error}}, ${{res.response.status}}, ${{res.data}}`)
        }}
        """
        return textwrap.dedent(template).strip()

    def to_httpx(self) -> str:
        body = self.body or ""
        if self.method.lower() == "get":
            template = f"""
            url = '{self.url}'
            headers = {repr(self.headers)}
            resp = httpx.get(url, headers=headers)
            resp.raise_for_status()
            """
        else:
            template = f"""
            url = '{self.url}'
            headers = {repr(self.headers)}
            content = '{body}'
            resp = httpx.{self.method.lower()}(url, content=content ,headers=headers)
            resp.raise_for_status()
            """
        return textwrap.dedent(template).strip()


@dataclass
class CurlOption:
    alias: list[str]
    cb: Callable


class CurlParser:
    """解析
    兼容以下参数
    -d, --data <data>           HTTP POST data
    -f, --fail                  Fail fast with no output on HTTP errors
    -h, --help <category>       Get help for commands
    -i, --include               Include response headers in output
    -o, --output <file>         Write to file instead of stdout
    -O, --remote-name           Write output to file named as remote file
    -s, --silent                Silent mode
    -T, --upload-file <file>    Transfer local FILE to destination
    -u, --user <user:password>  Server user and password
    -A, --user-agent <name>     Send User-Agent <name> to server
    -v, --verbose               Make the operation more talkative
    -V, --version               Show version number and quit
    """

    def __init__(self, command: str):
        self.index = 0
        self.tokens = shlex.split(command, posix=True)
        self.token_count = len(self.tokens)
        self.method_from_body_flag = False
        self.options: list[CurlOption] = []
        self.add_option("-d", "--data", cb=self.parse_data)
        self.add_option("-H", "--header", cb=self.parse_header)
        self.add_option("-X", cb=self.parse_method)
        skip = [
            ("-f", "--fail"),
            ("-h", "--help"),
            ("-i", "--include"),
        ]
        for alias in skip:
            self.add_option(*alias, cb=self.parse_skip)

        skip = [
            ("-o", "--output"),
            ("-O", "--remote-name"),
        ]
        for alias in skip:
            self.add_option(*alias, cb=partial(self.parse_skip, step=2))

        self.url = ""
        self.method = None
        self.body = None
        self.headers: dict[str, str] = {}

    def add_option(self, *alias: str, cb: Callable):
        self.options.append(CurlOption(alias=list(alias), cb=cb))

    def parse(self) -> CurlDetail:
        while self.index < self.token_count:
            self.parse_option()
        assert self.method
        return CurlDetail(url=self.url, body=self.body, headers=self.headers, method=self.method)

    def parse_option(self):
        token = self.tokens[self.index]
        for option in self.options:
            if token in option.alias:
                option.cb()
                break
            flag = False
            for alias in option.alias:
                if token.startswith(alias):
                    option.cb()
                    flag = True
                    break
            if flag:
                break
        else:
            if token.startswith("http"):
                if self.url:
                    raise ArgumentAlreadyException("url already exists")
                self.url = token
            self.index += 1

    def _must_have_next(self, index: int, token: str, _next: str | None):
        if _next is None:
            raise ArgumentValueNotExistsException()

    def parse_header(self):
        token = self.tokens[self.index]
        if token in ("-H", "--header"):
            if self.index + 1 >= self.token_count:
                raise ArgumentValueNotExistsException("bad header argument")
            pairs = self.tokens[self.index + 1]
            if ":" not in pairs:
                raise ArgumentValueNotExistsException("bad header argument")
            key, value = pairs.split(":", 1)
            self.headers[key.strip()] = value.strip()
            self.index += 2
        else:
            if token.startswith("-H"):
                pairs = token[2:]
            elif token.startswith("--header"):
                pairs = token[8:]
            else:
                raise ArgumentValueNotExistsException("bad header argument")
            if ":" not in pairs:
                raise ArgumentValueNotExistsException("bad header argument")
            key, value = pairs.split(":", 1)
            self.headers[key.strip()] = value.strip()
            self.index += 1

    def parse_data(self):
        token = self.tokens[self.index]
        if token in ("-d", "--data"):
            if self.index + 1 >= self.token_count:
                raise ArgumentValueNotExistsException("bad data argument")
            body = self.tokens[self.index + 1]
            self.body = body
            self.index += 2
        else:
            if token.startswith("-d"):
                body = token[2:]
            elif token.startswith("--data"):
                body = token[6:]
            else:
                raise ArgumentValueNotExistsException("bad data argument")
            self.body = body
            self.index += 1

        if self.method is None:
            self.method_from_body_flag = True
            self.method = "POST"

    def parse_method(self):
        token = self.tokens[self.index]
        if token == "-X":
            if self.index + 1 >= self.token_count:
                raise ArgumentValueNotExistsException("bad method argument")
            method = self.tokens[self.index + 1].upper()
            self.index += 2
        else:
            if token.startswith("-X"):
                method = token[2:]
            else:
                raise ArgumentValueNotExistsException("bad method argument")
            self.index += 1
        if self.method is not None and self.method_from_body_flag is False:
            raise ArgumentValueNotExistsException("bad method argument")
        self.method = method

    def parse_skip(self, step: int = 1):
        self.index += step


class AsyncSSLClientContext:
    def __init__(self, host: str, port: int = 443, verify: bool = False):
        self._host = host
        self._port = port
        self._resolved_ip = None
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self._ssl_ctx = ssl.create_default_context()
        if verify:
            self._ssl_ctx.check_hostname = True
            self._ssl_ctx.verify_mode = ssl.VerifyMode.CERT_REQUIRED
        else:
            self._ssl_ctx.check_hostname = False
            self._ssl_ctx.verify_mode = ssl.VerifyMode.CERT_NONE

        self._ssl_ctx._msg_callback = self.ssl_msg_callbacl  # type: ignore
        self._certificate_buf = b""
        self._cert: x509.Certificate | None = None

    async def __aenter__(self):
        reader, writer = await asyncio.open_connection(self._host, self._port, ssl=self._ssl_ctx)

        self.reader = reader
        self.writer = writer
        transport = writer.transport
        peername = transport.get_extra_info("peername")
        if peername:
            self._resolved_ip = peername[0]
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: types.TracebackType):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

        if exc_val:
            self.exception = (exc_tb, exc_val, exc_tb)
            return False

    async def get_peer_certificate(self) -> SSLCertSchema | None:
        async with self:
            return self.certificate

    def ssl_msg_callbacl(
        self,
        conn: ssl.SSLObject,
        direction: str,
        version: ssl.TLSVersion,
        content_type: ssl._TLSContentType,  # type: ignore
        msg_type: ssl._TLSMessageType,  # type: ignore
        data: bytes,
    ):
        try:
            if content_type == ssl._TLSContentType.HANDSHAKE:  # type: ignore
                # cert_msg_types = (ssl._TLSMessageType.CERTIFICATE, ssl._TLSMessageType.CERTIFICATE_VERIFY)  # type: ignore
                cert_msg_types = (ssl._TLSMessageType.CERTIFICATE,)  # type: ignore
                if msg_type in cert_msg_types:
                    self._certificate_buf += data
                if direction == "read" and msg_type == ssl._TLSMessageType.FINISHED:  # type: ignore
                    self.cert = self.certificate_parse(self._certificate_buf)

        except Exception as exp:
            print(exp)

    def certificate_parse(self, byte_data: bytes) -> x509.Certificate | None:
        cert_data = None
        cert = None

        # Find the start of the DER sequence (0x30) which should be followed by length bytes
        # Looking for 0x30 0x82 which indicates a length > 127 bytes encoded in the next 2 bytes
        der_start_index = byte_data.find(b"\x30\x82")

        if der_start_index != -1:
            # Read the two length bytes after 0x30 0x82
            if der_start_index + 3 < len(byte_data):
                length_bytes = byte_data[der_start_index + 2 : der_start_index + 4]
                der_length = (length_bytes[0] << 8) + length_bytes[1]
                # The total size of the DER structure is 1 (tag 0x30) + 3 (length bytes 0x82 + 2 bytes) + der_length
                total_der_size = 1 + 3 + der_length
                # Ensure the extracted slice is within the bounds of the original data
                if der_start_index + total_der_size <= len(byte_data):
                    cert_data = byte_data[der_start_index : der_start_index + total_der_size]
                    self.certificate = x509.load_der_x509_certificate(cert_data, default_backend())
        return cert

    @property
    def certificate(self) -> SSLCertSchema | None:
        cert = self._cert
        if not cert:
            return None
        subject = cert.subject
        issued_to = subject.rfc4514_string()  # Get the full subject string
        issued_o = (
            subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
            if subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
            else None
        )
        issuer = cert.issuer
        issuer_c = (
            issuer.get_attributes_for_oid(NameOID.COUNTRY_NAME)[0].value
            if issuer.get_attributes_for_oid(NameOID.COUNTRY_NAME)
            else None
        )
        issuer_o = (
            issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
            if issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
            else None
        )
        issuer_ou = (
            issuer.get_attributes_for_oid(NameOID.ORGANIZATIONAL_UNIT_NAME)[0].value
            if issuer.get_attributes_for_oid(NameOID.ORGANIZATIONAL_UNIT_NAME)
            else None
        )
        issuer_cn = (
            issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            if issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
            else None
        )
        cert_sn = str(cert.serial_number)
        cert_sha1 = cert.fingerprint(hashes.SHA1()).hex()
        cert_alg_oid = cert.signature_algorithm_oid
        cert_alg_name = cert.signature_hash_algorithm.name if cert.signature_hash_algorithm else str(cert_alg_oid)
        cert_ver = cert.version.value
        cert_sans = "N/A"
        cert_sans_li = []
        try:
            san_extension = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            for name in san_extension.value.get_values_for_type(x509.DNSName):
                cert_sans_li.append(f"DNS:{name}")
            for name in san_extension.value.get_values_for_type(x509.RFC822Name):
                cert_sans_li.append(f"email:{name}")
            for name in san_extension.value.get_values_for_type(x509.UniformResourceIdentifier):
                cert_sans_li.append(f"URI:{name}")
            for name in san_extension.value.get_values_for_type(x509.IPAddress):  # type: ignore
                cert_sans_li.append(f"IP Address:{name}")
        except x509.ExtensionNotFound:
            cert_sans = "N/A"
        if cert_sans_li:
            cert_sans = "; ".join(cert_sans_li)

        now = datetime.now(tz=timezone.utc)
        current = time.time()

        cert_exp = current > cert.not_valid_after_utc.timestamp()

        # cert_valid: Certificate Validity Period (Not Before and Not After)
        cert_valid_from = cert.not_valid_before_utc
        cert_valid_to = cert.not_valid_after_utc
        from_t = cert_valid_from.timestamp()
        to_t = cert_valid_to.timestamp()
        cert_valid = from_t <= current <= to_t

        validity_days = (cert_valid_to - cert_valid_from).days
        days_left = (cert_valid_to - now).days if cert_valid_to > now else 0
        # Now you can use these variables in your context dictionary
        context = {
            "host": self._host,
            "tcp_port": int(self._port),
            "resolved_ip": self._resolved_ip,
            "issued_to": issued_to,
            "issued_o": issued_o,
            "issuer_c": issuer_c,
            "issuer_o": issuer_o,
            "issuer_ou": issuer_ou,
            "issuer_cn": issuer_cn,
            "cert_sn": cert_sn,
            "cert_sha1": cert_sha1,
            "cert_alg": cert_alg_name,  # Or cert_alg_oid for the OID
            "cert_ver": cert_ver,
            "cert_sans": cert_sans,
            "cert_exp": cert_exp,
            "cert_valid": cert_valid,
            "valid_from": cert_valid_from.strftime("%Y-%m-%d"),
            "valid_till": cert_valid_to.strftime("%Y-%m-%d"),
            "validity_days": validity_days,
            "days_left": days_left,
            "valid_days_to_expire": days_left,
        }
        return SSLCertSchema(**context)

    @certificate.setter
    def certificate(self, cert: x509.Certificate | None):
        self._cert = cert


class NgaToolkit:
    class NgaThreadHtml(BaseModel):
        authorHead: str | None = Field(None)
        authorName: str | None = Field(None)
        authorUrl: str | None = Field(None)
        content_html: str | None = Field(None)

        def as_author(self) -> dict:
            author = {}
            if self.authorHead:
                author["avatar"] = self.authorHead
            if self.authorName:
                author["name"] = self.authorName
            if self.authorUrl:
                author["url"] = self.authorUrl
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
        url = "https://bbs.nga.cn/thread.php"
        UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1"
        headers = {"user-agent": UA}
        cookies = {}
        if uid:
            cookies["ngaPassportUid"] = uid
        if cid:
            cookies["ngaPassportCid"] = cid

        params: dict[str, str | int] = {
            "__output": 11,  # 返回 json 格式
            "page": page,
        }

        if fid is not None:
            params["fid"] = fid
        if favor is not None:
            params["favor"] = favor

        if order_by is not None:
            params["order_by"] = str(order_by.value)
        async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
            res = await client.get(url, params=params, cookies=cookies, headers=headers)

        if res.is_error:
            logger.warning(f"[NgaToolkit] get threads error: {res.status_code} {res.text}")
            raise HTTPException(status_code=res.status_code, detail=res.text)

        body = json.loads(res.text)
        t_li = [t for t in body["data"].get("__T", [])]
        for t in t_li:
            if t.get("icon") == 0:
                t["icon"] = None
        threads = Threads(threads=[Thread(**t) for t in t_li])

        if fid and not if_include_child_node:
            threads.threads = [t for t in threads.threads if t.fid == fid]

        sections = await NgaToolkit.get_sections()

        # nga 混用了 fid 和 stid 的概念, 当存在 stid 时, stid 即请求对应的 fid
        sections_dict = {(x.stid or x.fid): x for x in sections.sections}

        for t in threads.threads:
            t.postdateStr = datetime.fromtimestamp(t.postdate).strftime(r"%Y-%m-%d %H:%M:%S")
            t.lastpostStr = datetime.fromtimestamp(t.lastpost).strftime(r"%Y-%m-%d %H:%M:%S")
            t.url = f"https://bbs.nga.cn/read.php?tid={t.tid}"
            t.ios_app_scheme_url = f"nga://opentype=2?tid={t.tid}&"
            t.ios_open_scheme_url = (
                f"https://proxy-tool.19940731.xyz/api/network/url/redirect?url={t.ios_app_scheme_url}"
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
        url = "https://img4.nga.178.com/proxy/cache_attach/bbs_index_data.js"
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        data = json.loads(resp.text[33:])
        for section in data["data"]["0"]["all"].values():
            for item in section["content"].values():
                for detail in item["content"].values():
                    id_ = detail.get("stid") or detail["fid"]
                    icon = f"https://img4.nga.178.com/proxy/cache_attach/ficon/{id_}u.png"
                    sections.append(
                        ForumSectionIndex(
                            fid=detail["fid"],
                            name=detail["name"],
                            stid=detail.get("stid"),
                            info=f'{detail.get("info")}',
                            icon=icon,
                        )
                    )
        return GetForumSectionsRes(sections=sections)

    @staticmethod
    @cached(TTLCache(1024, 86400))
    async def get_smiles() -> list[NGASmile]:
        data = []
        async with httpx.AsyncClient(verify=False) as client:
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
            url = "https://img4.nga.178.com/common_res/js_bbscode_core.js"
            res = await client.get(url)
            if res.is_error:
                raise HTTPException(status_code=res.status_code, detail=res.text)

            js_code = res.text
            js_code = js_code.replace(
                r"""ubbcode.continueCharProc.reg = /[\xb7\x7e\x40\x23\x25\x26\x2a\x2b\x7c\x2d\x3d\x60\x7e\x21\x40\x23\x24\x25\x5e\x26\x2a\x28\x29\x5f\x2b\x7b\x7d\x7c\x3a\x22\x3c\x3e\x3f\x2d\x3d\x5b\x5d\x5c\x3b\x27\x2c\x2e\x2f\uff01\uffe5\u2026\u2026\uff08\uff09\u2014\u2014\uff5b\uff5d\uff1a\u201c\uff1f\u300b\u300a\u3010\u3011\u3001\uff1b\u2018\uff0c\u3002\u3001]{24,}/g""",
                "",
            )
            ctx = js2py.EvalJs()
            ctx.execute(f"{injection}{js_code}")
            smiles = ctx.ubbcode.smiles.to_dict()
            for category in smiles.keys():
                for code, detail in smiles[category].items():
                    if code == "_______name":
                        continue
                    _category = "" if category == "0" else category
                    name = f"[s:{_category}:{code}]"
                    url = f"https://img4.nga.178.com/ngabbs/post/smile/{detail}"
                    tag = f"""<img src="{url}">"""
                    data.append(NGASmile(name=name, url=url, tag=tag))

        return data

    @staticmethod
    @cached(TTLCache(4096, 86400))
    async def fetch_thread_detail(url: str, cid: str, uid: str) -> NgaThreadHtml | None:
        cookies = {
            "ngaPassportUid": uid,
            "ngaPassportCid": cid,
        }
        async with httpx.AsyncClient(cookies=cookies, verify=False, follow_redirects=True) as client:
            res = await client.get(url)
            if res.is_error:
                logger.warning(f"[NgaToolkit] fetch_thread_detail error: {res.status_code} {res.text}")
                return None

        document = Soup(res.text, "lxml")
        head = NgaToolkit.get_author_head_by_document(document)
        name = NgaToolkit.get_author_name_by_document(document)
        authorUrl = NgaToolkit.get_author_url_by_document(document)
        content_html = NgaToolkit.get_content_html_by_document(document)
        return NgaToolkit.NgaThreadHtml(
            authorHead=head, authorName=name, authorUrl=authorUrl, content_html=content_html
        )

    @staticmethod
    def format_content_html(content: str) -> str:
        def replace_img_tags(text: str) -> str:
            pattern = r"\[img\]\.(.*?)\[/img\]"
            replaced_text = re.sub(pattern, r'<img src="https://img.nga.178.com/attachments\1"></img>', text)
            return replaced_text

        def replace_b_tags(text: str) -> str:
            pattern = r"\[b\](.*?)\[/b\]"
            replaced_text = re.sub(pattern, r"<b>\1</b>", text)
            return replaced_text

        def replace_url_tags(text: str) -> str:
            pattern = r"\[url\](.*?)\[/url\]"
            replaced_text = re.sub(pattern, r'<a href="\1">\1</a>', text)
            return replaced_text

        def replace_quote_tags(text: str) -> str:
            pattern = r"\[quote\].*<b>.*</b>(<br/>)*(.*?)\[/quote\]"
            replaced_text = re.sub(pattern, r"<blockquote>\2</blockquote><br>", text)
            return replaced_text

        def replace_color_tags(text: str) -> str:
            pattern = r"\[color(.*?)\](.*?)\[/color\]"
            replaced_text = re.sub(pattern, r"\2", text)
            return replaced_text

        def replace_size_tags(text: str) -> str:
            pattern = r"\[size(.*?)\](.*?)\[/size\]"
            replaced_text = re.sub(pattern, r"\2", text)
            return replaced_text

        def replace_collapse_tags(text: str) -> str:
            pattern = r"\[collapse=(.*)\](.*?)\[/collapse\]"
            replaced_text = re.sub(pattern, r"<details><summary>\1</summary>\2</details>", text)

            pattern = r"\[collapse\](.*?)\[/collapse\]"
            replaced_text = re.sub(
                pattern, r"<details><summary>点击显示隐藏的内容</summary>\1</details>", replaced_text
            )
            return replaced_text

        def replace_align_tags(text: str) -> str:
            pattern = r"\[align=(.*)\](.*?)\[/align\]"
            replaced_text = re.sub(pattern, r"""<span style="text-align:\1">\2</span>""", text)
            return replaced_text

        def replace_emoji_tags(text: str) -> str:
            smiles = get_smiles()
            results = re.findall(r"\[s:.*?:.*?\]", text)
            if not results:
                return text
            for code in results:
                tag = smiles.get(code)
                if tag:
                    text = text.replace(code, tag)
            return text

        @cache
        def get_smiles() -> dict:
            data = asyncio.run(NgaToolkit.get_smiles())
            return {s.name: s.tag for s in data}

        if not content:
            return content
        content = replace_img_tags(content)
        content = replace_b_tags(content)
        content = replace_url_tags(content)
        content = replace_quote_tags(content)
        content = replace_color_tags(content)
        content = replace_size_tags(content)
        content = replace_collapse_tags(content)
        content = replace_align_tags(content)
        content = replace_emoji_tags(content)
        return content

    @staticmethod
    def get_author_head_by_document(document: Soup) -> str | None:
        head = document.select_one("table.forumbox.postbox>tbody>tr>td.c1>span>img")
        if head:
            return str(head.attrs["src"])
        return None

    @staticmethod
    def get_author_name_by_document(document: Soup) -> str | None:
        a = document.select_one("table.forumbox.postbox>tbody>tr>td.c1>span>div>a")
        if a:
            return str(a.text)
        return None

    @staticmethod
    def get_author_url_by_document(document: Soup) -> str | None:
        tag = document.select_one("a#postauthor0.author")
        if tag:
            return f"https://bbs.nga.cn/{tag.attrs['href']}"
        return None

    @staticmethod
    def get_content_html_by_document(document: Soup) -> str | None:
        subject = select_one_by(document, "table>tr>p.postcontent")
        tagComments = [tag.select_one("span.postcontent") for tag in document.select("table>tr")]
        comments = [str(x) for x in tagComments if x]
        content_li = []
        if subject:
            content_li.append(str(subject))

        content_li.extend(comments)
        content_html = "<hr>".join(content_li)
        if content_html:
            return NgaToolkit.format_content_html(content_html)
        return None


class TelegramToolkit:
    URLScheme = contextvars.ContextVar("URLScheme", default=True)

    @staticmethod
    def format_telegram_message_text(tag: Tag) -> str:
        return Soup(str(tag).replace("<br/>", "\n"), "lxml").getText()

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
    def get_head_by_document(document: Soup) -> str:
        img_css = "body > header > div > div.tgme_header_info > a.tgme_header_link > i > img"
        head_tag = document.select_one(img_css)
        return str(head_tag.attrs["src"]) if head_tag else ""

    @staticmethod
    def get_author_name_by_document(document: Soup) -> str:
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
        title = ""
        textTag = widget.select_one(".js-message_text")
        if textTag:
            title_tag = widget.select_one(".js-message_text > b")
            if title_tag:
                title = title_tag.get_text()
                return title
        tags = TelegramToolkit.get_tags_by_widget(widget)
        if tags:
            return " ".join(tags)

        return ""

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
    def get_tags_by_widget(widget: Tag) -> list[str]:
        text = TelegramToolkit.get_text_content_by_widget(widget)
        tags = []
        if text:
            tags = [x.strip() for x in text.replace("\n", " ").split(" ") if x.startswith("#")]
        return tags

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
        document = Soup(res.text, "lxml")
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
                tags = TelegramToolkit.get_tags_by_widget(widget)
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
                tags=tags,
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
        urlscheme = TelegramToolkit.URLScheme.get()
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
