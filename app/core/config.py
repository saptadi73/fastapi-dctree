from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ml-analysis-api"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(
        default="postgresql+asyncpg://openpg:openpgpwd@localhost:5432/dctree"
    )
    storage_dir: Path = Path("storage")
    dev_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:4000"])
    log_level: str = "INFO"
    auto_create_schema: bool = False
    max_upload_size_bytes: int = 25 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
