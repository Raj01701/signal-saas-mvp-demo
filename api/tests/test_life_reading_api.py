"""The life reading route: who you are, the past, the present and the years ahead."""

from __future__ import annotations

from fastapi.testclient import TestClient

from jyotish_api.config import ApiSettings
from jyotish_api.main import create_app

BIRTH = {
    "local_datetime": "1990-05-17T12:00:00",
    "place": {"name": "New Delhi", "latitude": 28.6139, "longitude": 77.209},
}


def test_life_reading_route() -> None:
    client = TestClient(create_app(ApiSettings(rate_limit="1000/minute")))
    body = {
        "birth": BIRTH,
        "today": "2026-09-30",
        "gender": "male",
        "name": "arjun",
        "years_ahead": 3,
    }
    reading = client.post("/v1/charts/life-reading", json=body).json()
    assert [y["year"] for y in reading["future"]] == [2026, 2027, 2028]
    assert reading["past"][-1]["current"] and reading["present"]["paragraphs"]
    assert reading["summary"][0].startswith("Arjun, you are ")
    assert reading["age"] == 36 and reading["glance"][0]["label"] == "Rising sign (Lagna)"
    too_far = {**body, "years_ahead": 11}
    assert client.post("/v1/charts/life-reading", json=too_far).status_code == 422
    before_birth = {**body, "today": "1989-01-01"}
    assert client.post("/v1/charts/life-reading", json=before_birth).status_code == 422
