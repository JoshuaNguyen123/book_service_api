"""Application configuration from environment."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings; load from env and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database (use forward slashes for paths; works on Windows, macOS, Linux)
    database_url: str = "sqlite:///./data/app.db"

    # CORS: disabled by default; set CORS_ORIGINS to enable (e.g. "http://localhost:3000")
    cors_origins: str | None = None

    # Server (for documentation; run with: uvicorn app.main:app --host HOST --port PORT)
    host: str = "0.0.0.0"
    port: int = 8000


def get_database_path() -> Path:
    """Resolve DB file path for SQLite from database_url."""
    url = Settings().database_url
    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "", 1)
        return Path(path)
    return Path("./data/app.db")
