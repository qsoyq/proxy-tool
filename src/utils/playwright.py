import asyncio
import logging
import time
from abc import ABC

from playwright import async_api
from playwright._impl._errors import TargetClosedError

logger = logging.getLogger(__file__)


class AsyncPlaywright(ABC):
    WATCH_URL_PATH = ''
    HEADLESS = True

    def __init__(
        self,
        url: str,
        user_agent: str = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    ):
        self.url = url
        self._cookies: list = []
        self.user_agent = user_agent
        self._start_ts = time.time()
        self.fut: asyncio.Future[str | dict] = asyncio.Future()

    def add_cookies(self, cookies: list):
        self._cookies.extend(cookies)

    def cookies_by_str(self, cookie: str, url: str) -> list:
        _cookies = [x.strip().split('=') for x in cookie.split(';') if x != '']
        _cookies_dict = dict([x for x in _cookies if len(x) == 2])
        cookies = [{'name': k, 'value': v, 'url': url} for k, v in _cookies_dict.items()]
        return cookies

    async def run(self):
        logger.debug(f'{self.__class__.__name__} run {self.url}')
        url = self.url
        cookies = self._cookies
        async with async_api.async_playwright() as playwright:
            logger.debug(f'{self.__class__.__name__} enter playwright context: {self.url}')
            chromium = playwright.chromium
            browser = await chromium.launch(headless=self.__class__.HEADLESS)
            logger.debug(f'{self.__class__.__name__} new browser: {self.url}')
            browser = await browser.new_context(user_agent=self.user_agent)
            logger.debug(f'{self.__class__.__name__} new context: {self.url}')
            if cookies:
                await browser.add_cookies(cookies)  # type: ignore

            page = await browser.new_page()
            logger.debug(f'{self.__class__.__name__} new page: {self.url}')
            page.on('response', self.on_response)

            try:
                logger.debug(f'{self.__class__.__name__} goto page: {self.url}')
                await page.goto(url)
                logger.debug(f'{self.__class__.__name__} wait for: {self.url}')
                result = await self.fut
                logger.debug(f'{self.__class__.__name__} fetch result done, {self.url}')
                return result
            except Exception as e:
                logger.warning(f'{self.__class__.__name__} [run] 运行错误, 请检查用户 id: {self.url}')
                raise e
            finally:
                await browser.close()
                logger.debug(f'{self.__class__.__name__} close browser: {self.url}')

    async def on_response(self, response: async_api.Response):
        try:
            assert self.__class__.WATCH_URL_PATH, '未指定需要监控的请求路径'
            if self.__class__.WATCH_URL_PATH in response.url:
                try:
                    logger.debug(f'{self.__class__.__name__} [on_response] {self.url} {response.request.method}')
                    is_json = 'application/json' in response.headers.get('content-type', '')
                    body = await response.json() if is_json else await response.text()
                    if self.fut and not self.fut.done():
                        self.fut.set_result(body)
                except Exception as e:
                    if self.fut and not self.fut.done():
                        self.fut.set_exception(e)
        except TargetClosedError as e:
            logger.warning(f'{self.__class__.__name__} on_response: TargetClosedError {e}')
