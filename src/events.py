import asyncio
import gc
import logging
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from rssapi.core.events import lifespan as rssapi_lifespan
from schemas.ping import get_default_memory
from settings import AppSettings

logger = logging.getLogger(__file__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(rssapi_lifespan(app))
        await startup_event(app)
        yield
        await shutdown(app)


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


async def startup_event(app: FastAPI):
    app.state.background_gc_task = asyncio.create_task(background_gc(), name="background_gc")


async def shutdown(app: FastAPI):
    task: asyncio.Task = app.state.background_gc_task
    if not task.done():
        task.cancel()
        logger.info("[shutdown]: background_gc task cancelled")

    logger.info("shutdown")
