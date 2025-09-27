import time
import logging
import asyncio
from abc import ABC

from playwright import async_api
from playwright._impl._errors import TargetClosedError


logger = logging.getLogger(__file__)


class AsyncPlaywright(ABC):
    WATCH_URL_PATH = ""
    HEADLESS = True

    def __init__(
        self,
        video_path: str,
        cookie: str | None = None,
        user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        timeout: float = 10,
    ):
        self.video_path = video_path
        self._cookie = cookie
        self.user_agent = user_agent
        self._timeout = timeout
        self._start_ts = time.time()
        self._end_ts = self._start_ts + timeout
        self.fut: asyncio.Future[str | dict] = asyncio.Future()

    @property
    def timeout(self) -> float:
        cur = time.time()
        if cur >= self._end_ts:
            return 0

        return self._end_ts - cur

    @property
    def cookies(self):
        cookies = None
        if self._cookie:
            _cookies = [x.strip().split("=") for x in self._cookie.split(";") if x != ""]
            _cookies_dict = dict([x for x in _cookies if len(x) == 2])
            cookies = [{"name": k, "value": v, "url": "https://www.douyin.com"} for k, v in _cookies_dict.items()]
            logger.debug(f"{self.__class__.__name__} make cookies: {self.video_path}")
        return cookies

    async def run(self):
        logger.debug(f"{self.__class__.__name__} run {self.video_path}")
        url = f"https://www.douyin.com/video/{self.video_path}"

        cookies = self.cookies

        async with async_api.async_playwright() as playwright:
            logger.debug(f"{self.__class__.__name__} enter playwright context: {self.video_path}")
            chromium = playwright.chromium
            browser = await chromium.launch(headless=self.__class__.HEADLESS, timeout=self.timeout * 1000)
            logger.debug(f"{self.__class__.__name__} new browser: {self.video_path}")
            browser = await browser.new_context(user_agent=self.user_agent)
            logger.debug(f"{self.__class__.__name__} new context: {self.video_path}")
            if cookies:
                await browser.add_cookies(cookies)  # type: ignore

            page = await browser.new_page()
            logger.debug(f"{self.__class__.__name__} new page: {self.video_path}")
            page.on("response", self.on_response)

            try:
                logger.debug(f"{self.__class__.__name__} goto page: {self.video_path}")
                await asyncio.wait_for(page.goto(url, timeout=self.timeout * 1000), self.timeout)
                logger.debug(f"{self.__class__.__name__} wait for: {self.video_path}")
                result = await asyncio.wait_for(self.fut, self.timeout)
                logger.debug(f"{self.__class__.__name__} fetch result done, {self.video_path}")
                return result
            except asyncio.TimeoutError as e:
                logger.warning(f"{self.__class__.__name__} [run] 等待数据超时, 请检查用户 id: {self.video_path}")
                raise e
            finally:
                await browser.close()
                logger.debug(f"{self.__class__.__name__} close browser: {self.video_path}")

    async def on_response(self, response: async_api.Response):
        try:
            assert self.__class__.WATCH_URL_PATH, "未指定需要监控的请求路径"
            if self.__class__.WATCH_URL_PATH in response.url:
                try:
                    logger.debug(
                        f"{self.__class__.__name__} [on_response] {self.video_path} {response.request.method}"
                    )
                    is_json = "application/json" in response.headers.get("content-type", "")
                    body = await response.json() if is_json else await response.text()
                    if self.fut and not self.fut.done():
                        self.fut.set_result(body)
                except Exception as e:
                    if self.fut and not self.fut.done():
                        self.fut.set_exception(e)
        except TargetClosedError as e:
            logger.warning(f"{self.__class__.__name__} on_response: TargetClosedError {e}")
