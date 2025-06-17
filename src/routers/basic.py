import socket
import logging
from fastapi import Depends, APIRouter, Request, Response
from deps import get_current_username

router = APIRouter(tags=["Basic"], prefix="/api/basic")

logger = logging.getLogger(__file__)


@router.get("/users/me", summary="获取当前用户")
def read_current_user(username: str = Depends(get_current_username)):
    return {"username": username}


@router.get("/whoami", summary="返回当前输入信息")
async def whoami(req: Request):
    resp = ""
    hostname = socket.gethostname()
    resp = f"{resp}Hostname: {hostname}\n"

    remote_addr = f"{req.client.host}:{req.client.port}" if req.client else ""
    resp = f"{resp}RemoteAddr:{remote_addr}\n"
    for key, val in req.headers.items():
        resp = f"{resp}{key}: {val}\n"
    logger.debug(f"[whoami]:\n\n{resp}\n")
    return Response(resp)
