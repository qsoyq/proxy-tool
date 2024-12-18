import time
import logging

import typer
import uvicorn

from fastapi import FastAPI
from pydantic import BaseModel

import routers.basic
import routers.tool.basic
import routers.notifications.push
import routers.webhook.railway
import routers.checkin.flyairport
import routers.store.memory
import routers.clash.basic
import routers.clash.config
import routers.stash.stoverride
import routers.network.dns.doh
import routers.network.proxy.reverse
import routers.network.url.redirect
import routers.network.url.forward
import routers.bilibili.live.room
import routers.convert.xml
import routers.convert.svg
import routers.convert.curl
import routers.mikanani.rss
import routers.nga.thread
import routers.v2ex.nodes
import routers.v2ex.my
from settings import AppSettings

cmd = typer.Typer()
app = FastAPI()
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
app.include_router(routers.nga.thread.router, prefix=api_prefix)
app.include_router(routers.v2ex.nodes.router, prefix=api_prefix)
app.include_router(routers.v2ex.my.router, prefix=api_prefix)
app.include_router(routers.network.dns.doh.router, prefix=api_prefix)
app.include_router(routers.network.proxy.reverse.router, prefix=api_prefix)
app.include_router(routers.network.url.redirect.router, prefix=api_prefix)
app.include_router(routers.network.url.forward.router, prefix=api_prefix)
app.include_router(routers.clash.basic.router, prefix=api_prefix)
app.include_router(routers.clash.config.router, prefix=api_prefix)
app.include_router(routers.stash.stoverride.router, prefix=api_prefix)
run_at_ts = int(time.time())


class PingRes(BaseModel):
    message: str
    timestamp: int
    run_at_ts: int


@app.get("/ping", response_model=PingRes)
async def ping():
    return {"message": "pong", "timestamp": int(time.time()), "run_at_ts": run_at_ts}


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
