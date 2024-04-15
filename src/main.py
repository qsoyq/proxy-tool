import logging

import typer
import uvicorn

from fastapi import FastAPI

import routers.clash.basic
import routers.clash.config
import routers.stash.stoverride
import routers.network.dns.doh
import routers.network.proxy.reverse
import routers.network.url.redirect
import routers.bilibili.live.room
import routers.convert.xml

from settings import AppSettings

cmd = typer.Typer()
app = FastAPI()
api_prefix = AppSettings().api_prefix
app.include_router(routers.clash.basic.router, prefix=api_prefix)
app.include_router(routers.clash.config.router, prefix=api_prefix)
app.include_router(routers.stash.stoverride.router, prefix=api_prefix)
app.include_router(routers.network.dns.doh.router, prefix=api_prefix)
app.include_router(routers.network.proxy.reverse.router, prefix=api_prefix)
app.include_router(routers.network.url.redirect.router, prefix=api_prefix)
app.include_router(routers.bilibili.live.room.router, prefix=api_prefix)
app.include_router(routers.convert.xml.router, prefix=api_prefix)


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
