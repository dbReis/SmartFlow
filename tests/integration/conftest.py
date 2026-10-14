import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from smartflow.config import Settings
from smartflow.models import Base
from smartflow.storage.database import create_engine, create_session_factory

TEST_PM_KEY = "test-pm-key"


@pytest.fixture
def settings() -> Settings:
    database_url = os.environ.get("SMARTFLOW_TEST_DATABASE_URL")
    if not database_url:
        pytest.fail(
            "SMARTFLOW_TEST_DATABASE_URL is not set. Run the tests in the dev "
            "container, or point it at a PostgreSQL test database."
        )
    return Settings(
        _env_file=None,
        database_url=database_url,
        db_ssl=False,
        pm_api_key=TEST_PM_KEY,
    )


@pytest.fixture
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)
