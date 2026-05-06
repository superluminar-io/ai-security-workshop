## Fix: Enforce Discount Limits and Ownership

The vulnerability is that the system allows applying arbitrarily large discounts (e.g., 95%–100%) without any business validation.

### Goal
Anne: isn't it weird that the customer can apply discounts to their own orders? 
- A customer may only apply discounts to their own orders.
- Discount percentage is capped at a reasonable maximum (e.g., 25%).
- Discounts above a certain threshold (e.g., 15%) require approval.

---

## Step 1: Update `discount_policy` in `policy.py`

Add validation for discount limits and ownership:

<details>
<summary>Hint 1</summary>

```python
def discount_policy(
    actor_customer_id: str,
    order_id: str,
    percent: int,
    *,
    order_customer_id: str | None = None,
) -> Decision:
    """Decide whether a discount should be allowed.

    FIXED:
    - Only the order customer can apply discounts to their own order
    - Discount percentage is capped at 25%
    - Discounts above 15% require approval (flagged for human review)
    """

    # Verify ownership
    if actor_customer_id != order_customer_id:
        return Decision(
            allowed=False,
            reason=f"Not authorized to apply discount to order {order_id}"
        )

    # Enforce maximum discount
    MAX_DISCOUNT_PERCENT = 25
    if percent > MAX_DISCOUNT_PERCENT:
        return Decision(
            allowed=False,
            reason=f"Discount {percent}% exceeds maximum allowed discount of {MAX_DISCOUNT_PERCENT}%"
        )

    # Validate non-negative
    if percent < 0:
        return Decision(
            allowed=False,
            reason="Discount percentage cannot be negative"
        )

    # Flag large discounts for approval
    APPROVAL_THRESHOLD = 15
    if percent > APPROVAL_THRESHOLD:
        return Decision(
            allowed=True,
            reason=f"Discount {percent}% approved but requires human review",
            requires_approval=True
        )

    return Decision(allowed=True, reason="Discount approved")
```

</details>

---

## Step 2: Update `apply_discount` in `tools.py`

Update the tool to fetch order details and enforce the policy:

<details>
<summary>Hint 1</summary>

```python
@tool
def apply_discount(
    actor_customer_id: str,
    order_id: str,
    percent: int,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Apply a discount percent to an order.

    FIXED: Discounts are limited to 25% and require ownership.
    """
    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute(
            "SELECT order_id, customer_id FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if not row:
            return _err(f"Unknown order_id: {order_id}")

        # Enforce the discount policy
        decision = policy.discount_policy(
            actor_customer_id,
            order_id,
            percent,
            order_customer_id=row["customer_id"],
        )

        if not decision.allowed:
            return _err(decision.reason)

        # Policy approved; apply the discount
        conn.execute(
            "UPDATE orders SET discount_percent = ? WHERE order_id = ?",
            (int(percent), order_id),
        )
        conn.commit()

        # Log with approval flag if necessary
        audit_details = {
            "order_id": order_id,
            "percent": int(percent),
            "requires_approval": decision.requires_approval,
        }
        db.audit(
            conn,
            actor_customer_id=actor_customer_id,
            action="apply_discount",
            details=audit_details,
        )

        msg = f"Applied discount {percent}% to {order_id}."
        if decision.requires_approval:
            msg += " (This discount has been flagged for human review.)"

        return _ok(msg, {"order_id": order_id, "percent": int(percent), "flagged": decision.requires_approval})
    finally:
        conn.close()
```

</details>

---

## Alternative: No Direct Discount Authority

In a more secure design, customers would not have direct discount authority at all. Instead, they could request a discount, but only a support agent could approve it. In that case, you might remove the `apply_discount` tool from the customer assistant entirely:

```python
# In app.py, when building the agent:
agent.register_tool(search_products)
agent.register_tool(list_products)
agent.register_tool(get_product_details)
agent.register_tool(get_customer_profile)
agent.register_tool(list_orders)
agent.register_tool(refund_order)
# agent.register_tool(apply_discount)  # NOT available to customers; requires support staff
```

---

## Step 3: Validate the fix

Run:

```bash
pytest tests/test_guardrails.py::test_discount_exceeds_maximum_blocked
pytest tests/test_guardrails.py::test_discount_ownership_enforced
```

---

## Teaching Points

1. **Set reasonable business limits**: Discounts are a legitimate tool, but they need guardrails. A 25% maximum is meaningful but still flexible.

2. **Tiered enforcement**: Small discounts auto-approve; large ones flag for review. This balances user experience with oversight.

3. **Ownership matters**: Like refunds and PII access, discounts should only apply to the actor's own orders.

4. **Consider the zero-trust model**: If discounts are high-risk, don't give the AI agent authority at all—require a human approval flow.

5. **Audit flags**: Use the audit log to track which discounts were flagged, creating visibility for compliance teams.
