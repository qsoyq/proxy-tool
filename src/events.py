import gc
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from schemas.ping import get_default_memory
from settings import AppSettings
from utils import NgaToolkit  # type:ignore
from routers.rss.douyin.user import get_feeds_by_cache, DouyinPlaywright

logger = logging.getLogger(__file__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_event(app)
    yield
    await shutdown(app)


async def startup_event(app: FastAPI):
    async def background_gc():
        while True:
            memory = get_default_memory()
            memory_percent = float(memory.percent[:-1])
            settings = AppSettings()
            if memory_percent >= settings.gc_trigger_memory_percent_limit:
                logger.debug(
                    f"[background_gc]: trigger gc collect because memory exceeds 80, current: {memory_percent}",
                )
                gc.collect()
            await asyncio.sleep(settings.gc_trigger_memory_percent_interval)

    async def rss_douyin_user_auto_fetch():
        """根据历史访问过的用户 ID, 定时获取

        RSS 客户端串行同步请求订阅，并在一定时间后结束

        如果每次访问数据过慢，会导致每次更新订阅仅刷新少数订阅源
        """
        logger.info("[rss_douyin_user_auto_fetch] Start")
        while True:
            for task in DouyinPlaywright.HISTORY.copy():
                try:
                    await get_feeds_by_cache(task.username, task.cookie)
                except Exception as e:
                    logger.warning(f"[rss_douyin_user_auto_fetch start] [get_feeds_by_cache] failed, {e}")
            await asyncio.sleep(AppSettings().rss_douyin_user_auto_fetch_wait)

    app.state.background_gc_task = asyncio.create_task(background_gc())
    asyncio.create_task(asyncio.to_thread(NgaToolkit.get_smiles))
    asyncio.create_task(rss_douyin_user_auto_fetch())


async def shutdown(app: FastAPI):
    task: asyncio.Task = app.state.background_gc_task
    if not task.done():
        task.cancel()
        logger.info("[shutdown]: background_gc task cancelled")
