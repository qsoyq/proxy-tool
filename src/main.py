import logging

import typer
import uvicorn
from fastapi import FastAPI
from rssapi.applications.rss.routers.nodeseek import NodeseekToolkit

import middlewares.errors
from events import lifespan
from init import initial
from responses import PingResponse
from schemas.ping import PingRes, ping_responses
from settings import version
from utils.basic import init_logger

cmd = typer.Typer()
app = FastAPI(title='proxy tool', version=version, lifespan=lifespan)
initial(app)


@app.get('/', response_model=PingRes, tags=['Basic'], responses=ping_responses, response_class=PingResponse)
@app.get('/ping', response_model=PingRes, tags=['Basic'], responses=ping_responses, response_class=PingResponse)
async def ping():
    assert getattr(app.state, 'background_gc_task', None)

    m = PingRes.model_construct()
    m.nodeseek = {'ArticlePostCache': list(NodeseekToolkit.ArticlePostCache.keys())}
    m.sentry_cache = await middlewares.errors.SentryCacheMiddleware.get_errors()
    return m


@cmd.command()
def http(
    host: str = typer.Option('0.0.0.0', '--host', '-h', envvar='http_host'),
    port: int = typer.Option(8000, '--port', '-p', envvar='http_port'),
    reload: bool = typer.Option(False, '--debug', envvar='http_reload'),
    log_level: int = typer.Option(logging.DEBUG, '--log_level', envvar='log_level'),
):
    """启动 http 服务"""

    init_logger(log_level)
    logging.info(f'http server listening on {host}:{port}')
    uvicorn.run(app, host=host, port=port, reload=reload)


if __name__ == '__main__':
    cmd()
