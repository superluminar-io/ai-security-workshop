from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import db
import tools

if TYPE_CHECKING:
    from strands.types.tools import ToolContext


def _init_tmp_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "test.sqlite")
    db.initialize(db_path)
    return db_path


class _Session:
    """Stand-in for the Strands ToolContext.

    Only `invocation_state` matters here: it is how the application threads
    trusted session facts (the authenticated actor, the db path) into a tool.
    The real object is constructed by the SDK; the wrapper only reads
    `.invocation_state`, so a plain object is enough to test the boundary.
    """

    def __init__(self, **invocation_state: object) -> None:
        self.invocation_state = invocation_state


IDENTITY_TOOLS = [
    tools.get_customer_profile_tool,
    tools.list_orders_tool,
    tools.refund_order_tool,
    tools.apply_discount_tool,
    tools.send_email_tool,
]


def _props(decorated_tool: Any) -> dict:
    return decorated_tool.tool_spec["inputSchema"]["json"].get("properties", {})


def test_model_cannot_supply_actor_identity() -> None:
    """The LLM-facing tools must expose no way to set the actor identity.

    Identity is bound from the session; the model proposes intent only. If an
    actor field appeared in any tool schema, the model -- or a prompt injection
    riding in untrusted content -- could assert a different identity. This holds
    for every possible model output, which is the whole point: it is a property
    of the interface, not of the model's behavior.
    """
    for decorated_tool in IDENTITY_TOOLS:
        props = _props(decorated_tool)
        assert "actor_customer_id" not in props
        assert "actor_id" not in props


def test_tool_fails_closed_without_session() -> None:
    """With no authenticated actor in the session, identity-bearing tools refuse."""
    ctx = cast("ToolContext", _Session())  # no actor_customer_id
    res = tools.refund_order_tool("order_001", 100, tool_context=ctx)
    assert res["status"] == "error"


def test_wrapper_forwards_session_actor(monkeypatch) -> None:
    """The wrapper passes the session actor -- and nothing else -- as identity.

    We capture what the trusted core receives. The model only ever provided the
    business parameters (order_id, refund_cents); the actor comes from the
    session. There is no channel through which the model could substitute a
    different one.
    """
    captured: dict[str, object] = {}

    def fake_core(actor_customer_id, order_id, refund_cents, *, db_path=None, approval_token=None):
        captured["actor"] = actor_customer_id
        captured["order_id"] = order_id
        return tools._ok("ok")

    monkeypatch.setattr(tools, "refund_order", fake_core)

    ctx = cast("ToolContext", _Session(actor_customer_id="cust_001", db_path="unused"))
    tools.refund_order_tool("order_002", 100, tool_context=ctx)

    assert captured["actor"] == "cust_001"
    assert captured["order_id"] == "order_002"
