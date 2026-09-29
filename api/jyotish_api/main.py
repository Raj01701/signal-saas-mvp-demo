"""FastAPI application entry point."""

from fastapi import FastAPI

from jyotish_api import __version__ as api_version
from jyotish_engine import ENGINE_VERSION

app = FastAPI(title="Jyotish API", version=api_version)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe that also reports component versions."""
    return {"status": "ok", "api_version": api_version, "engine_version": ENGINE_VERSION}
