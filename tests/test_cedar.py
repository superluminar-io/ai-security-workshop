from __future__ import annotations

import policy
import policy_cedar


def test_owner_can_act_on_own_order() -> None:
    assert policy_cedar.order_action_allowed("cust_001", "refund_order", "order_001", "cust_001") is True
    assert policy_cedar.order_action_allowed("cust_001", "apply_discount", "order_001", "cust_001") is True


def test_non_owner_cannot_act_on_order() -> None:
    assert policy_cedar.order_action_allowed("cust_001", "refund_order", "order_002", "cust_002") is False


def test_customer_data_scoped_to_self() -> None:
    assert policy_cedar.customer_data_allowed("cust_001", "cust_001") is True
    assert policy_cedar.customer_data_allowed("cust_001", "cust_002") is False


def test_policy_layer_is_cedar_backed(monkeypatch) -> None:
    """policy.py must DELEGATE to the Cedar engine, not re-implement the rules.

    We force the engine to deny everything. Hand-rolled ownership code would still
    allow the owner, so these assertions pass only if policy.py actually consults
    Cedar. This is what makes Module 6 load-bearing rather than a side demo.
    """
    monkeypatch.setattr(policy_cedar, "order_action_allowed", lambda *a, **k: False)
    monkeypatch.setattr(policy_cedar, "customer_data_allowed", lambda *a, **k: False)

    refund = policy.refund_policy(
        "cust_001", "order_001", 100, order_customer_id="cust_001", order_total_cents=1000
    )
    assert refund.allowed is False  # owner; only Cedar-delegation can deny this
    assert policy.can_access_customer_data("cust_001", "cust_001").allowed is False
