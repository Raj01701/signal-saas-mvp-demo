"""Request IDs, security headers, the body-size limit, metrics and private docs."""

from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from jyotish_api.config import ApiSettings
from jyotish_api.main import create_app
from jyotish_api.observability import logger


def _client(**settings: object) -> TestClient:
    return TestClient(create_app(ApiSettings(rate_limit="1000/minute", **settings)))  # type: ignore[arg-type]


def test_request_ids_and_security_headers() -> None:
    client = _client()
    given = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert given.headers["x-request-id"] == "abc-123"
    made = client.get("/health", headers={"X-Request-ID": "bad id with spaces"})
    assert len(made.headers["x-request-id"]) == 32
    for header, value in (
        ("x-content-type-options", "nosniff"),
        ("x-frame-options", "DENY"),
        ("cache-control", "no-store"),
    ):
        assert made.headers[header] == value


def test_large_bodies_are_refused() -> None:
    client = _client(max_body_bytes=100)
    response = client.post(
        "/v1/charts", content=b"x" * 500, headers={"content-type": "application/json"}
    )
    assert response.status_code == 413 and "larger than 100 bytes" in response.json()["detail"]


def test_metrics_count_routes_not_raw_paths() -> None:
    client = _client()
    client.get("/health")
    client.get("/v1/people/some-id")  # unauthenticated: 401, but counted under its template
    text = client.get("/metrics").text
    assert 'jyotish_requests_total{method="GET",route="/health",status="200"} 1' in text
    assert 'route="/v1/people/{person_id}"' in text and "some-id" not in text
    assert "jyotish_request_seconds_count" in text


def test_docs_and_metrics_can_be_turned_off() -> None:
    client = _client(public_docs=False, metrics_enabled=False)
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/metrics").status_code == 404


def test_streamed_bodies_are_limited_too() -> None:
    client = _client(max_body_bytes=100)
    chunks = (b"x" * 60 for _ in range(2))  # no Content-Length: sent chunked
    response = client.post(
        "/v1/charts", content=chunks, headers={"content-type": "application/json"}
    )
    assert response.status_code == 413 and "larger than 100 bytes" in response.json()["detail"]


def test_metrics_can_require_a_token() -> None:
    client = _client(metrics_token="s3cret")
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer s3cret"}).status_code == 200


def test_a_forged_forwarded_for_does_not_escape_the_limit() -> None:
    client = TestClient(create_app(ApiSettings(rate_limit="2/minute")))
    codes = [
        client.get("/health", headers={"X-Forwarded-For": f"203.0.113.{i}"}).status_code
        for i in range(3)
    ]
    assert codes == [200, 200, 429]


def test_the_client_is_read_behind_trusted_proxies() -> None:
    client = TestClient(create_app(ApiSettings(rate_limit="1/minute", forwarded_hops=1)))

    def status(forwarded: str) -> int:
        return client.get("/health", headers={"X-Forwarded-For": forwarded}).status_code

    assert status("1.1.1.1, 198.51.100.7") == 200
    assert status("2.2.2.2, 198.51.100.7") == 429  # same client, forged prefix
    assert status("1.1.1.1, 198.51.100.8") == 200  # another client
    assert status("not-an-address") == 200  # unreadable: the connecting address


class _Lines(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


def test_each_request_is_logged_as_one_json_line() -> None:
    client = _client()
    lines = _Lines()
    logger.addHandler(lines)
    try:
        client.get("/v1/people/some-id", headers={"X-Request-ID": "log-1"})
    finally:
        logger.removeHandler(lines)
    entry = json.loads(lines.lines[-1])
    assert entry["request_id"] == "log-1" and entry["route"] == "/v1/people/{person_id}"
    assert entry["status"] == 401 and entry["method"] == "GET" and entry["ms"] >= 0
