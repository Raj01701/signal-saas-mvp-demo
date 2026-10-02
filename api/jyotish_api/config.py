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
    #: A stricter limit per client for the report and chat routes (they may call a paid model).
    narrative_rate_limit: str = "60/hour"
    #: Proxies in front of the API that append the client to X-Forwarded-For (see
    #: ratelimit.py); 0 ignores the header and uses the connecting address.
    forwarded_hops: int = 0
    #: Charts kept in memory, keyed by birth data, settings and engine version.
    chart_cache_size: int = 512
    #: SQLAlchemy URL; SQLite by default, Postgres (pg8000 driver) in production.
    database_url: str = "sqlite:///./jyotish.db"
    #: TLS to Postgres, named as in libpq: "verify-full" requires TLS and checks the
    #: server's certificate and host name (against database_ca_file when set, such as
    #: Supabase's CA certificate, else the system CAs); "prefer" is the driver's default,
    #: encrypted when the server offers it but unchecked. SQLite ignores it.
    database_tls: Literal["prefer", "verify-full"] = "prefer"
    database_ca_file: str | None = None
    #: Supabase token verification: the project's JWT secret (HS256) or its JWKS URL.
    supabase_jwt_secret: str | None = None
    supabase_jwks_url: str | None = None
    supabase_audience: str = "authenticated"
    #: Narratives: "template" (offline, free), "claude", or "auto" (Claude when a key is set).
    narrative_provider: Literal["auto", "template", "claude"] = "auto"
    anthropic_api_key: str | None = None
    narrative_model: str = "claude-opus-5-5"
    #: Largest request body accepted (bytes); larger declared bodies get HTTP 413.
    max_body_bytes: int = 1_000_000
    #: Serve /docs and /openapi.json (turn off in production if the schema is private).
    public_docs: bool = True
    #: One JSON access-log line per request, and Prometheus metrics at /metrics.
    log_requests: bool = True
    metrics_enabled: bool = True
    #: When set, /metrics needs "Authorization: Bearer <token>".
    metrics_token: str | None = None
    #: Web Push reminders: the VAPID private key (base64url, from ``python -m
    #: jyotish_api.push keys``) and a contact for the push services ("mailto:..." or an
    #: https URL). Push is off unless both are set.
    vapid_private_key: str | None = None
    vapid_subject: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> ApiSettings:
    return ApiSettings()
