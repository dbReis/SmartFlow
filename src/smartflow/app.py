import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tornado.web import Application

from smartflow.config import Settings
from smartflow.log_config import log_request

log = structlog.get_logger(__name__)


def make_app(
    settings: Settings, session_maker: async_sessionmaker[AsyncSession]
) -> Application:
    from smartflow.handlers.feedback import FeedbackHandler
    from smartflow.handlers.health import HealthHandler

    deps = {"session_maker": session_maker}
    routes = [
        (r"/api/health", HealthHandler),
        (r"/api/feedback", FeedbackHandler, deps),
    ]
    log.debug("routes_registered", paths=[route[0] for route in routes])
    return Application(routes, debug=settings.debug, log_function=log_request)
