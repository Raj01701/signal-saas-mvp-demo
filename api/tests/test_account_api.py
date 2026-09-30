"""Account routes: token checks, people and events, export and deletion, migrations."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from jyotish_api.config import ApiSettings
from jyotish_api.db import Base, make_engine
from jyotish_api.main import create_app

SECRET = "test-secret-with-enough-length-for-hs256"
BIRTH = {
    "local_datetime": "1990-05-17T12:00:00",
    "place": {"name": "New Delhi", "latitude": 28.6139, "longitude": 77.2090},
}


def _token(sub: str, secret: str = SECRET, **claims: Any) -> dict[str, str]:
    payload = {"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 600, **claims}
    return {"Authorization": f"Bearer {jwt.encode(payload, secret, algorithm='HS256')}"}


@pytest.fixture
def client() -> TestClient:
    app = create_app(
        ApiSettings(database_url="sqlite://", supabase_jwt_secret=SECRET, rate_limit="1000/minute")
    )
    Base.metadata.create_all(app.state.db)
    return TestClient(app)


def test_tokens_are_checked(client: TestClient) -> None:
    assert client.get("/v1/me").status_code == 401
    assert (
        client.get(
            "/v1/me", headers=_token("u1", secret="a-wrong-secret-that-is-long-enough-for-hs256")
        ).status_code
        == 401
    )
    expired = _token("u1", exp=int(time.time()) - 10)
    assert client.get("/v1/me", headers=expired).status_code == 401
    unconfigured = TestClient(create_app(ApiSettings(database_url="sqlite://")))
    assert unconfigured.get("/v1/me", headers=_token("u1")).status_code == 503


def test_people_events_export_and_deletion(client: TestClient) -> None:
    me = _token("user-1", email="a@example.com")
    assert client.get("/v1/me", headers=me).json() == {
        "id": "user-1", "email": "a@example.com", "research_consent": False, "people": 0,
    }  # fmt: skip
    assert client.put("/v1/me", json={"research_consent": True}, headers=me).json()[
        "research_consent"
    ]

    person = client.post("/v1/people", json={"name": "Asha", "birth": BIRTH}, headers=me).json()
    minor = {"name": "Child", "birth": BIRTH, "is_minor": True}
    assert client.post("/v1/people", json=minor, headers=me).status_code == 422
    assert (
        client.post("/v1/people", json={**minor, "guardian_consent": True}, headers=me).status_code
        == 201
    )
    renamed = client.put(
        f"/v1/people/{person['id']}", json={"name": "Asha K", "birth": BIRTH}, headers=me
    )
    assert renamed.json()["name"] == "Asha K"
    assert [p["name"] for p in client.get("/v1/people", headers=me).json()] == ["Asha K", "Child"]

    base = f"/v1/people/{person['id']}/events"
    for day, kind in (("2015-02-01", "marriage"), ("2012-07-01", "job")):
        assert client.post(base, json={"kind": kind, "date": day}, headers=me).status_code == 201
    assert (
        client.post(base, json={"kind": "lottery", "date": "2020-01-01"}, headers=me).status_code
        == 422
    )
    events = client.get(base, headers=me).json()
    assert [e["kind"] for e in events] == ["job", "marriage"]
    assert client.delete(f"{base}/{events[0]['id']}", headers=me).status_code == 204

    chart = client.post(f"/v1/people/{person['id']}/chart", json={}, headers=me)
    assert chart.status_code == 200 and chart.json()["birth"]["local_datetime"].startswith(
        "1990-05-17"
    )

    assert client.post(base, json={"kind": "child_birth", "date": "2018-03-01"}, headers=me)
    rectified = client.post(
        f"/v1/people/{person['id']}/rectify",
        json={"uncertainty_minutes": 20, "step_seconds": 60},
        headers=me,
    ).json()
    assert len(rectified["candidates"]) >= 2 and len(rectified["scan"]) == 41

    other = _token("user-2")
    assert client.get(f"/v1/people/{person['id']}", headers=other).status_code == 404
    assert client.get(base, headers=other).status_code == 404

    export = client.get("/v1/me/export", headers=me).json()
    assert export["me"]["people"] == 2 and len(export["events"][person["id"]]) == 2

    assert client.delete("/v1/me", headers=me).status_code == 204
    assert client.get("/v1/me", headers=me).json()["people"] == 0  # a fresh, empty account
    assert client.get(f"/v1/people/{person['id']}", headers=me).status_code == 404


def test_migrations_match_the_models(tmp_path: Path) -> None:
    config = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path / 'test.db'}")
    command.upgrade(config, "head")
    command.check(config)  # raises if the models and the migrations differ


@pytest.mark.skipif(
    not os.environ.get("JYOTISH_API_TEST_POSTGRES_URL"),
    reason="set JYOTISH_API_TEST_POSTGRES_URL (postgresql+pg8000://...) to run against Postgres",
)
def test_postgres_round_trip() -> None:
    url = os.environ["JYOTISH_API_TEST_POSTGRES_URL"]
    config = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    command.check(config)
    with make_engine(url).connect() as connection:  # Supabase's REST roles see nothing
        rows = connection.exec_driver_sql(
            "SELECT relname, relrowsecurity FROM pg_class WHERE relname IN ('users', 'people', "
            "'life_events', 'push_subscriptions', 'push_reminders', 'alembic_version')"
        ).all()
    assert len(rows) == 6 and all(secured for _, secured in rows)
    client = TestClient(create_app(ApiSettings(database_url=url, supabase_jwt_secret=SECRET)))
    me = _token(f"pg-{time.time_ns()}")
    person = client.post("/v1/people", json={"name": "Asha", "birth": BIRTH}, headers=me).json()
    assert client.get(f"/v1/people/{person['id']}", headers=me).status_code == 200
    assert client.delete("/v1/me", headers=me).status_code == 204
