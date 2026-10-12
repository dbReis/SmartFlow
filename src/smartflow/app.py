import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tornado.web import Application

from smartflow.config import Settings
from smartflow.handlers.category import CategoryHandler
from smartflow.log_config import log_request

log = structlog.get_logger(__name__)


def make_app(
    settings: Settings, session_maker: async_sessionmaker[AsyncSession]
) -> Application:
    from smartflow.handlers.comments import CommentsHandler
    from smartflow.handlers.docs import OpenAPIHandler, SwaggerUIHandler
    from smartflow.handlers.feedback import (
        FeedbackCategoryHandler,
        FeedbackHandler,
        FeedbackStatusHandler,
    )
    from smartflow.handlers.health import HealthHandler
    from smartflow.handlers.notation import NotationHandler

    deps = {"session_maker": session_maker}
    pm_deps = {**deps, "pm_api_key": settings.pm_api_key}
    routes = [
        (r"/api/health", HealthHandler),
        (r"/api/feedback", FeedbackHandler, deps),
        (r"/api/feedback/(\d{1,9})/comments", CommentsHandler, deps),
        (r"/api/comments/(\d{1,9})/notation", NotationHandler, deps),
        (r"/api/feedback/(\d{1,9})/category", FeedbackCategoryHandler, pm_deps),
        (r"/api/feedback/(\d{1,9})/status", FeedbackStatusHandler, pm_deps),
        (r"/api/category", CategoryHandler, pm_deps),
        (r"/docs/?", SwaggerUIHandler),
        (r"/openapi.json", OpenAPIHandler),
    ]
    log.debug("routes_registered", paths=[route[0] for route in routes])
    return Application(
        routes,
        default_handler_args=deps,
        debug=settings.debug,
        log_function=log_request,
    )
