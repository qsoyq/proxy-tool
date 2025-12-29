import gc
import logging
import asyncio
from contextlib import asynccontextmanager
import rssapi.core.events
from fastapi import FastAPI
from schemas.ping import get_default_memory
from settings import AppSettings
from utils.nga import NgaToolkit  # type:ignore

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

    app.state.background_gc_task = asyncio.create_task(background_gc(), name="background_gc")
    asyncio.create_task(asyncio.to_thread(NgaToolkit.get_smiles), name="get_smiles")
    await rssapi.core.events.startup_event(app)


async def shutdown(app: FastAPI):
    task: asyncio.Task = app.state.background_gc_task
    if not task.done():
        task.cancel()
        logger.info("[shutdown]: background_gc task cancelled")

    logger.info("shutdown")
