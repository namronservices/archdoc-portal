"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://archdoc:archdoc@localhost:5432/archdoc"

    # Filesystem roots
    git_data_root: str = "/data/git"
    artifacts_root: str = "/data/artifacts"

    # Fixed Git commit author (no auth in Phase 1)
    git_author_name: str = "ArchDoc Portal"
    git_author_email: str = "portal@archdoc.local"

    # Puppeteer launch config passed to mermaid-cli (enables --no-sandbox in
    # containers). Ignored when the file does not exist (e.g. local runs).
    mermaid_puppeteer_config: str = "/etc/puppeteer.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
