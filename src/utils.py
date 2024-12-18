import textwrap
import json
from functools import reduce, partial
from typing import Callable
import shlex
from dataclasses import dataclass, asdict


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
        let res = await {self.method.lower()}({{ url, body: '{body}', headers: {json.dumps(self.headers)})
        if (res.error || res.response.status >= 400) {{
            console.log(`[Error] request error: ${{res.error}}, ${{res.response.status}}, ${{res.data}}`)
        }}
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


if __name__ == "__main__":
    cmd = """
    curl -X POST "https://sss-web.tastientech.com/api/sign/member/signV2" \
    -H "Host: sss-web.tastientech.com" \
    -H"Referer: https://servicewechat.com/wx557473f23153a429/378/page-frame.html" \
    -H"Accept-Encoding: gzip,compress,br,deflate" \
    -H"Content-Length: 70" \
    -H"User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.54(0x18003622) NetType/WIFI Language/zh_CN" \
    -H"Version: 3.2.3" \
    -H"Channel: 1" \
    -H"Content-Type: application/json" \
    -H"Connection: keep-alive" \
    -d'{"activityId":54,"memberName":"xxx","memberPhone":"xxx"}'
    """.strip()
    detail = CurlParser(cmd).parse()

    from pprint import pprint
    import os

    terminal_size = os.get_terminal_size().columns
    pprint(cmd)
    print("=" * terminal_size)
    pprint(detail)
    print("=" * terminal_size)
    print(detail.to_json())
    print("=" * terminal_size)
    print(detail.to_stash())
    print("=" * terminal_size)
