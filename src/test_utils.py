from utils import AsyncSSLClientContext


import pytest


@pytest.mark.asyncio
async def test_async_ssl_client_context():
    for host in ("www.baidu.com", "www.tencent.com", "www.youtube.com", "www.google.com"):
        client = AsyncSSLClientContext(host, verify=False)
        cert = await client.get_peer_certificate()
        assert cert, cert
