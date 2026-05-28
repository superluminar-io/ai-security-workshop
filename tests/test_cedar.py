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


def test_policy_layer_is_cedar_backed() -> None:
    """The live policy decisions are driven by the Cedar engine: a non-owner is
    denied, the owner is allowed (then subject to HITL/caps)."""
    assert policy.refund_policy("cust_001", "order_x", 100, order_customer_id="cust_002").allowed is False
    owner = policy.refund_policy("cust_001", "order_x", 100, order_customer_id="cust_001", order_total_cents=1000)
    assert owner.allowed is True
    assert owner.requires_approval is True
