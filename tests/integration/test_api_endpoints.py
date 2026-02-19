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


def test_chat_endpoint_returns_assistant_message(test_client: TestClient):
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