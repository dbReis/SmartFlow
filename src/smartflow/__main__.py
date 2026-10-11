import asyncio

import structlog

from smartflow.app import make_app
from smartflow.config import Settings, get_settings
from smartflow.log_config import configure_logging
from smartflow.storage.database import (
    check_connection,
    create_engine,
    create_session_factory,
    create_tables,
)

log = structlog.get_logger(__name__)


async def serve(settings: Settings):
    engine = create_engine(settings)
    await check_connection(engine)
    await create_tables(engine)
    session_maker = create_session_factory(engine)
    app = make_app(settings, session_maker)
    app.listen(settings.port, address=settings.host)
    log.info("server_started", host=settings.host, port=settings.port)
    try:
        await asyncio.Event().wait()
    finally:
        log.info("server_stopping")
        await engine.dispose()
        log.debug("database_engine_disposed")


def main():
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    log.debug(
        "settings_loaded",
        host=settings.host,
        port=settings.port,
        debug=settings.debug,
        db_echo=settings.db_echo,
        log_level=settings.log_level,
        log_format=settings.log_format,
    )
    asyncio.run(serve(settings))


if __name__ == "__main__":
    main()
