"""Entry point: ``python -m smartflow`` (or the ``smartflow`` script).

Loads the settings, configures logging, connects to the database and serves
the API until the process is stopped.
"""

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
    """Start the API and keep it running until the process is stopped.

    Startup fails fast: if the database is unreachable or the tables can't be
    created, the error is raised before the server accepts any request.

    Args:
        settings: The loaded configuration (database URL, host, port, ...).
    """
    engine = create_engine(settings)
    await check_connection(engine)
    await create_tables(engine)
    session_maker = create_session_factory(engine)
    app = make_app(settings, session_maker)
    app.listen(settings.port, address=settings.host)
    log.info("server_started", host=settings.host, port=settings.port)
    try:
        # Tornado serves on the running event loop; wait forever (until Ctrl+C / SIGTERM).
        await asyncio.Event().wait()
    finally:
        log.info("server_stopping")
        # Close the pooled connections cleanly instead of letting the database time them out.
        await engine.dispose()
        log.debug("database_engine_disposed")


def main():
    """Load the settings, set up logging, then run the server.

    Logging is configured first so every later message (including startup
    failures) uses the chosen format. Secrets such as the database URL and the
    PM key are never logged.
    """
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
