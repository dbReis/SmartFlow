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
    database_url = settings.database_url
    engine = create_async_engine(
        database_url,
        echo=settings.db_echo,
        pool_recycle=3600,
        pool_pre_ping=True,
        connect_args={
            "ssl": settings.db_ssl,
            "timeout": 10,
        },
    )
    log.debug(
        "database_engine_created",
        host=engine.url.host,
        database=engine.url.database,
        pool_size=engine.pool.size(),
        echo=settings.db_echo,
    )
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def check_connection(engine: AsyncEngine) -> None:
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
    log.debug("tables_creating", tables=list(Base.metadata.tables))
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        log.error(
            "tables_creation_failed",
            host=engine.url.host,
            error=type(exc).__name__,
        )
        raise
    log.info("tables_ready", tables=list(Base.metadata.tables))
