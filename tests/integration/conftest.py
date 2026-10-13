"""Fixtures for the integration tests (real PostgreSQL, real app).

pytest loads this file automatically: any test can use a fixture defined here
just by naming it as a parameter, e.g. ``async def test_x(session_maker): ...``.

Database tests run against the PostgreSQL test database given by
SMARTFLOW_TEST_DATABASE_URL (the dev container's "db" service, or the
PostgreSQL service in CI). Never against Neon.
"""

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
    """App settings for tests, independent of the developer's .env."""
    database_url = os.environ.get("SMARTFLOW_TEST_DATABASE_URL")
    if not database_url:
        pytest.fail(
            "SMARTFLOW_TEST_DATABASE_URL is not set. Run the tests in the dev "
            "container, or point it at a PostgreSQL test database."
        )
    return Settings(
        # _env_file=None: never read .env, which points at Neon.
        _env_file=None,
        database_url=database_url,
        db_ssl=False,
        pm_api_key=TEST_PM_KEY,
    )


@pytest.fixture
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    """The app's own engine, on a freshly created, empty schema.

    Tables are dropped and recreated at the *start* of each test, not the end:
    every test starts from a known state, and after a failing test its data is
    still in the database to inspect (psql -h db -U smartflow smartflow_test).
    """
    engine = create_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """The same session factory the app uses, bound to the test database."""
    return create_session_factory(engine)
