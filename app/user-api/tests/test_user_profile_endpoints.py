from pathlib import Path

from fastapi.testclient import TestClient
from jose import jwt

from src.main import app, settings


client = TestClient(app)

_TEST_PRIVATE_KEY_PATH = Path(__file__).resolve().parent / "fixtures" / "rsa_private.pem"


def _make_token(sub: str) -> str:
    """Build a JWT signed with test RS256 private key (public key in app config)."""
    from datetime import datetime, timedelta

    private_pem = _TEST_PRIVATE_KEY_PATH.read_text() if _TEST_PRIVATE_KEY_PATH.is_file() else ""
    if not private_pem:
        raise RuntimeError("Test fixture rsa_private.pem not found; run key generation script.")
    payload = {"sub": sub, "exp": datetime.now() + timedelta(minutes=5)}
    return jwt.encode(payload, private_pem, algorithm=settings.JWT_ALGORITHM)


def test_get_and_update_profile(monkeypatch):
    # Use an in-memory dict instead of real Mongo for the test
    fake_store: dict[str, dict] = {}

    def fake_find_one(query):
        return fake_store.get(query["user_id"])

    def fake_update_one(query, update, upsert=False):
        user_id = query["user_id"]
        data = update["$set"]
        data["user_id"] = user_id
        fake_store[user_id] = data

    from src.service import profile_service

    monkeypatch.setattr(profile_service, "profiles", type("P", (), {
        "find_one": staticmethod(fake_find_one),
        "update_one": staticmethod(fake_update_one),
    }))

    token = _make_token("user-123")

    # Initially profile should be mostly empty but with user_id
    resp = client.get(
        "/profiles/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user-123"

    # Update profile
    resp = client.put(
        "/profiles/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "ignored", "display_name": "Alice", "bio": "Hi"},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["user_id"] == "user-123"
    assert updated["display_name"] == "Alice"
    assert updated["bio"] == "Hi"

