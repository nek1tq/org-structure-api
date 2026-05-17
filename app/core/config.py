from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Org Structure API"
    app_version: str = "0.1.0"
    debug: bool = False

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/org_structure",
        description="Async PostgreSQL connection string",
    )
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    max_tree_depth: int = 5
    default_tree_depth: int = 1

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
