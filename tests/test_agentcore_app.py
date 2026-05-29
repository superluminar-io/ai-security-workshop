from __future__ import annotations


def test_handle_extracts_prompt_and_returns_text(monkeypatch):
    """_handle must pass payload['prompt'] to the agent and surface the text response."""
    import agentcore_app

    class FakeResult:
        message = {"content": [{"text": "Your orders: order_001."}]}

    monkeypatch.setattr(agentcore_app, "_agent", lambda msg, **kw: FakeResult())

    result = agentcore_app._handle({"prompt": "show my orders", "actorCustomerId": "cust_001"})

    assert result["result"] == "Your orders: order_001."


def test_handle_uses_actor_customer_id_from_payload(monkeypatch):
    """_handle must pass actorCustomerId from payload into invocation_state."""
    import agentcore_app

    captured: dict = {}

    class FakeResult:
        message = {"content": [{"text": "ok"}]}

    def fake_agent(msg, **kw):
        captured.update(kw.get("invocation_state", {}))
        return FakeResult()

    monkeypatch.setattr(agentcore_app, "_agent", fake_agent)
    agentcore_app._handle({"prompt": "hello", "actorCustomerId": "cust_002"})

    assert captured["actor_customer_id"] == "cust_002"


def test_handle_defaults_actor_when_missing(monkeypatch):
    """_handle must default actorCustomerId to cust_001 when not in payload."""
    import agentcore_app

    captured: dict = {}

    class FakeResult:
        message = {"content": [{"text": "ok"}]}

    def fake_agent(msg, **kw):
        captured.update(kw.get("invocation_state", {}))
        return FakeResult()

    monkeypatch.setattr(agentcore_app, "_agent", fake_agent)
    agentcore_app._handle({"prompt": "hello"})

    assert captured["actor_customer_id"] == "cust_001"
