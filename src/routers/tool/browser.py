import logging
from fastapi import APIRouter, Query
from schemas.adapter import HttpUrl
from responses import PrettyJSONResponse
from playwright.async_api import async_playwright


router = APIRouter(tags=["Utils"], prefix="/broswer")

logger = logging.getLogger(__file__)


@router.get("/playwright", summary="playwright", response_class=PrettyJSONResponse)
async def playwright(
    url: HttpUrl = Query(...),
    cookie: str = Query(None),
    userAgent: str = Query(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        examples=[
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
        ],
    ),
):
    cookies = []
    if cookie is not None:
        _cookies = dict([x.strip().split("=") for x in cookie.split(";") if x != ""])
        cookies = [{"name": k, "value": v, "url": url} for k, v in _cookies.items()]
    async with async_playwright() as playwright:
        chromium = playwright.chromium
        browser = await chromium.launch()
        browser = await browser.new_context(user_agent=userAgent)
        if cookies:
            await browser.add_cookies(cookies)  # type: ignore

        page = await browser.new_page()
        res = await page.goto(url)
        text = await res.text() if res else None
        status = res.status if res else None
        await browser.close()
    return {"text": text, "status": status}
