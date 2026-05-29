# Solution: Authorization as policy, evaluated by an engine

## The policy (`cedar/policies.cedar`)

```cedar
permit (
    principal,
    action in [Action::"refundOrder", Action::"applyDiscount"],
    resource
)
when { resource has owner && resource.owner == principal };

permit (
    principal,
    action == Action::"viewCustomerData",
    resource
)
when { principal == resource };
```

Cedar is default-deny: anything not explicitly permitted is denied.

## The integration (`policy_cedar.py`)

Each decision becomes a request (principal / action / resource / context) plus
the entities involved and their attributes:

```python
def order_action_allowed(actor_id, action, order_id, owner_id) -> bool:
    request = {
        "principal": f'Customer::"{actor_id}"',
        "action": _ACTION[action],
        "resource": f'Order::"{order_id}"',
        "context": {},
    }
    entities = [
        {"uid": {"type": "Customer", "id": actor_id}, "attrs": {}, "parents": []},
        {"uid": {"type": "Order", "id": order_id},
         "attrs": {"owner": {"__entity": {"type": "Customer", "id": owner_id}}},
         "parents": []},
    ]
    return _authorize(request, entities)   # is_authorized(...).decision == Allow
```

## Wire it into the live path (`policy.py`)

`policy.py` delegates its ownership / data-access checks to the engine. The HITL
approval, email allowlist, and caps stay as code (they could also become Cedar
`context` conditions):

```python
import policy_cedar

def can_access_customer_data(actor_customer_id, customer_id):
    if not policy_cedar.customer_data_allowed(actor_customer_id, customer_id):
        return _deny("Access denied: you can only access your own account data.")
    return Decision(allowed=True)

def refund_policy(actor_customer_id, order_id, refund_cents, *, order_customer_id=None, order_total_cents=None):
    if not policy_cedar.order_action_allowed(actor_customer_id, "refund_order", order_id, order_customer_id):
        return _deny(f"Not authorized to refund order {order_id}.")
    # ... cap (Module 5) and HITL approval (Module 3) stay here ...
```

## Validate

```bash
pytest tests/test_cedar.py -q          # the Cedar engine directly
pytest tests/test_authorization.py -q  # the same ownership/scoping checks, now Cedar-backed
```

`tests/test_authorization.py` is the real proof: those ownership and PII-scoping
tests now pass *through* Cedar, the engine is load-bearing, not a side demo.

## Teaching Points

1. **Authorization is data.** Expressing it as policy makes it reviewable,
   versionable, and changeable without touching application logic.
2. **The engine is interchangeable.** Cedar, OPA/Rego, OpenFGA, Oso, same
   shape. Picking one is not a lock-in decision about the *pattern*.
3. **Position unchanged.** It is still a deterministic Layer-1 decision outside
   the model. We moved where the rule lives, not what protects you.
