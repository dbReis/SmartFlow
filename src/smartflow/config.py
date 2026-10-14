from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from smartflow.log_config import LogFormat


class Settings(BaseSettings):
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
    return Settings()
