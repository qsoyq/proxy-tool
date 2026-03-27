import base64
import enum
import logging

import dns.flags
import dns.message
import dns.rdatatype
import httpx
from fastapi import APIRouter, Query
from schemas.adapter import HttpUrl
from schemas.network.dns.doh import DoHResponse


class DoHMethod(str, enum.Enum):
    auto = "auto"
    json = "json"
    wireformat = "wireformat"


router = APIRouter(tags=["Utils"], prefix="/network/dns")

logger = logging.getLogger(__file__)


default_doh = "https://1.1.1.1/dns-query"


def _query_doh_json(url: str, name: str) -> dict | None:
    """尝试使用 JSON API 查询，不支持时返回 None。"""
    resp = httpx.get(
        url,
        params={"name": name, "type": "A"},
        headers={"Accept": "application/dns-json"},
    )
    if resp.status_code != 200:
        return None
    content_type = resp.headers.get("content-type", "")
    if "application/dns-json" not in content_type and "application/json" not in content_type:
        return None
    data: dict = resp.json()
    return data


def _query_doh_wireformat(url: str, name: str) -> dict:
    """使用 RFC 8484 DNS wire format (GET) 查询并转换为 JSON 结构。"""
    q = dns.message.make_query(name, dns.rdatatype.A)
    wire = q.to_wire()
    dns_param = base64.urlsafe_b64encode(wire).rstrip(b"=").decode()

    resp = httpx.get(
        url,
        params={"dns": dns_param},
        headers={"Accept": "application/dns-message"},
    )
    resp.raise_for_status()

    r = dns.message.from_wire(resp.content)
    flags = r.flags

    result: dict = {
        "Status": r.rcode().value,
        "TC": int(bool(flags & dns.flags.TC)),
        "RD": int(bool(flags & dns.flags.RD)),
        "RA": int(bool(flags & dns.flags.RA)),
        "AD": int(bool(flags & dns.flags.AD)),
        "CD": int(bool(flags & dns.flags.CD)),
        "Question": [],
        "Answer": [],
    }

    for rrset in r.question:
        result["Question"].append(
            {
                "name": str(rrset.name),
                "type": rrset.rdtype.value,
            }
        )

    for rrset in r.answer:
        for rdata in rrset:
            result["Answer"].append(
                {
                    "name": str(rrset.name),
                    "type": rrset.rdtype.value,
                    "TTL": rrset.ttl,
                    "data": str(rdata),
                }
            )

    return result


@router.get("/doh", summary="DNS-Over-Https", response_model=DoHResponse)
def doh(
    url: HttpUrl = Query(default_doh, description="使用的 dns服务https 路径"),
    name: str = Query(..., description="域名"),
    method: DoHMethod = Query(
        DoHMethod.auto, description="查询方式: auto 自动检测, json 使用 JSON API, wireformat 使用 RFC 8484 wire format"
    ),
):
    """使用 doh 解析域名， 返回对应的 A记录</br>
    https://1.1.1.1/dns-query</br>
    https://223.5.5.5/resolve</br>
    https://dns.adguard-dns.com/dns-query</br>
    """
    doh_url = str(url)

    if method == DoHMethod.json:
        data = _query_doh_json(doh_url, name)
        if data is None:
            raise httpx.HTTPStatusError(
                f"JSON API not supported by {doh_url}",
                request=httpx.Request("GET", doh_url),
                response=httpx.Response(400),
            )
    elif method == DoHMethod.wireformat:
        data = _query_doh_wireformat(doh_url, name)
    else:
        data = _query_doh_json(doh_url, name)
        if data is None:
            logger.debug(f"doh JSON API not supported for {doh_url}, falling back to wire format")
            data = _query_doh_wireformat(doh_url, name)

    logger.debug(f"doh request domain: {name}\nresponse\n{data}")
    return data
