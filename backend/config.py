"""
NEXUS — Adaptive Network Resilience Intelligence
Configuration management via pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file="D:/AIORI/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite+aiosqlite:///D:/AIORI/nexus.db",
        alias="DATABASE_URL",
    )
    sync_database_url: str = Field(
        default="sqlite:///D:/AIORI/nexus.db",
        alias="SYNC_DATABASE_URL",
    )

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    debug: bool = Field(default=True, alias="DEBUG")

    # ── Simulation ────────────────────────────────────────────────────────────
    simulation_backend: str = Field(default="wsl", alias="SIMULATION_BACKEND")
    wsl_distro: str = Field(default="Ubuntu", alias="WSL_DISTRO")


# Singleton settings instance used across the app
settings = Settings()

