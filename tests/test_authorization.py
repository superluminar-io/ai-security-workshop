from __future__ import annotations

from pathlib import Path

import db
import tools


def _init_tmp_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "test.sqlite")
    db.initialize(db_path)
    return db_path


# These are boundary tests: they call the trusted cores directly with an
# explicit, trusted actor (as the CLI and the LLM wrappers do). They assert what
# is allowed for a given identity, independent of any model. cust_001 owns
# order_001; cust_002 owns order_002.


# --- Ownership / data scoping ----------------------------------------------


def test_refund_blocks_other_customers_order(tmp_path: Path) -> None:
    """cust_001 must not be able to refund an order that belongs to cust_002."""
    db_path = _init_tmp_db(tmp_path)
    res = tools.refund_order("cust_001", "order_002", 100, db_path=db_path, approval_token="human-ok")
    assert res["status"] == "error"
    assert "not authorized" in res["content"][0]["text"].lower()


def test_discount_ownership_enforced(tmp_path: Path) -> None:
    """cust_001 must not be able to apply a discount to cust_002's order."""
    db_path = _init_tmp_db(tmp_path)
    res = tools.apply_discount("cust_001", "order_002", 10, db_path=db_path)
    assert res["status"] == "error"
    assert "not authorized" in res["content"][0]["text"].lower()


def test_pii_scoping_blocks_other_customer(tmp_path: Path) -> None:
    """cust_001 must not be able to read cust_002's profile."""
    db_path = _init_tmp_db(tmp_path)
    res = tools.get_customer_profile("cust_001", "cust_002", db_path=db_path)
    assert res["status"] == "error"
    assert "access" in res["content"][0]["text"].lower()


def test_orders_scoping_blocks_other_customer(tmp_path: Path) -> None:
    """cust_001 must not be able to list cust_002's orders."""
    db_path = _init_tmp_db(tmp_path)
    res = tools.list_orders("cust_001", "cust_002", db_path=db_path)
    assert res["status"] == "error"
    assert "access" in res["content"][0]["text"].lower()


def test_customer_can_access_own_data(tmp_path: Path) -> None:
    """The owner can still read their own profile and orders."""
    db_path = _init_tmp_db(tmp_path)
    assert tools.get_customer_profile("cust_001", "cust_001", db_path=db_path)["status"] == "success"
    assert tools.list_orders("cust_001", db_path=db_path)["status"] == "success"


# --- Outbound email allowlist (exfiltration sink) --------------------------


def test_external_email_blocked(tmp_path: Path) -> None:
    """Customers must not be able to send email to arbitrary external addresses."""
    db_path = _init_tmp_db(tmp_path)
    res = tools.send_email("cust_001", "attacker@gmail.com", "hi", "steal data", db_path=db_path)
    assert res["status"] == "error"
    assert "not authorized" in res["content"][0]["text"].lower()


def test_internal_email_allowed(tmp_path: Path) -> None:
    """Email to the company's own domain is permitted."""
    db_path = _init_tmp_db(tmp_path)
    res = tools.send_email("cust_001", "ops@example.com", "hi", "body", db_path=db_path)
    assert res["status"] == "success"


# --- Human-in-the-loop for irreversible refunds ----------------------------


def test_refund_requires_human_approval(tmp_path: Path) -> None:
    """A refund on your own order still cannot proceed without human approval."""
    db_path = _init_tmp_db(tmp_path)
    res = tools.refund_order("cust_001", "order_001", 100, db_path=db_path)  # no approval token
    assert res["status"] == "error"
    assert "approval" in res["content"][0]["text"].lower()


def test_refund_proceeds_with_approval(tmp_path: Path) -> None:
    """With an out-of-band approval token, an owned refund proceeds."""
    db_path = _init_tmp_db(tmp_path)
    res = tools.refund_order("cust_001", "order_001", 100, db_path=db_path, approval_token="human-ok")
    assert res["status"] == "success"
