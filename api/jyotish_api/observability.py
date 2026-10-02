"""Request IDs, JSON access logs, security headers, a body-size limit and metrics.

A pure ASGI middleware (it does not buffer responses) that, for every HTTP request:

- takes the caller's ``X-Request-ID`` when it is short and plain, or makes one, and
  returns it;
- refuses bodies larger than the limit (HTTP 413): at once when the declared length
  is too large, and while reading when a streamed (chunked) body grows past it;
- adds security headers suited to a JSON API (no sniffing, no framing, no referrer,
  and no caching, since responses carry birth data);
- logs one JSON line (method, route, status, milliseconds, request ID) and counts
  requests and latency per route for ``/metrics`` in the Prometheus text format.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from collections import defaultdict
from typing import Any

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("jyotish_api.access")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cache-control", b"no-store"),
]


class Metrics:
    """Request counts and latency sums per method, route and status."""

    def __init__(self) -> None:
        self.requests: dict[tuple[str, str, int], int] = defaultdict(int)
        self.seconds: dict[tuple[str, str], float] = defaultdict(float)
        self.observed: dict[tuple[str, str], int] = defaultdict(int)

    def observe(self, method: str, route: str, status: int, seconds: float) -> None:
        self.requests[(method, route, status)] += 1
        self.seconds[(method, route)] += seconds
        self.observed[(method, route)] += 1

    def render(self) -> str:
        lines = [
            "# HELP jyotish_requests_total HTTP requests by method, route and status.",
            "# TYPE jyotish_requests_total counter",
        ]
        for (method, route, status), count in sorted(self.requests.items()):
            labels = f'method="{method}",route="{route}",status="{status}"'
            lines.append(f"jyotish_requests_total{{{labels}}} {count}")
        lines += [
            "# HELP jyotish_request_seconds HTTP request latency by method and route.",
            "# TYPE jyotish_request_seconds summary",
        ]
        for (method, route), total in sorted(self.seconds.items()):
            labels = f'method="{method}",route="{route}"'
            lines.append(f"jyotish_request_seconds_sum{{{labels}}} {total:.6f}")
            lines.append(
                f"jyotish_request_seconds_count{{{labels}}} {self.observed[(method, route)]}"
            )
        return "\n".join(lines) + "\n"


def _route(scope: Scope) -> str:
    """The matched route's template, so metrics stay bounded (no IDs in paths)."""
    route: Any = scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "unmatched"


def _log_to_stdout() -> None:
    """Uvicorn configures only its own loggers, so ours gets a handler of its own (once);
    without it the access lines would fall below the root logger's WARNING level."""
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False


class ObservabilityMiddleware:
    def __init__(
        self, app: ASGIApp, metrics: Metrics, max_body_bytes: int, log_requests: bool = True
    ) -> None:
        self.app = app
        self.metrics = metrics
        self.max_body_bytes = max_body_bytes
        self.log_requests = log_requests
        if log_requests:
            _log_to_stdout()
        self.too_large = f"request body larger than {max_body_bytes} bytes"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])
        }
        given = headers.get("x-request-id", "")
        request_id = given if _REQUEST_ID.match(given) else uuid.uuid4().hex
        started = time.perf_counter()
        status = 500

        async def reply(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                extra = [(b"x-request-id", request_id.encode()), *SECURITY_HEADERS]
                message["headers"] = [*message.get("headers", []), *extra]
            await send(message)

        received = 0

        async def limited() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise HTTPException(413, self.too_large)
            return message

        try:
            length = int(headers.get("content-length", "0") or "0")
        except ValueError:
            length = 0
        try:
            if length > self.max_body_bytes:
                body = json.dumps({"detail": self.too_large}).encode()
                await reply(
                    {
                        "type": "http.response.start",
                        "status": 413,
                        "headers": [(b"content-type", b"application/json")],
                    }
                )
                await send({"type": "http.response.body", "body": body})
            else:
                await self.app(scope, limited, reply)
        finally:
            seconds = time.perf_counter() - started
            route = _route(scope)
            self.metrics.observe(scope["method"], route, status, seconds)
            if self.log_requests:
                logger.info(
                    json.dumps(
                        {
                            "request_id": request_id,
                            "method": scope["method"],
                            "route": route,
                            "status": status,
                            "ms": round(seconds * 1000, 1),
                        }
                    )
                )
