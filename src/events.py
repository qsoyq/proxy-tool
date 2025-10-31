import gc
import time
import traceback
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from schemas.ping import get_default_memory
from settings import AppSettings
from utils.nga import NgaToolkit  # type:ignore
from routers.rss.douyin.user import get_feeds_by_cache
from utils.rss.douyin import AccessHistory

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
        if not AppSettings().rss_douyin_user_auto_fetch_enable:
            logger.info("[rss_douyin_user_auto_fetch] Disable")
            return

        timeout = AppSettings().rss_douyin_user_auto_fetch_timeout
        logger.info("[rss_douyin_user_auto_fetch] Start")
        history = await AccessHistory.get_history()
        for task in history:
            logger.info(f"[rss_douyin_user_auto_fetch] [user] {task.username}")

        # 避免异常频繁重启导致的资源浪费
        await asyncio.sleep(AppSettings().rss_douyin_user_auto_fetch_start_wait)
        while True:
            history = await AccessHistory.get_history()
            cache_hit_count = 0
            for task in history:
                try:
                    cache_hit_count += 1
                    t0 = time.monotonic()
                    logger.debug(f"[rss_douyin_user_auto_fetch] start {task.username}")
                    try:
                        async with asyncio.timeout(timeout):
                            await get_feeds_by_cache(task.username, task.cookie)
                    except TimeoutError:
                        logger.debug(f"[rss_douyin_user_auto_fetch] timeout with {task.username}")

                    t1 = time.monotonic()
                    # 命中缓存的情况下, 连续 30 次命中缓存后才会进入等待
                    # 持续时间大于 1s 认定未命中缓存, 同时重置缓存命中计数器
                    if (t1 - t0) > 1 or cache_hit_count >= 30:
                        cache_hit_count = 0
                        await asyncio.sleep(AppSettings().rss_douyin_user_auto_fetch_once_wait)
                except Exception:
                    msg = traceback.format_exc()
                    logger.warning(f"[rss_douyin_user_auto_fetch] [get_feeds_by_cache] failed, {task.username}\n{msg}")
            await asyncio.sleep(AppSettings().rss_douyin_user_auto_fetch_wait)

    logger.info(f"settings: {AppSettings().model_dump()}")
    app.state.background_gc_task = asyncio.create_task(background_gc(), name="background_gc")
    asyncio.create_task(asyncio.to_thread(NgaToolkit.get_smiles), name="get_smiles")
    asyncio.create_task(rss_douyin_user_auto_fetch(), name="rss_douyin_user_auto_fetch")


async def shutdown(app: FastAPI):
    task: asyncio.Task = app.state.background_gc_task
    if not task.done():
        task.cancel()
        logger.info("[shutdown]: background_gc task cancelled")

    logger.info("shutdown")
