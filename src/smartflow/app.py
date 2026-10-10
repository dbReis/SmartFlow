from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tornado.web import Application

from smartflow.config import Settings
from smartflow.log_config import log_request


def make_app(
    settings: Settings, session_maker: async_sessionmaker[AsyncSession]
) -> Application:
    from smartflow.handlers.base import TesteHandler
    from smartflow.handlers.health import HealthHandler

    deps = {"session_maker": session_maker}
    routes = [(r"/api/health", HealthHandler), (r"/api/teste", TesteHandler, deps)]
    return Application(routes, debug=settings.debug, log_function=log_request)
