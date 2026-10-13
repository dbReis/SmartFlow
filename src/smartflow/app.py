import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from swagger_ui import api_doc
from tornado.web import Application

from smartflow.config import Settings
from smartflow.handlers.category import CategoryHandler
from smartflow.log_config import log_request
from smartflow.openapi import build_spec

log = structlog.get_logger(__name__)


def make_app(
    settings: Settings, session_maker: async_sessionmaker[AsyncSession]
) -> Application:
    from smartflow.handlers.base import NotFoundHandler
    from smartflow.handlers.comments import CommentsHandler
    from smartflow.handlers.docs import OpenAPIHandler
    from smartflow.handlers.feedback import (
        FeedbackCategoryHandler,
        FeedbackHandler,
        FeedbackItemHandler,
        FeedbackMergeHandler,
        FeedbackStatusHandler,
    )
    from smartflow.handlers.health import HealthHandler
    from smartflow.handlers.notation import NotationHandler
    from smartflow.handlers.pm_base_handler import PMSessionHandler

    deps = {"session_maker": session_maker}
    pm_deps = {**deps, "pm_api_key": settings.pm_api_key}
    routes = [
        (r"/api/health", HealthHandler),
        (r"/api/feedback", FeedbackHandler, deps),
        (r"/api/feedback/(\d{1,9})", FeedbackItemHandler, deps),
        (r"/api/feedback/(\d{1,9})/comments", CommentsHandler, deps),
        (r"/api/comments/(\d{1,9})/notation", NotationHandler, deps),
        (r"/api/feedback/(\d{1,9})/category", FeedbackCategoryHandler, pm_deps),
        (r"/api/feedback/(\d{1,9})/status", FeedbackStatusHandler, pm_deps),
        (r"/api/feedback/(\d{1,9})/merge", FeedbackMergeHandler, pm_deps),
        (r"/api/category", CategoryHandler, pm_deps),
        (r"/api/pm/session", PMSessionHandler, pm_deps),
        (r"/openapi.json", OpenAPIHandler),
    ]
    log.debug("routes_registered", paths=[route[0] for route in routes])
    app = Application(
        routes,
        # Any URL that matches no route: a JSON 404 like every other error.
        default_handler_class=NotFoundHandler,
        default_handler_args=deps,
        debug=settings.debug,
        log_function=log_request,
    )
    # Swagger UI at /docs, served from the swagger-ui-py package (no CDN).
    api_doc(app, config=build_spec(), url_prefix="/docs", title="SmartFlow API")
    return app
