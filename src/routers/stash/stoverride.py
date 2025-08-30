import re
import uuid
import json
import yaml
import inspect
import logging
import urllib.parse
from typing import Any, cast

import httpx
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import PlainTextResponse
from cachetools import TTLCache
from asyncache import cached

from schemas.adapter import HttpUrl
from schemas.github.releases import ReleaseSchema


router = APIRouter(tags=["Proxy"], prefix="/stash/stoverride")

logger = logging.getLogger(__file__)


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
    return PlainTextResponse(res, headers={"Content-Disposition": "inline"})


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
    return PlainTextResponse(content=content)


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
    return PlainTextResponse(content=content)


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
    return PlainTextResponse(inspect.cleandoc(payload.format(provname=provname)))


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
    return PlainTextResponse(inspect.cleandoc(content))


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
):
    """
    支持以下参数的转写
    - MitM
    - Script
    - Rewrite
        - Header Rewrite
        - URL Rewrite
    - Rule

    已知未支持参数
    - Argument
    - Rewrite
        - Body Rewrite
        - Mock
    """
    async with httpx.AsyncClient(headers={"User-Agent": user_agent}, verify=False) as client:
        resp = await client.get(url)
        if resp.is_error:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    override: dict[str, Any] = {}
    section = None
    mitms: list[str] = []
    rules: list[str] = []
    url_rewrites: list[str] = []
    header_rewrites: list[str] = []
    scripts: list[dict] = []
    script_providers = {}

    for line in resp.text.splitlines():
        line = line.strip()
        if line.startswith("#!"):
            k, v = line[2:].split("=")
            override[k.strip()] = v.strip()
            continue

    for line in resp.text.splitlines():
        line = line.strip()
        if not line:
            continue

        matched = re.match(r"^\[(.*)?\]", line)
        if matched:
            section = matched.group(1)
            continue

        if section is None:
            continue

        match section:
            case "MitM":
                if line.startswith("hostname"):
                    for item in line.split("=", 1)[1].split(","):
                        mitms.append(item.strip())
            case "Rule":
                rules.append(line.replace(" ", ""))
            case "Rewrite":
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
                # response body
            case "Script":
                matched = re.match(r"(http-request|http-response) (.*?http.*?) (.*)", line)
                if not matched:
                    raise ValueError(f"invalid script line: {line}")

                type_, match_, p3 = matched.groups()
                type_ = type_.replace("http-", "")
                p3 = cast(str, p3)
                kwargs = {k: v for item in p3.split(", ") for k, v in [item.split("=")]}
                # TODO: 兼容 Argument
                payload = {
                    "match": match_,
                    "name": kwargs.pop("tag", uuid.uuid4().hex),
                    "type": type_,
                    "require-body": kwargs.pop("requires-body", "false").strip() == "true",
                    # "argument": kwargs.pop("argument", ""),
                    "binary-mode": kwargs.pop("binary-body-mode", "false").strip() == "true",
                    "timeout": 20,
                }
                scripts.append(payload)
                _script = {
                    "url": kwargs.pop("script-path"),
                    "interval": 86400,
                }
                script_providers[payload["name"]] = _script
            case "Argument":
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
    if header_rewrites:
        override.setdefault("http", {})
        override["http"]["header-rewrite"] = header_rewrites
    if scripts:
        override.setdefault("http", {})
        override["http"]["script"] = scripts
        override["script-providers"] = script_providers

    if name is not None:
        override["name"] = name

    if category is not None:
        override["category"] = category

    if icon is not None:
        override["icon"] = icon

    if desc is not None:
        override["desc"] = desc

    text = yaml.safe_dump(override, sort_keys=False, allow_unicode=True)
    headers = {
        "Content-Disposition": "inline",
    }
    return PlainTextResponse(text, media_type="text/plain;charset=utf-8", headers=headers)
