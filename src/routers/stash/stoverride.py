import re
import uuid
import json
import yaml
import inspect
import logging
import urllib.parse
from typing import Any, cast

import httpx
from fastapi import APIRouter, Query, HTTPException, Path
from fastapi.responses import PlainTextResponse
from cachetools import TTLCache
from asyncache import cached

from schemas.adapter import HttpUrl, KeyValuePairStr
from schemas.github.releases import ReleaseSchema
from schemas.loon import LoonArgument
from utils.stash.dns import NameserverPolicyGeositeOverride
from utils.stash.ruleset import RulesetGeositeOverride

router = APIRouter(tags=["Stash"], prefix="/stash/stoverride")


logger = logging.getLogger(__file__)


def rewrite_loon_argument(
    argument: str, loon_arguments: dict[str, LoonArgument], overrideScriptArguments: dict | None
) -> str | None:
    """将 Loon 脚本参数重写为 Stash 可用的脚本参数，填充 Argument 默认值"""
    if overrideScriptArguments is None:
        overrideScriptArguments = {}

    if not argument:
        return ""

    fields = re.findall(r"\{([^}]+)\}", argument)
    body = {}
    for field in fields:
        value = overrideScriptArguments.get(field) or loon_arguments[field].default
        if value == "true":
            value = True
        if value == "false":
            value = False
        body[field] = value
    return json.dumps(body, ensure_ascii=False)


@cached(TTLCache(32, 600))
async def get_jq_path_content(url: str, user_agent: str) -> str:
    async with httpx.AsyncClient(headers={"User-Agent": user_agent}, verify=False) as client:
        resp = await client.get(url)
        if resp.is_error:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        text = resp.text

    lines = [line for line in text.splitlines() if not line.strip().startswith("#")]
    return re.sub(r"\s+", " ", " ".join(lines))


def kv_pair_parse(content: str) -> dict:
    data = {}
    key = ""
    index = 0
    stop = len(content)
    while index < stop:
        char = content[index]
        if char == " ":
            index += 1
            continue

        # get key name
        if char == "=":
            index += 1

            # parse value
            prefix: list[str] = []
            value = ""
            while index < stop:
                char = content[index]
                if char == "," and len(prefix) == 0:
                    index += 1
                    break

                value += char
                if key.lower() == "argument":
                    if char in "[(":
                        prefix.append(char)
                        index += 1
                        continue

                    if char == ")":
                        if not prefix or prefix[-1] != "(":
                            raise ValueError(f"bad character at index of: {index}\ncontent:{content}")
                        prefix.pop()
                        index += 1
                        continue

                    if char == "]":
                        if not prefix or prefix[-1] != "[":
                            raise ValueError(f"bad character at index of: {index}\ncontent:{content}")
                        prefix.pop()
                        index += 1
                        continue

                index += 1

            if prefix:
                raise ValueError(f"invalid value: {key} - {value} - {prefix}")

            data[key] = value
            key = ""
        else:
            key += char
            index += 1

    return data


