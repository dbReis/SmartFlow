import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from smartflow.config import Settings

log = structlog.get_logger(__name__)


def create_engine(settings: Settings) -> AsyncEngine:
    database_url = settings.database_url
    engine = create_async_engine(
        database_url,
        echo=settings.db_echo,
        pool_recycle=3600,  # Recycle connections every hour
        pool_pre_ping=True,  # Neon's dev branch sleeps after ~5 min idle
        connect_args={
            "ssl": True,  # Neon requires SSL connections
            "timeout": 10,  # Fail after 10 s instead of asyncpg's default 60 s
        },
    )
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def check_connection(engine: AsyncEngine) -> None:
    log.debug(
        "Checking database connection", host=engine.url.host, port=engine.url.port
    )
    try:
        async with engine.connect() as conn:
            await conn.scalar(text("SELECT 1"))
        log.info(
            "Database connection check successful",
            host=engine.url.host,
            port=engine.url.port,
        )
    except Exception as exc:
        log.error(
            "Database connection check failed",
            host=engine.url.host,
            port=engine.url.port,
            error=type(exc).__name__,
        )

        raise
