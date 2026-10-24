"""Environment-backed settings. No secrets are required for the public Elexon API."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    http_timeout_seconds: float = 30.0
    http_max_retries: int = 3
    cache_ttl_seconds: int = 900
    cors_origins: str = "*"
    near_zero_mw: float = 1.0
    log_level: str = "INFO"
    forecast_lead_days: int = 4
    chunk_days: int = 7
    max_range_days: int = 31

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw == "*":
            return ["*"]
        return [part.strip() for part in raw.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
