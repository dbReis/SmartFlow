"""Application settings, read from ``SMARTFLOW_*`` environment variables."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from smartflow.log_config import LogFormat


class Settings(BaseSettings):
    """Every setting the API reads, with its default.

    Each field maps to an environment variable with the ``SMARTFLOW_`` prefix
    (``database_url`` -> ``SMARTFLOW_DATABASE_URL``). A local ``.env`` file is
    read too; real environment variables take precedence over it.

    Attributes:
        database_url: SQLAlchemy URL, e.g. ``postgresql+asyncpg://user:pw@host/db``.
            Required: startup fails without it.
        db_echo: Log every SQL statement (debugging only).
        db_ssl: Use SSL to the database. On for Neon; off for the local
            Docker database, which has no certificate.
        host: Interface to listen on. ``0.0.0.0`` so it is reachable in a container.
        port: Port to listen on.
        debug: Tornado debug mode (auto-reload, tracebacks in logs).
        log_level: Minimum level logged, e.g. ``INFO``.
        log_format: ``console`` for humans, ``json`` for log collectors.
        pm_api_key: The shared key Product Managers send as a Bearer token.
            ``SecretStr`` keeps it out of logs and reprs. When unset, the PM
            endpoints answer 503.
    """

    model_config = SettingsConfigDict(env_prefix="SMARTFLOW_", env_file=".env")

    database_url: str
    db_echo: bool = False
    db_ssl: bool = True
    host: str = "0.0.0.0"
    port: int = 8888
    debug: bool = False
    log_level: str = "DEBUG"
    log_format: LogFormat = "console"
    pm_api_key: SecretStr | None = None


def get_settings() -> Settings:
    """Load the settings from the environment (and ``.env``).

    Raises:
        pydantic.ValidationError: If a required setting is missing or invalid.
    """
    return Settings()
