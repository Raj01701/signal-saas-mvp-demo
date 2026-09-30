"""API configuration from the environment (prefix ``JYOTISH_API_``)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JYOTISH_API_", extra="ignore")

    #: Browser origins allowed to call the API (the web app).
    cors_origins: list[str] = ["http://localhost:3000"]
    #: Requests per client address, in the ``limits`` notation.
    rate_limit: str = "120/minute"
    #: Charts kept in memory, keyed by birth data, settings and engine version.
    chart_cache_size: int = 512
    #: SQLAlchemy URL; SQLite by default, Postgres (pg8000 driver) in production.
    database_url: str = "sqlite:///./jyotish.db"
    #: Supabase token verification: the project's JWT secret (HS256) or its JWKS URL.
    supabase_jwt_secret: str | None = None
    supabase_jwks_url: str | None = None
    supabase_audience: str = "authenticated"
    #: Narratives: "template" (offline, free), "claude", or "auto" (Claude when a key is set).
    narrative_provider: Literal["auto", "template", "claude"] = "auto"
    anthropic_api_key: str | None = None
    narrative_model: str = "claude-opus-5-5"


@lru_cache(maxsize=1)
def get_settings() -> ApiSettings:
    return ApiSettings()
