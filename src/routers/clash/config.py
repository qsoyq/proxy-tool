import logging
from enum import Enum
from fastapi.responses import PlainTextResponse
import httpx
from fastapi import APIRouter, Query
from pydantic import HttpUrl
import yaml


class QxBehaviourEnum(str, Enum):
    reject = "reject"


class QxMatchRuleEnum(str, Enum):
    hostsuffix = "host-suffix"


router = APIRouter(tags=["clash.config"], prefix="/clash/config")

logger = logging.getLogger(__file__)


@router.get("/qx/rules")
def qx(
    url: HttpUrl = Query(..., description="规则文件"),
    behavior: QxBehaviourEnum = Query(..., description="接受处理的行为"),
):
    """将 qx 的规则配置文件转换为 clash 可识别的 rule-set 文件
    匹配规则支持:
        - host-suffix
        行为
    """
    domains = []
    resp = httpx.get(str(url))
    resp.raise_for_status()
    for line in resp.text.split("\n"):
        line = line.strip().replace(" ", "").lower()
        if not line or line.startswith("#"):
            continue
        if not line.endswith(behavior):
            continue
        type_, domain, _ = line.split(",")
        if type_ != QxMatchRuleEnum.hostsuffix:
            continue
        domains.append(f"+.{domain}")
    logger.debug(f"count: {len(domains)}")
    content = yaml.safe_dump({"payload": domains})
    return PlainTextResponse(content=content)
