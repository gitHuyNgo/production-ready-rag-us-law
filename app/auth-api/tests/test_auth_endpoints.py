from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_register_and_login_and_me():
    # Register
    resp = client.post(
        "/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"

    # Login
    resp = client.post(
        "/auth/token",
        data={"username": "alice", "password": "secret123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data

    token = data["access_token"]

    # Call /me with bearer token
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    me = resp.json()
    assert me["username"] == "alice"
    assert me["email"] == "alice@example.com"

