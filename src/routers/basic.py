import logging
from fastapi import Depends
from fastapi import APIRouter
from deps import get_current_username

router = APIRouter(tags=["Basic"], prefix="/api/basic")

logger = logging.getLogger(__file__)


@router.get("/users/me", summary="获取当前用户")
def read_current_user(username: str = Depends(get_current_username)):
    return {"username": username}
