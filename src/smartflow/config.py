from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from smartflow.log_config import LogFormat


class Settings(BaseSettings):
    # Each field is read from SMARTFLOW_<FIELD> (e.g. SMARTFLOW_PORT), then
    # from the .env file, then falls back to the default below.
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
    # Web pages allowed to call this API from a browser (CORS), comma-separated,
    # e.g. "https://smartflow-ui.onrender.com,http://localhost:5173". Empty: none.
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()
        ]


def get_settings() -> Settings:
    return Settings()
