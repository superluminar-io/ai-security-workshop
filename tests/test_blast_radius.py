from __future__ import annotations

from pathlib import Path

import db
import tools

# Module 5 targets. These encode blast-radius limits -- ordinary appsec hygiene
# that bounds the damage of an action that already cleared identity (Module 2),
# authorization, and approval (Module 3). They are EXPECTED TO FAIL until Module
# 5 adds the caps. Each test pre-satisfies the earlier layers (own order,
# approval token) so that the only thing left to fail on is the cap itself.


def _init_tmp_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "test.sqlite")
    db.initialize(db_path)
    return db_path


def test_refund_exceeds_order_total_blocked(tmp_path: Path) -> None:
    """A refund larger than the order total must be rejected (order_001 = 2500)."""
    db_path = _init_tmp_db(tmp_path)
    res = tools.refund_order("cust_001", "order_001", 999_999, db_path=db_path, approval_token="human-ok")
    assert res["status"] == "error"


def test_discount_exceeds_maximum_blocked(tmp_path: Path) -> None:
    """A discount above the allowed maximum must be rejected."""
    db_path = _init_tmp_db(tmp_path)
    res = tools.apply_discount("cust_001", "order_001", 90, db_path=db_path)
    assert res["status"] == "error"
    assert any(word in res["content"][0]["text"].lower() for word in ["exceed", "maximum", "limit", "cap"])
