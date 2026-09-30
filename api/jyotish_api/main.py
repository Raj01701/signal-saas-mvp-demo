"""FastAPI application: calculation routes and account routes under ``/v1``."""

from __future__ import annotations

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from jyotish_api import __version__ as api_version
from jyotish_api.charts import ChartCache
from jyotish_api.config import ApiSettings, get_settings
from jyotish_api.db import make_engine, session_factory
from jyotish_api.routers import account, compute, narrative
from jyotish_engine import ENGINE_VERSION
from jyotish_engine.place.geocode import gazetteer


def _value_error(_: Request, exc: Exception) -> JSONResponse:
    """Engine errors about the input (dates outside the ephemeris, polar days,
    unknown options) are the caller's to fix."""
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load the place gazetteer (about 10 s) in the background at startup, so the
    first place search does not wait for it."""
    app.state.warmup = threading.Thread(target=gazetteer, name="gazetteer", daemon=True)
    app.state.warmup.start()
    yield


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        lifespan=_lifespan,
        title="Jyotish API",
        version=api_version,
        description="Vedic astrology calculations with cited, explainable results.",
    )
    app.state.settings = settings
    app.state.charts = ChartCache(settings.chart_cache_size)
    app.state.db = make_engine(settings.database_url)
    app.state.sessions = session_factory(app.state.db)
    app.state.limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValueError, _value_error)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness probe that also reports component versions."""
        return {"status": "ok", "api_version": api_version, "engine_version": ENGINE_VERSION}

    @app.get("/ready")
    def ready() -> JSONResponse:
        """200 once startup work (the gazetteer) is done, 503 before."""
        warmup = getattr(app.state, "warmup", None)
        loading = warmup is not None and warmup.is_alive()
        return JSONResponse(status_code=503 if loading else 200, content={"ready": not loading})

    app.include_router(compute.router)
    app.include_router(account.router)
    app.include_router(narrative.router)
    return app


app = create_app()
