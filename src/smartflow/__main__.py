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
    log.info("server started", host=settings.host, port=settings.port)
    try:
        await asyncio.Event().wait()
    finally:
        await engine.dispose()


def main():
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    asyncio.run(serve(settings))


if __name__ == "__main__":
    main()
