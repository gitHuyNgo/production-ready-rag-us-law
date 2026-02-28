"""Minimal smoke test for API Gateway."""
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
    assert r.json().get("service") == "api-gateway"


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "api-gateway" in r.json().get("service", "")
