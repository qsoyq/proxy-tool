import logging

import httpx
from fastapi import APIRouter, HTTPException, Query
from schemas.apple.itunes import SearchAppListSchema

router = APIRouter(tags=["Utils"], prefix="/apple/itunes")

logger = logging.getLogger(__file__)


@router.get("/appstore/apps", summary="AppStore查询", response_model=SearchAppListSchema)
async def app_list(
    term: str = Query(..., description="搜索名称"),
    entity: str | None = Query("software", description="搜索类别"),
    country: str | None = Query(None, description="地区", examples=["cn", "us"]),
):
    params = {
        "term": term,
    }
    if entity is not None:
        params["entity"] = entity
    if country is not None:
        params["country"] = country
    # ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/605.1.15"
    ua = ""
    url = "https://itunes.apple.com/search"
    async with httpx.AsyncClient(headers={"User-Agent": ua}) as client:
        resp = await client.get(url, params=params)
        if resp.is_error:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()["results"]
    return {"data": data}
