import gc
import logging
import asyncio


import typer
import uvicorn

from fastapi import FastAPI


from exception import register_exception_handler
import routers.basic
import routers.tool.basic
import routers.notifications.push
import routers.webhook.railway
import routers.checkin.flyairport
import routers.store.memory
import routers.clash.basic
import routers.clash.config
import routers.stash.stoverride
import routers.stash.ruleset
import routers.network.dns.doh
import routers.network.proxy.reverse
import routers.network.url.redirect
import routers.network.url.forward
import routers.network.ssl
import routers.bilibili.live.room
import routers.convert.xml
import routers.convert.svg
import routers.convert.curl
import routers.mikanani.rss
import routers.mikanani.bangumi
import routers.nga.thread
import routers.v2ex.nodes
import routers.v2ex.my
import routers.apple.location
import routers.apple.ics
import routers.apple.ics.github
import routers.apple.ics.vlrgg
import routers.apple.ics.gofans
import routers.iptv.sub
import routers.rss.nnr
import routers.rss.day1024
import routers.rss.nodeseek
import routers.rss.v2ex
import routers.rss.nga
import routers.rss.gofans
from settings import AppSettings, version
from schemas.ping import ping_responses, PingRes, get_default_memory

cmd = typer.Typer()
app = FastAPI(title="proxy tool", version=version)
api_prefix = AppSettings().api_prefix
app.include_router(routers.basic.router, prefix=api_prefix)
app.include_router(routers.tool.basic.router, prefix=api_prefix)
app.include_router(routers.notifications.push.router, prefix=api_prefix)
app.include_router(routers.webhook.railway.router, prefix=api_prefix)
app.include_router(routers.checkin.flyairport.router, prefix=api_prefix)
app.include_router(routers.store.memory.router, prefix=api_prefix)
app.include_router(routers.bilibili.live.room.router, prefix=api_prefix)
app.include_router(routers.convert.xml.router, prefix=api_prefix)
app.include_router(routers.convert.svg.router, prefix=api_prefix)
app.include_router(routers.convert.curl.router, prefix=api_prefix)
app.include_router(routers.mikanani.rss.router, prefix=api_prefix)
app.include_router(routers.mikanani.bangumi.router, prefix=api_prefix)
app.include_router(routers.nga.thread.router, prefix=api_prefix)
app.include_router(routers.v2ex.nodes.router, prefix=api_prefix)
app.include_router(routers.v2ex.my.router, prefix=api_prefix)
app.include_router(routers.network.dns.doh.router, prefix=api_prefix)
app.include_router(routers.network.proxy.reverse.router, prefix=api_prefix)
app.include_router(routers.network.url.redirect.router, prefix=api_prefix)
app.include_router(routers.network.url.forward.router, prefix=api_prefix)
app.include_router(routers.network.ssl.router, prefix=api_prefix)
app.include_router(routers.clash.basic.router, prefix=api_prefix)
app.include_router(routers.clash.config.router, prefix=api_prefix)
app.include_router(routers.stash.stoverride.router, prefix=api_prefix)
app.include_router(routers.stash.ruleset.router, prefix=api_prefix)
app.include_router(routers.apple.location.router, prefix=api_prefix)
app.include_router(routers.apple.ics.router, prefix=api_prefix)
app.include_router(routers.apple.ics.github.router, prefix=api_prefix)
app.include_router(routers.apple.ics.vlrgg.router, prefix=api_prefix)
app.include_router(routers.apple.ics.gofans.router, prefix=api_prefix)
app.include_router(routers.iptv.sub.router, prefix=api_prefix)
app.include_router(routers.rss.nnr.router, prefix=api_prefix)
app.include_router(routers.rss.day1024.router, prefix=api_prefix)
app.include_router(routers.rss.nodeseek.router, prefix=api_prefix)
app.include_router(routers.rss.v2ex.router, prefix=api_prefix)
app.include_router(routers.rss.nga.router, prefix=api_prefix)
app.include_router(routers.rss.gofans.router, prefix=api_prefix)

register_exception_handler(app)

logger = logging.getLogger(__file__)


@app.on_event("startup")
async def startup_event():
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

    app.state.background_gc_task = asyncio.create_task(background_gc())


@app.on_event("shutdown")
async def shutdown():
    task: asyncio.Task = app.state.background_gc_task
    if not task.done:
        task.cancel()
        logger.info("[shutdown]: background_gc task cancelled")


@app.get("/", response_model=PingRes, tags=["Basic"], responses=ping_responses)
@app.get("/ping", response_model=PingRes, tags=["Basic"], responses=ping_responses)
async def ping():
    assert getattr(app.state, "background_gc_task", None)
    return PingRes.construct()


@cmd.command()
def http(
    host: str = typer.Option("0.0.0.0", "--host", "-h", envvar="http_host"),
    port: int = typer.Option(8000, "--port", "-p", envvar="http_port"),
    reload: bool = typer.Option(False, "--debug", envvar="http_reload"),
    log_level: int = typer.Option(logging.DEBUG, "--log_level", envvar="log_level"),
):
    """启动 http 服务"""
    logging.basicConfig(level=log_level)
    logging.info(f"http server listening on {host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    cmd()
