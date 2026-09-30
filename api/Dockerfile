# syntax=docker/dockerfile:1.7
# The API image. Build from the repository root with the pinned DE440 hash:
#
#   docker build -f api/Dockerfile --build-arg DE440_SHA256=<sha256> -t jyotish-api .
#
# docs/RUNBOOK.md explains how to obtain and pin the hash.

FROM python:3.11-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY engine/pyproject.toml engine/README.md engine/
COPY api/pyproject.toml api/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --package jyotish-api
COPY engine engine
COPY api api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package jyotish-api

FROM python:3.11-slim AS ephemeris
ARG DE440_URL=https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440.bsp
ARG DE440_SHA256
RUN <<EOF
python - "$DE440_URL" "$DE440_SHA256" <<'PY'
import hashlib, sys, urllib.request
url, expected = sys.argv[1], sys.argv[2]
if not expected:
    sys.exit("pass --build-arg DE440_SHA256=<pinned sha256> (see docs/RUNBOOK.md)")
digest = hashlib.sha256()
with urllib.request.urlopen(url) as response, open("/de440.bsp", "wb") as out:
    for block in iter(lambda: response.read(1 << 20), b""):
        digest.update(block)
        out.write(block)
if digest.hexdigest() != expected.lower():
    sys.exit(f"DE440 checksum mismatch: {digest.hexdigest()}")
print("DE440 verified")
PY
EOF

FROM python:3.11-slim
RUN useradd --create-home --uid 10001 jyotish
WORKDIR /app
COPY --from=build /app /app
COPY knowledge /app/knowledge
COPY --from=ephemeris /de440.bsp /app/data/ephemeris/de440.bsp
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    JYOTISH_DATA_DIR=/app/data/ephemeris \
    JYOTISH_KNOWLEDGE_DIR=/app/knowledge \
    JYOTISH_API_PUBLIC_DOCS=false \
    JYOTISH_API_DATABASE_TLS=verify-full
USER jyotish
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
# Behind a proxy, set JYOTISH_API_FORWARDED_HOPS (docs/RUNBOOK.md): the client address
# comes from the entries the trusted proxies appended, never from the whole header.
# Uvicorn's access log is off (it records client addresses); the API logs one JSON
# line per request instead.
CMD ["uvicorn", "jyotish_api.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--limit-concurrency", "200", "--timeout-graceful-shutdown", "20", "--no-access-log"]
