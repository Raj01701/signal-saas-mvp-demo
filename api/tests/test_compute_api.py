"""Calculation routes: shapes, error mapping, caching, rate limiting, OpenAPI."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from jyotish_api.config import ApiSettings
from jyotish_api.main import create_app

DELHI = {"name": "New Delhi", "latitude": 28.6139, "longitude": 77.2090}
BIRTH = {"local_datetime": "1990-05-17T12:00:00", "place": DELHI}


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(ApiSettings(rate_limit="1000/minute")))


def _post(client: TestClient, path: str, body: dict[str, Any]) -> Any:
    response = client.post(path, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_chart_and_cache(client: TestClient) -> None:
    first = _post(client, "/v1/charts", {"birth": BIRTH})
    assert len(first["grahas"]) >= 9 and first["engine_version"]
    cache = client.app.state.charts  # type: ignore[attr-defined]
    hits = cache.hits
    assert _post(client, "/v1/charts", {"birth": BIRTH}) == first
    assert cache.hits == hits + 1
    kp = _post(client, "/v1/charts", {"birth": BIRTH, "preset": "kp"})
    assert kp["settings"]["ayanamsa"] != first["settings"]["ayanamsa"]


def test_chart_derived_routes(client: TestClient) -> None:
    yogas = _post(client, "/v1/charts/yogas", {"birth": BIRTH, "gender": "male"})
    assert yogas["catalogue_size"] >= 300
    assert _post(client, "/v1/charts/strengths", {"birth": BIRTH})
    readings = _post(client, "/v1/charts/readings", {"birth": BIRTH})
    assert readings["catalogue_size"] == 375 and len(readings["readings"]) == 30
    for system, key in (
        ("yogini", "table"),
        ("chara", "sign_periods"),
        ("kalachakra", "kalachakra_periods"),
    ):
        out = _post(client, "/v1/charts/dashas", {"birth": BIRTH, "system": system})
        assert out["system"] == system and out[key]
    transits = _post(
        client, "/v1/charts/transits", {"birth": BIRTH, "start": "2020-01-01", "end": "2035-01-01"}
    )
    assert transits["saturn"]["sade_sati"] and transits["double_from_moon"]
    annual = _post(client, "/v1/charts/annual", {"birth": BIRTH, "years_completed": 30})
    assert annual["varshaphal"]["years_completed"] == 30 and annual["tithi_pravesha"]["jd_ut"]
    sensitivity = _post(client, "/v1/charts/sensitivity", {"birth": BIRTH})
    assert sensitivity["factors"][0]["name"] == "Lagna"
    kp = _post(client, "/v1/charts/kp", {"birth": BIRTH})
    assert len(kp["cusps"]) == 12 and kp["ruling_planets"]


def test_other_routes(client: TestClient) -> None:
    places = client.get("/v1/geo/search", params={"q": "Varanasi", "country": "IN"}).json()
    assert places and places[0]["country_code"] == "IN"
    panchanga = _post(client, "/v1/panchanga", {"date": "2026-09-30", "place": DELHI})
    assert panchanga["calendar"]["samvatsara"] == "Parabhava"
    bride = {"local_datetime": "1993-11-02T06:30:00", "place": DELHI}
    match = _post(client, "/v1/match", {"groom": BIRTH, "bride": bride})
    assert 0 <= match["ashtakoota_total"] <= 36 and len(match["dashakoota"]) == 10
    horary = _post(
        client, "/v1/kp/horary", {"number": 111, "moment": "2026-09-30T08:00:00", "place": DELHI}
    )
    assert horary["horary_number"] == 111


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/v1/charts/dashas", {"birth": BIRTH, "system": "no-such-dasha"}),
        ("/v1/charts/transits", {"birth": BIRTH, "start": "2030-01-01", "end": "2020-01-01"}),
        ("/v1/charts", {"birth": {**BIRTH, "local_datetime": "1700-01-01T00:00:00"}}),
        ("/v1/kp/horary", {"number": 250, "moment": "2026-09-30T08:00:00", "place": DELHI}),
    ],
)
def test_bad_input_is_422(client: TestClient, path: str, body: dict[str, Any]) -> None:
    response = client.post(path, json=body)
    assert response.status_code == 422 and response.json()["detail"]


def test_rate_limit() -> None:
    limited = TestClient(create_app(ApiSettings(rate_limit="2/minute")))
    codes = [limited.get("/health").status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_openapi_schema(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    for path in ("/v1/charts", "/v1/charts/dashas", "/v1/match", "/v1/panchanga", "/v1/kp/horary"):
        assert path in schema["paths"]
