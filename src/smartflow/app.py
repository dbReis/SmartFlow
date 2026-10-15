"""Builds the Tornado application: routes, their dependencies and the docs."""

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
    """Create the Tornado application with every route wired up.

    Dependencies are injected per route through Tornado's ``initialize``: public
    routes get ``deps`` (the session factory), Product Manager routes get
    ``pm_deps`` (the session factory plus the PM key).

    Args:
        settings: The loaded configuration.
        session_maker: The app's single session factory, shared by all handlers.

    Returns:
        The application, ready to ``listen()``. Swagger UI is mounted on
        ``/docs`` and the raw spec on ``/openapi.json``.
    """
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
    # \d{1,9} keeps ids numeric and inside PostgreSQL's INTEGER range, so a bad
    # id is a 404 from the router instead of a database error.
    routes = [
        (r"/api/health", HealthHandler, deps),
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
        # Tornado's built-in 404 handler is created with these arguments too.
        default_handler_args=deps,
        debug=settings.debug,
        log_function=log_request,
    )
    api_doc(app, config=build_spec(), url_prefix="/docs", title="SmartFlow API")
    return app
