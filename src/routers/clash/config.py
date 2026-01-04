import logging
from enum import Enum

import httpx
import yaml
from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from schemas.adapter import HttpUrl


class QxBehaviourEnum(str, Enum):
    reject = 'reject'


class QxMatchRuleEnum(str, Enum):
    hostsuffix = 'host-suffix'


router = APIRouter(tags=['Proxy'], prefix='/clash/config')

logger = logging.getLogger(__file__)


@router.get('/qx/rules', summary='qx规则转clash')
def qx(
    url: HttpUrl = Query(..., description='规则文件'),
    behavior: QxBehaviourEnum = Query(..., description='接受处理的行为'),
):
    """将 qx 的规则配置文件转换为 clash 可识别的 rule-set 文件
    匹配规则支持:
        - host-suffix

    """
    domains = []
    resp = httpx.get(str(url))
    resp.raise_for_status()
    for line in resp.text.split('\n'):
        line = line.strip().replace(' ', '').lower()
        if not line or line.startswith('#'):
            continue
        if not line.endswith(behavior):
            continue
        type_, domain, _ = line.split(',')
        if type_ != QxMatchRuleEnum.hostsuffix:
            continue
        domains.append(f'+.{domain}')
    content = yaml.safe_dump({'payload': domains}, allow_unicode=True)
    return PlainTextResponse(content=content)


@router.get('/qx/nocomments', summary='移除文本中的部分注释')
async def qx_no_comments(
    url: HttpUrl = Query(..., description='规则文件'),
):
    """script-hub 处理带有注释的 qx 规则会存在异常"""
    resp = httpx.get(str(url), verify=False)
    resp.raise_for_status()
    lines = []
    for line in resp.text.split('\n'):
        if line.startswith('#!') or not line.startswith('#'):
            if line:
                lines.append(line)
    content = '\n\n'.join(lines)
    return PlainTextResponse(content=content)
