import yaml
import logging
from fastapi.responses import PlainTextResponse
import httpx
from fastapi import APIRouter, Query
from pydantic import HttpUrl


router = APIRouter(tags=["Proxy"], prefix="/stash/ruleset")

logger = logging.getLogger(__file__)


@router.get("/adblock", summary="Adblock-style规则集转换")
def adblock_to_ruleset(url: HttpUrl = Query(...)):
    r"""转换为 yaml 格式, domain 类型的规则集

    支持以下规则
    - ||stun1.douyucdn.cn
    - ||mcdn.bilivideo.cn^

    不支持以下规则
    /.*pcdn.*biliapi\.net/
    """
    resp = httpx.get(str(url))
    resp.raise_for_status()
    domains = []
    suffix_domains = []
    for line in resp.text.split("\n"):
        line = line.strip()
        if line.startswith("||") and line.endswith("^"):
            domains.append(f"{line[2:-1]}")
        elif line.startswith("||"):
            suffix_domains.append(f"+.{line[2:]}")
        elif line.startswith("/") and line.endswith("/"):
            # todo: support regex pattern rule
            pass
        else:
            logger.warning(f"unsupport rule type: {line}")
    contents = list(set(domains) | set(suffix_domains))
    suffix_domains = list(set(suffix_domains))
    return PlainTextResponse(yaml.safe_dump({"payload": contents}, allow_unicode=True))
