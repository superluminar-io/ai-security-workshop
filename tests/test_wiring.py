from __future__ import annotations

from pathlib import Path

import db
from agent_setup import build_agent
from scripted_model import ScriptedModel


def _init_tmp_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "test.sqlite")
    db.initialize(db_path)
    return db_path


def _refunded(db_path: str, order_id: str) -> int:
    conn = db.connect(db_path)
    try:
        row = conn.execute("SELECT refunded_cents FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        return int(row["refunded_cents"]) if row else -1
    finally:
        conn.close()


def test_boundary_is_enabled_in_the_request_path(tmp_path: Path) -> None:
    """Drive the REAL agent (tool registration + invocation_state) with a model
    that emits a hostile tool call: logged in as cust_001, refund cust_002's order.

    This checks the deterministic boundary is wired into the live request path,
    not merely present in the cores: a mis-wired agent (registering a core instead
    of a wrapper, or not binding the session) would let the refund through here
    even if the unit tests pass.

    RED until identity + authorization are enabled (Modules 2-3); GREEN once they
    are. It is an ENABLEMENT check (is the control in the path?), not a safety
    certificate.
    """
    db_path = _init_tmp_db(tmp_path)
    agent = build_agent(
        model=ScriptedModel([("refund_order", {"order_id": "order_002", "refund_cents": 100})])
    )
    agent("hello", invocation_state={"actor_customer_id": "cust_001", "db_path": db_path})

    # order_002 belongs to cust_002. A boundary in the path refuses the refund.
    assert _refunded(db_path, "order_002") == 0
