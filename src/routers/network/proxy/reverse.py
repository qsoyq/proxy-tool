import logging
import httpx
from fastapi import APIRouter, Path, Request
from fastapi.responses import Response

router = APIRouter(tags=["network.proxy"], prefix="/network/proxy")

logger = logging.getLogger(__file__)


@router.get("/reverse/{host}/{path:path}", summary="转发请求")
@router.post("/reverse/{host}/{path:path}", summary="转发请求")
@router.put("/reverse/{host}/{path:path}", summary="转发请求")
@router.delete("/reverse/{host}/{path:path}", summary="转发请求")
@router.options("/reverse/{host}/{path:path}", summary="转发请求")
@router.head("/reverse/{host}/{path:path}", summary="转发请求")
@router.patch("/reverse/{host}/{path:path}", summary="转发请求")
@router.trace("/reverse/{host}/{path:path}", summary="转发请求")
async def forwarding(
    req: Request,
    host: str = Path(..., description="请求主机地址"),
    path: str = Path("", description="请求路径"),
):
    """转发请求"""
    method = req.method
    scheme = req.url.scheme
    scheme = "https"
    query = req.url.query
    headers = {}
    headers = dict(req.headers)
    headers["host"] = host
    url = f"{scheme}://{host}/{path}"
    logger.debug(f"\nurl: {url}\nheaders:{headers}")
    body = await req.body()
    client = httpx.AsyncClient()
    res = await client.request(method, url, headers=headers, params=query, content=body)
    logger.debug(f"\nres\nheaders:{dict(res.headers)}")
    return Response(content=res.content, status_code=res.status_code, headers=dict(res.headers))
