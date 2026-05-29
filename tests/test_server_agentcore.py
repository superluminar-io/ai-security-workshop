from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def flask_client(monkeypatch):
    monkeypatch.setenv(
        "AGENTCORE_RUNTIME_ARN",
        "arn:aws:bedrock-agentcore:eu-central-1:123456789012:runtime/test-abc123",
    )
    import server

    server.app.config["TESTING"] = True
    server.app.config["SECRET_KEY"] = "test-secret"
    with server.app.test_client() as c:
        yield c


class _FakeStreamingBody:
    def __init__(self, data: dict):
        self._bytes = json.dumps(data).encode()

    def read(self):
        return self._bytes


def _mock_client(response_text: str) -> MagicMock:
    mock = MagicMock()
    mock.invoke_agent_runtime.return_value = {
        "response": _FakeStreamingBody({"result": response_text})
    }
    return mock


def test_chat_returns_agent_response(flask_client, monkeypatch):
    """POST /api/chat should return the text from the AgentCore runtime."""
    import server

    monkeypatch.setattr(server, "_agentcore_client", _mock_client("Hello from the agent!"))

    resp = flask_client.post("/api/chat", json={"message": "hi"})

    assert resp.status_code == 200
    assert resp.get_json()["response"] == "Hello from the agent!"


def test_chat_passes_session_id_on_second_call(flask_client, monkeypatch):
    """Second request in same session must pass the same runtimeSessionId."""
    import server

    mock = _mock_client("ok")
    monkeypatch.setattr(server, "_agentcore_client", mock)

    with flask_client.session_transaction() as sess:
        pass  # open session so Flask creates it

    flask_client.post("/api/chat", json={"message": "first"})
    flask_client.post("/api/chat", json={"message": "second"})

    calls = mock.invoke_agent_runtime.call_args_list
    assert len(calls) == 2
    first_session = calls[0].kwargs["runtimeSessionId"]
    second_session = calls[1].kwargs["runtimeSessionId"]
    assert first_session == second_session  # same session across requests


def test_chat_empty_message_returns_400(flask_client):
    """Empty message must be rejected without calling the AgentCore runtime."""
    resp = flask_client.post("/api/chat", json={"message": ""})
    assert resp.status_code == 400


def test_health_endpoint(flask_client):
    """GET /api/health must return status ok."""
    resp = flask_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
