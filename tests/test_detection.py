from __future__ import annotations

from pathlib import Path

import db
import tools


def _init_tmp_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "test.sqlite")
    db.initialize(db_path)
    return db_path


def _audit_actions(db_path: str) -> list[str]:
    conn = db.connect(db_path)
    try:
        return [r["action"] for r in conn.execute("SELECT action FROM audit_log ORDER BY audit_id").fetchall()]
    finally:
        conn.close()


def test_discount_is_audited(tmp_path: Path) -> None:
    """Applying a discount writes a structured audit record."""
    db_path = _init_tmp_db(tmp_path)
    tools.apply_discount("cust_001", "order_001", 10, db_path=db_path)
    assert "apply_discount" in _audit_actions(db_path)


def test_profile_read_is_audited(tmp_path: Path) -> None:
    """Reading PII is sensitive and is audited too."""
    db_path = _init_tmp_db(tmp_path)
    tools.get_customer_profile("cust_001", "cust_001", db_path=db_path)
    assert "view_customer_profile" in _audit_actions(db_path)


def test_recent_action_count_flags_bursts(tmp_path: Path) -> None:
    """The anomaly signal counts an actor's recent actions for alerting."""
    db_path = _init_tmp_db(tmp_path)
    for _ in range(3):
        tools.refund_order("cust_001", "order_001", 100, db_path=db_path, approval_token="human-ok")

    conn = db.connect(db_path)
    try:
        assert db.count_recent_actions(conn, "cust_001", "refund_order") >= 3
        assert db.count_recent_actions(conn, "cust_001", "refund_order", within_seconds=0) == 0
    finally:
        conn.close()
