"""Database setup: the async engine, the session factory and startup checks."""

import time

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from smartflow.config import Settings
from smartflow.models import Base

log = structlog.get_logger(__name__)


def create_engine(settings: Settings) -> AsyncEngine:
    """Create the app's single engine (and its connection pool).

    Args:
        settings: Provides the URL, SQL echo and SSL options.

    Returns:
        The engine. No connection is opened yet; see check_connection().
    """
    database_url = settings.database_url
    engine = create_async_engine(
        database_url,
        echo=settings.db_echo,
        # Neon closes idle connections: recycle them hourly and test each one
        # before use, so a request never gets a dead connection.
        pool_recycle=3600,
        pool_pre_ping=True,
        connect_args={
            "ssl": settings.db_ssl,
            # Fail after 10 s instead of hanging if the database is unreachable.
            "timeout": 10,
        },
    )
    log.debug(
        "database_engine_created",
        # Host and database name only: the URL holds the password.
        host=engine.url.host,
        database=engine.url.database,
        pool_size=engine.pool.size(),
        echo=settings.db_echo,
    )
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create the factory handlers use to open one session per request.

    ``expire_on_commit=False`` keeps the loaded values on the objects after
    commit. Handlers serialise objects after their transaction ends; with
    expiry on, reading an attribute would trigger a lazy load outside async
    context and fail with MissingGreenlet.
    """
    return async_sessionmaker(engine, expire_on_commit=False)


async def check_connection(engine: AsyncEngine) -> None:
    """Run ``SELECT 1`` so a bad URL or password fails at startup, not on the first request.

    Raises:
        Exception: Whatever the driver raised; logged first (its type only,
            since the message may contain connection details).
    """
    log.debug("database_connection_checking", host=engine.url.host)
    started = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.scalar(text("SELECT 1"))
    except Exception as exc:
        log.error(
            "database_connection_failed",
            host=engine.url.host,
            error=type(exc).__name__,
        )
        raise
    log.info(
        "database_connected",
        host=engine.url.host,
        database=engine.url.database,
        ms=round((time.perf_counter() - started) * 1000),
    )


async def create_tables(engine: AsyncEngine) -> None:
    """Create any missing tables. Existing tables are left untouched.

    A stand-in for migrations (Alembic): it creates new tables but never alters
    existing ones.

    Raises:
        Exception: Whatever the database raised; logged first.
    """
    log.debug("tables_creating", tables=list(Base.metadata.tables))
    try:
        async with engine.begin() as conn:
            # create_all is synchronous; run_sync runs it on the async connection.
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        log.error(
            "tables_creation_failed",
            host=engine.url.host,
            error=type(exc).__name__,
        )
        raise
    log.info("tables_ready", tables=list(Base.metadata.tables))
