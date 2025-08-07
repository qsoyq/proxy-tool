import uuid
import json
import urllib.parse
import logging
from fastapi.responses import PlainTextResponse
import httpx
from fastapi import APIRouter, Query
from pydantic import HttpUrl
import inspect
import yaml

router = APIRouter(tags=["Proxy"], prefix="/stash/stoverride")

logger = logging.getLogger(__file__)


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
