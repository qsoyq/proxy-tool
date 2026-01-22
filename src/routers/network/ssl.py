import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import ssl_checker
from fastapi import APIRouter, Query
from schemas.network.ssl import SSLCertSchema, SSLCertsResSchema
from utils.basic import AsyncSSLClientContext

router = APIRouter(tags=['Utils'], prefix='/network/ssl')

logger = logging.getLogger(__file__)


def get_peer_cert_context(host: str, port: int = 443) -> SSLCertSchema | None:
    obj = ssl_checker.SSLChecker()
    cert, resolved_ip = obj.get_cert(host, 443)
    context = obj.get_cert_info(host, cert, resolved_ip)
    if context == 'failed':
        return None
    context['tcp_port'] = int(port)
    return SSLCertSchema(**context)


@router.get('/certs', summary='查询网站证书信息', response_model=SSLCertsResSchema)
def certs(hosts: list[str] = Query(..., description='域名列表')):
    """使用 ssl_checker 实现"""
    with ThreadPoolExecutor() as exector:
        result = exector.map(get_peer_cert_context, hosts)
    return {'li': result}


@router.get('/certs/v2', summary='查询网站证书信息V2', response_model=SSLCertsResSchema)
async def certs_v2(hosts: list[str] = Query(..., description='域名列表')):
    """使用 asyncio 实现"""
    results = await asyncio.gather(
        *[AsyncSSLClientContext(host, verify=False).get_peer_certificate() for host in hosts]
    )
    return {'li': results}
