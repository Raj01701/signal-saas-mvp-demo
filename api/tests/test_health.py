from fastapi.testclient import TestClient

from jyotish_api.main import app


def test_health_reports_versions() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["engine_version"]
