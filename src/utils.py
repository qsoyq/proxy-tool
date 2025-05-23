import time
import ssl
import asyncio
import types
from datetime import datetime, timezone
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import NameOID
import textwrap
import json
from functools import reduce, partial
from typing import Callable
import shlex
from dataclasses import dataclass, asdict
from schemas.network.ssl import SSLCertSchema


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
