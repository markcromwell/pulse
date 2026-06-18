# Unit tests for PULSE. Uses the app factory for an isolated instance.
from fastapi.testclient import TestClient

from app import create_app

client = TestClient(create_app())


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
