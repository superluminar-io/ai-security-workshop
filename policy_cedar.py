"""Module 6: externalize authorization to Cedar.

Authorization is expressed as *data* -- declarative Cedar policy, evaluated by an
engine, outside both the model and the application's business code. `policy.py`
delegates its ownership / data-access decisions here. The same idea maps to
OPA/Rego, OpenFGA/Zanzibar, and Oso, so this is not AWS lock-in: Cedar is open
source and runs standalone (Amazon Verified Permissions is just the managed
service around it).
"""

from __future__ import annotations

from pathlib import Path

POLICIES = (Path(__file__).parent / "cedar" / "policies.cedar").read_text()

_ACTION = {
    "refund_order": 'Action::"refundOrder"',
    "apply_discount": 'Action::"applyDiscount"',
    "view_customer_profile": 'Action::"viewCustomerData"',
    "list_orders": 'Action::"viewCustomerData"',
}


def _is_allow(result) -> bool:
    """Robust to cedarpy returning a Decision enum or a plain string."""
    decision = getattr(result, "decision", result)
    return str(decision).split(".")[-1].strip().lower() == "allow"


def _authorize(request: dict, entities: list) -> bool:
    from cedarpy import is_authorized

    return _is_allow(is_authorized(request, POLICIES, entities))


def order_action_allowed(actor_id: str, action: str, order_id: str, owner_id: str) -> bool:
    """Is `actor_id` allowed to perform `action` on order `order_id` owned by `owner_id`?"""
    request = {
        "principal": f'Customer::"{actor_id}"',
        "action": _ACTION[action],
        "resource": f'Order::"{order_id}"',
        "context": {},
    }
    entities = [
        {"uid": {"type": "Customer", "id": actor_id}, "attrs": {}, "parents": []},
        {
            "uid": {"type": "Order", "id": order_id},
            "attrs": {"owner": {"__entity": {"type": "Customer", "id": owner_id}}},
            "parents": [],
        },
    ]
    return _authorize(request, entities)


def customer_data_allowed(actor_id: str, customer_id: str) -> bool:
    """Is `actor_id` allowed to view customer data for `customer_id`?"""
    request = {
        "principal": f'Customer::"{actor_id}"',
        "action": 'Action::"viewCustomerData"',
        "resource": f'Customer::"{customer_id}"',
        "context": {},
    }
    entities = [
        {"uid": {"type": "Customer", "id": actor_id}, "attrs": {}, "parents": []},
        {"uid": {"type": "Customer", "id": customer_id}, "attrs": {}, "parents": []},
    ]
    return _authorize(request, entities)
