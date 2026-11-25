"""Application configuration loaded from environment variables."""

import secrets
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings for PULSE."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "PULSE"
    APP_ENV: str = "development"

    DATABASE_URL: str = "sqlite:///./pulse.db"

    # If unset in env, generate a secure runtime secret for local development.
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    INGESTION_INTERVAL_MINUTES: int = 30
    INGEST_ON_STARTUP: bool = True
    FEED_FETCH_TIMEOUT_SECONDS: int = 15

    # Optional free-tier JSON News API keys (for additional Indian news JSON sources)
    GNEWS_API_KEY: str = ""
    NEWSDATA_API_KEY: str = ""

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    SEED_DEMO_DATA: bool = True
    DEMO_ADMIN_EMAIL: str = "admin@pulse.org"
    DEMO_ADMIN_PASSWORD: str = "Admin@123"
    DEMO_READER_EMAIL: str = "reader@pulse.org"
    DEMO_READER_PASSWORD: str = "Reader@123"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