@cached(TTLCache(32, 86400))
async def get_weather_kit_tag_name(owner: str, repo: str) -> str:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    params = {
        "per_page": 5,
        "page": 1,
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        res = await client.get(url, params=params)
        if res.is_error:
            raise HTTPException(status_code=res.status_code, detail=res.text)
        releases_list: list[ReleaseSchema] = [ReleaseSchema.model_construct(**x) for x in res.json()]
        if not releases_list:
            raise HTTPException(status_code=404, detail="release not found")
        return cast(str, releases_list[0].tag_name)


@cached(TTLCache(32, 3600))
async def get_weather_kit_override_content(owner: str, repo: str, tag_name: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        url = f"https://github.com/NSRingo/WeatherKit/releases/download/{tag_name}/iRingo.WeatherKit.stoverride"
        res = await client.get(url)
        if res.is_error:
            raise HTTPException(status_code=res.status_code, detail=res.text)
        return res.text


@router.get("/rules/random", summary="stash随机规则覆写生成")
def rules_random(name: str = Query("name"), category: str = Query("category"), size: int = Query(100)):
    rules = [f"DOMAIN,{uuid.uuid4().hex}.com,DIRECT" for x in range(size)]
    data = {"name": name, "category": category, "rules": rules}
    res = yaml.safe_dump(data)
    return PlainTextResponse(
        res, headers={"Content-Disposition": "inline"}, media_type="application/yaml;charset=utf-8"
    )


@router.get("/override", summary="Stash覆写修改")
def override(
    url: HttpUrl = Query(..., description="覆写文件订阅地址"),
    name: str | None = Query(None),
    desc: str | None = Query(None),
    category: str | None = Query(None, description="分类名称"),
    icon: str | None = Query(None),
):
    """覆盖覆写文件
    \f
    使用 yaml 进行解析， 无法保留注释
    """
    logger.debug(f"url: {url}")
    res = httpx.get(str(url), follow_redirects=True)
    res.raise_for_status()
    dom = yaml.safe_load(res.content)
    dom["category"] = category
    if name is not None:
        dom["name"] = name
    if desc is not None:
        dom["desc"] = desc
    if category is not None:
        dom["category"] = category
    if icon is not None:
        dom["icon"] = icon
    content = yaml.safe_dump(dom, allow_unicode=True)
    return PlainTextResponse(content=content, media_type="application/yaml;charset=utf-8")


@router.get("/override/v2", summary="Stash覆写修改V2")
def override_v2(
    url: HttpUrl = Query(..., description="覆写文件订阅地址"),
    name: str | None = Query(None),
    desc: str | None = Query(None),
    category: str | None = Query(None, description="分类名称"),
    icon: str | None = Query(None),
):
    """保留注释行， 仅保留整行的注释， 不支持保留同行文本内容后的注释
    \f
    按行分析文件， 保留未匹配的文本
    不按照 yaml 解析
    """

    logger.debug(f"url: {url}")
    res = httpx.get(str(url), follow_redirects=True)
    res.raise_for_status()
    lines = []
    for line in res.text.split("\n"):
        if line.strip().startswith("#"):
            lines.append(line)
            continue
        text = line.strip()
        if text.startswith("name") and name is not None:
            line = f"name: {name}"
            name = None
        if text.startswith("desc") and desc is not None:
            line = f"desc: {desc}"
            desc = None
        if text.startswith("category") and category is not None:
            line = f"category: {category}"
            category = None
        if text.startswith("icon") and icon is not None:
            line = f"icon: {icon}"
            icon = None
        lines.append(line)
    if name is not None:
        lines.insert(0, f"name: {name}")
    if desc is not None:
        lines.insert(0, f"desc: {desc}")
    if category is not None:
        lines.insert(0, f"category: {category}")
    if icon is not None:
        lines.insert(0, f"icon: {icon}")
    content = "\n".join(lines)
    return PlainTextResponse(content=content, media_type="application/yaml;charset=utf-8")


@router.get("/tiles/oil", summary="Stash油价磁贴")
def oil(provname: str = Query(..., description="省份名")):
    """
    provname=后面填写所在省份名，如不填写 默认江苏油价。provname的值不带"省"字 范例：provname=江苏，provname=上海，provname=广东。
    """
    payload = """
    name: 油价
    desc: 复制本内容到自己的库 在provname=后面填写所在省份名，如不填写 默认江苏油价。provname的值不带"省"字 范例：provname=江苏，provname=上海，provname=广东。此脚本使用的公开apikey ，建议自行申请apikey 然后自行修改脚本内的apikey
    tiles:
    - name: {provname}-youjia
      icon: 'car'
      backgroundColor: '#c932a9'
      argument: 'provname={provname}'
    script-providers:
        {provname}-youjia:
            url: https://raw.githubusercontent.com/deezertidal/Surge_Module/master/files/oil.js
    """
    return PlainTextResponse(
        inspect.cleandoc(payload.format(provname=provname)), media_type="application/yaml;charset=utf-8"
    )


@router.get("/tiles/github/rate-limit", summary="GitHub访问429限制")
def github_rate_limit():
    """绕过针对 CN 的 `You have triggered a rate limit` 限制"""

    content = """
    name: Github Rate Limit
    desc: |-
        绕过针对 CN 的 `You have triggered a rate limit` 限制
    category: enhance
    icon: https://raw.githubusercontent.com/qsoyq/icons/main/assets/icon/github.png
    http:
        mitm:
            - "gist.githubusercontent.com"
            - "raw.githubusercontent.com"
            - "avatars.githubusercontent.com"
        header-rewrite:
            - https://(avatars|gist|raw).githubusercontent.com request-replace Accept-Language en-us
    """
    return PlainTextResponse(inspect.cleandoc(content), media_type="application/yaml;charset=utf-8")


@router.get("/headers", summary="Header调试覆写")
def http_header_override(
    name: str = Query("http-header"),
    mitm: str = Query(..., description="中间人攻击域名"),
    match: str = Query(..., description="匹配的 URL"),
    headers: list[str] = Query([], description="需要抓包的Header"),
    cookies: list[str] = Query([], description="需要抓包的Cookie"),
):
    """输出 Header 抓包覆写"""
    argument = json.dumps({"headers": headers, "cookies": cookies})
    content = f"""
    name: {name}
    desc: |-
    category: debug
    icon: https://raw.githubusercontent.com/qsoyq/shell/main/assets/icon/debug.png

    http:
        mitm:
            - "{mitm}"
        script:
            -   match: {match}
                name: {name}
                type: request
                require-body: false
                timeout: 10
                argument: |-
                    {argument}
                binary-mode: false
                debug: true

    script-providers:
        {name}:
            url: https://raw.githubusercontent.com/qsoyq/stash/main/script/debug/http-header.js
            interval: 86400
    """
    r_headers = {
        "Content-Disposition": f"inline;filename*=UTF-8''{urllib.parse.quote(name)}.stoverride",
    }
    return PlainTextResponse(inspect.cleandoc(content), headers=r_headers)


@router.get("/NSRingo/WeatherKit", summary="NSRingo/WeatherKit 最新覆写")
async def weather_kit():
    owner, repo = "NSRingo", "WeatherKit"
    tag_name = await get_weather_kit_tag_name(owner, repo)
    content = await get_weather_kit_override_content(owner, repo, tag_name)
    headers = {
        "Content-Disposition": "inline",
    }
    return PlainTextResponse(content, media_type="application/x-yaml;charset=utf-8", headers=headers)


@router.get("/loon", summary="转写 Loon 插件到 Stash 覆写")
async def loon(
    url: HttpUrl = Query(..., description="Loon 插件地址"),
    user_agent: str = Query("StashCore/3.1.0 Stash/3.1.0 Clash/1.11.0"),
    name: str | None = Query(None, description="强制覆盖 name"),
    desc: str | None = Query(None, description="强制覆盖 desc"),
    category: str | None = Query(None, description="强制覆盖 category"),
    icon: str | None = Query(None, description="强制覆盖 icon"),
    scriptArguments: list[KeyValuePairStr] = Query(
        [], description="强制覆写脚本参数", examples=["debug=ture", "text=loon"]
    ),
):
    """
    Argument
    https://nsloon.app/docs/Plugin/


    不支持的内容
    - Rewrite
        - Mock
    - Script
        - generic
        - cron
    """
    overrideScriptArguments = {k: v for item in scriptArguments for k, v in [item.split("=", 1)]}

    async with httpx.AsyncClient(headers={"User-Agent": user_agent}, verify=False) as client:
        resp = await client.get(url)
        if resp.is_error:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    override: dict[str, Any] = {}
    section = None
    mitms: list[str] = []
    rules: list[str] = []
    url_rewrites: list[str] = []
    body_rewrites: list[str] = []
    header_rewrites: list[str] = []
    scripts: list[dict] = []
    script_providers = {}
    arguments: dict[str, LoonArgument] = {}
    _payload: dict[str, Any] = {}

    for line in resp.text.splitlines():
        line = line.strip()
        if line.startswith("#!"):
            k, v = line[2:].split("=")
            override[k.strip()] = v.strip()
            continue

    if name is not None:
        override["name"] = name

    if category is not None:
        override["category"] = category

    if icon is not None:
        override["icon"] = icon

    if desc is not None:
        override["desc"] = desc

    for line in resp.text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("#"):
            continue

        matched = re.match(r"^\[(.*)?\]", line)
        if matched:
            section = matched.group(1)
            continue

        if section is None:
            continue

        section = section.lower()
        match section:
            # 优先处理 Argument, 便于后续 Script 填充参数
            case "argument":
                name = None
                result: dict[str, Any] = {}
                for part in line.split(","):
                    part = part.strip().strip('"')
                    if "=" in part:
                        key, value = part.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        if name is None and key not in ("tag", "desc"):
                            name = key.strip()
                        result[key] = value
                    else:
                        result.setdefault("_values", []).append(part)

                assert name, (line, result)
                _payload = {
                    "name": name,
                    "type": result[name],
                    "desc": result.get("desc", ""),
                    "tag": result.get("tag", ""),
                    "default": result["_values"][0],
                    "values": result["_values"],
                }

                arguments[name] = LoonArgument(**_payload)

    logger.debug(f"[loon] arguments: {arguments}")

    for line in resp.text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("#"):
            continue
        matched = re.match(r"^\[(.*)?\]", line)
        if matched:
            section = matched.group(1)
            continue

        if section is None:
            continue

        section = section.lower()
        # Mock
        if "mock-request-body" in line or "mock-response-body" in line:
            logger.debug(f"skip by mock: {line}")
            continue

        match section:
            case "mitm":
                if line.startswith("hostname"):
                    for item in line.split("=", 1)[1].split(","):
                        mitms.append(item.strip())
            case "rule":
                content = line.replace(" ", "")
                if len(content.split(",")) <= 2:
                    logger.warning(f"[Loon Rules]invalid rule: {line}")
                else:
                    rules.append(content)
            case "rewrite":
                # URL 类型复写
                # https://nsloon.app/docs/Rewrite/#url-%E7%B1%BB%E5%9E%8B%E5%A4%8D%E5%86%99
                matched = re.match(r"(.*?http.*?) header (.*?http.*)", line)
                if matched:
                    p1, p2 = matched.groups()
                    url_rewrites.append(f"{p1} {p2} transparent")
                    continue

                # redirect
                matched = re.match(r"(.*?http.*?) (\d{3}) (.*?http.*)", line)
                if matched:
                    p1, p2, p3 = matched.groups()
                    url_rewrites.append(f"{p1} {p3} {p2}")
                    continue

                # reject
                matched = re.match(r"(.*?http.*?) (reject.*)", line)
                if matched:
                    p1, p2 = matched.groups()
                    p2.replace("-", "_").replace(" ", "").strip()
                    url_rewrites.append(f"{p1} - {p2}")
                    continue

                # request header
                matched = re.match(
                    r"(.*?http.*?) (header-add|header-del|header-replace|header-replace-regex) (.*)", line
                )
                if matched:
                    p1, p2, p3 = matched.groups()
                    p2.replace("header", "request")
                    header_rewrites.append(f"{p1} {p2} {p3}")
                    continue

                # response header
                matched = re.match(
                    r"(.*?http.*?) (response-header-add|response-header-del|response-header-replace|response-header-replace-regex) (.*)",
                    line,
                )
                if matched:
                    p1, p2, p3 = matched.groups()
                    p2.replace("header", "")
                    header_rewrites.append(f"{p1} {p2} {p3}")
                    continue

                # request body
                matched = re.match(
                    r"(.*?http.*?) (request-body-replace-regex|request-body-json-add|request-body-json-replace|request-body-json-del|request-body-json-jq) (.*)",
                    line,
                )
                if matched:
                    url, rewrite_type, content = matched.groups()
                    rewrite_type = rewrite_type.replace("request-body", "request").replace("json-jq", "jq")
                    if rewrite_type == "request-jq":
                        jq_path_pattern = r'jq-path="(http.*)"'
                        jq_path_matched = re.match(jq_path_pattern, content)
                        if jq_path_matched:
                            url = jq_path_matched.group(1)
                            content = await get_jq_path_content(url, user_agent)

                        content = content.strip("'")
                    body_rewrites.append(f"{url} {rewrite_type} {content}")
                    continue

                # response body
                matched = re.match(
                    r"(.*?http.*?) (response-body-replace-regex|response-body-json-add|response-body-json-replace|response-body-json-del|response-body-json-jq) (.*)",
                    line,
                )
                if matched:
                    url, rewrite_type, content = matched.groups()
                    rewrite_type = rewrite_type.replace("response-body", "response").replace("json-jq", "jq")

                    if rewrite_type == "response-jq":
                        jq_path_pattern = r'jq-path="(http.*)"'
                        jq_path_matched = re.match(jq_path_pattern, content)
                        if jq_path_matched:
                            url = jq_path_matched.group(1)
                            content = await get_jq_path_content(url, user_agent)

                        content = content.strip("'")

                    body_rewrites.append(f"{url} {rewrite_type} {content}")
                    continue

                # header ?
                matched = re.match(r"(.*?http.*?) (header) (.*)", line)
                if matched:
                    logger.warning(f"[Bad Header Rewrite] {line}")
                    continue

                # redirect ?
                matched = re.match(r"(.*?http.*?) (.*?) (\d{3})", line)
                if matched:
                    logger.warning(f"[Bad Redirect Rewrite] {line}")
                    continue

                logger.warning(f"[NotImplementedError] {line}")
                raise NotImplementedError(line)

            case "script":
                matched = re.match(r"(cron) (.*)", line)

                if matched:
                    # TODO: 实现 cron 脚本转换
                    logger.debug("skip because of cron script")
                    continue

                matched = re.match(r"(generic) (.*)", line)
                if matched:
                    logger.debug("skip because of generic script")
                    continue

                matched = re.match(r"(http-request|http-response) (.*?http.*?) (.*)", line)
                if not matched:
                    raise ValueError(f"invalid script line: {line}")

                type_, match_, p3 = matched.groups()
                type_ = type_.replace("http-", "")
                p3 = cast(str, p3)

                # bad case
                if match_ == r"^https:\/\/j1\.pupuapi\.com\/client\/a朴朴超市,":
                    continue
                try:
                    kwargs = kv_pair_parse(p3)
                except Exception as e:
                    logger.error(f"[Loon Script] get kwargs by script\n{match_}\n{p3}\n{kwargs}\n{line}")
                    raise e

                try:
                    _payload = {
                        "match": match_,
                        "name": kwargs.pop("tag", uuid.uuid4().hex),
                        "type": type_,
                        "require-body": kwargs.pop("requires-body", "false").strip() == "true",
                        "argument": rewrite_loon_argument(
                            kwargs.pop("argument", ""), arguments, overrideScriptArguments
                        ),
                        "binary-mode": kwargs.pop("binary-body-mode", "false").strip() == "true",
                        "timeout": int(kwargs.pop("timeout", 20)),
                    }
                    scripts.append(_payload)
                    _script = {
                        "url": kwargs.pop("script-path"),
                        "interval": 86400,
                    }
                    script_providers[_payload["name"]] = _script
                except Exception as e:
                    logger.warning(f"[Loon Script] add script failed: {e}\n{match_}\n{type_}\n{p3}")
                    raise e
            case "argument":
                ...
            case _:
                logger.warning(f"[Loon] Unkown section: {section}")

    if mitms:
        override.setdefault("http", {})
        override["http"]["mitm"] = mitms
    if rules:
        rules = [x for x in rules if x]
        override["rules"] = rules
    if url_rewrites:
        override.setdefault("http", {})
        override["http"]["url-rewrite"] = url_rewrites
    if body_rewrites:
        override.setdefault("http", {})
        override["http"]["body-rewrite"] = body_rewrites
    if header_rewrites:
        override.setdefault("http", {})
        override["http"]["header-rewrite"] = header_rewrites
    if scripts:
        override.setdefault("http", {})
        override["http"]["script"] = scripts
        override["script-providers"] = script_providers
    # 设置 width 避免默认的单行内容过长导致的换行
    text = yaml.safe_dump(override, sort_keys=False, allow_unicode=True, width=9999)
    headers = {
        "Content-Disposition": "inline",
    }
    return PlainTextResponse(text, media_type="application/yaml;charset=utf-8", headers=headers)


@router.get("/geosite/nameserver-policy/{geosite}", summary="生成基于 geosite 的 nameserver-policy")
async def nameserver_policy_by_geosite(
    geosite: str = Path(..., examples=["google", "google@cn", "google@dns"]),
    dns: str = Query("system", examples=["system", "1.1.1.", "https://223.6.6.6/dns-query"]),
    geosite_url: str = Query(
        "https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat",
        examples=["https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat"],
    ),
):
    """geosite 数据来源自 https://github.com/v2fly/domain-list-community

    数据存在 12-24h 的动态缓存时间
    """
    attribute = None
    if "@" in geosite:
        geosite, attribute = geosite.split("@", 1)
    policy = NameserverPolicyGeositeOverride(geosite, dns=dns, attribute=attribute, geosite_url=geosite_url)
    text = await policy.to_yaml()
    headers = {
        "Content-Disposition": "inline",
    }
    return PlainTextResponse(text, media_type="application/yaml;charset=utf-8", headers=headers)


@router.get("/geosite/ruleset/{geosite}", summary="生成基于 geosite 的 ruleset")
async def ruleset_by_geosite(
    geosite: str = Path(..., examples=["google", "google@cn", "google@dns"]),
    geosite_url: str = Query(
        "https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat",
        examples=["https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat"],
    ),
):
    """geosite 数据来源自 https://github.com/v2fly/domain-list-community

    数据存在 12-24h 的动态缓存时间
    """
    attribute = None
    if "@" in geosite:
        geosite, attribute = geosite.split("@", 1)
    ruleset = RulesetGeositeOverride(geosite, attribute=attribute, geosite_url=geosite_url)
    text = await ruleset.to_yaml()
    headers = {
        "Content-Disposition": "inline",
    }
    return PlainTextResponse(text, media_type="application/yaml;charset=utf-8", headers=headers)
