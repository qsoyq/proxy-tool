import middlewares.errors
import middlewares.json_response
import middlewares.rss
import routers.apple.itunes.appstore
import routers.apple.location
import routers.basic
import routers.bilibili.live.room
import routers.checkin.flyairport
import routers.clash.basic
import routers.clash.config
import routers.convert.curl
import routers.convert.svg
import routers.convert.xml
import routers.dandanplay.bilibili
import routers.iptv.sub
import routers.mikanani.bangumi
import routers.mikanani.rss
import routers.network.dns.doh
import routers.network.proxy.reverse
import routers.network.ssl
import routers.network.url.forward
import routers.network.url.redirect
import routers.nga.thread
import routers.notifications.push
import routers.stash.ruleset
import routers.stash.stoverride
import routers.store.memory
import routers.tool.basic
import routers.tool.browser
import routers.tool.f50
import routers.tool.fingerprint
import routers.tool.image
import routers.tool.url
import routers.v2ex.my
import routers.v2ex.nodes
import routers.webhook.railway
from exception import register_exception_handler
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from ical_api.init import include_routers as include_ical_api_routers
from rssapi.core.middlewares.rss import add_middleware as add_rssapi_middlewares
from rssapi.init import include_routers as include_rssapi_routers
from settings import AppSettings
from utils.mermaid import load_mermaid_plugin


def include_routers(app: FastAPI):
    api_prefix = AppSettings().api_prefix
    app.include_router(routers.basic.router, prefix=api_prefix)
    app.include_router(routers.tool.basic.router, prefix=api_prefix)
    app.include_router(routers.tool.image.router, prefix=api_prefix)
    app.include_router(routers.tool.fingerprint.router, prefix=api_prefix)
    app.include_router(routers.tool.browser.router, prefix=api_prefix)
    app.include_router(routers.tool.url.router, prefix=api_prefix)
    app.include_router(routers.tool.f50.router, prefix=api_prefix)
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
    app.include_router(routers.apple.itunes.appstore.router, prefix=api_prefix)
    app.include_router(routers.iptv.sub.router, prefix=api_prefix)
    app.include_router(routers.dandanplay.bilibili.router, prefix=api_prefix)

    include_rssapi_routers(app, api_prefix=api_prefix)
    include_ical_api_routers(app, api_prefix=api_prefix)


def add_middlewares(app: FastAPI):
    add_rssapi_middlewares(app)
    middlewares.errors.add_middleware(app)
    middlewares.json_response.add_middleware(app)


def init_mcp(app: FastAPI):
    mcp = FastApiMCP(app, name=AppSettings().mcp.mcp_name, description=AppSettings().mcp.mcp_description)
    for tool in mcp.tools:
        tool.name = tool.name[:64]

    mcp.mount_http()


def initial(app: FastAPI):
    include_routers(app)
    add_middlewares(app)

    register_exception_handler(app)
    load_mermaid_plugin()
    init_mcp(app)
