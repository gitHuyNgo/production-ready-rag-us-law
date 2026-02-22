import json
from http import HTTPStatus

from fastapi.testclient import TestClient

from src.dtos.chat_dto import ChatDto, ChatMessageDto, Role


def test_health_endpoint_reports_online(test_client: TestClient):
    resp = test_client.get("/health/")

    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["status"] == "online"
    # Database may or may not be connected; just ensure key exists
    assert "database" in data


def test_chat_endpoint_websocket(test_client: TestClient):
    dto = ChatDto(
        history=[ChatMessageDto(role=Role.user, content="Hi")],
        role=Role.user,
        content="What is contract law?",
    )

    with test_client.websocket_connect("/chat/") as websocket:
        websocket.send_text(json.dumps(dto.model_dump()))
        payload = None
        while True:
            raw = websocket.receive_text()
            msg = json.loads(raw)
            if msg.get("t") == "error":
                raise AssertionError(f"Server error: {msg.get('error')}")
            if msg.get("t") == "done":
                payload = msg
                break

    assert payload is not None
    assert payload["received_role"] == "assistant"
    assert isinstance(payload["received_content"], str)
    assert "ANSWER to" in payload["received_content"]
    assert payload["history_length"] == len(dto.history)

def test_chat_endpoint_post(test_client: TestClient):
    dto = ChatDto(
        history=[ChatMessageDto(role=Role.user, content="Hi")],
        role=Role.user,
        content="What is contract law?",
    )

    resp = test_client.post("/chat/", json=dto.model_dump())

    assert resp.status_code == HTTPStatus.OK
    payload = resp.json()
    
    assert payload["received_role"] == "assistant"
    assert isinstance(payload["received_content"], str)
    assert "ANSWER to" in payload["received_content"]
    assert payload["history_length"] == len(dto.history)