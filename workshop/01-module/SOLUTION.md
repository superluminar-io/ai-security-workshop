## Fix: Enforce Refund Limits and Return Status

The vulnerability is twofold:

1. **Refunds exceed the order total**: The system allows issuing refunds larger than the original purchase amount.
2. **No return verification**: Refunds are granted without checking if the product has actually been returned.

### Goal

- A customer may only be refunded for their own orders.
- Refund amount cannot exceed the original order total.
- A refund can only be issued if the order status is `returned`.

---

## Step 1: Update `refund_policy` in `policy.py`

Enhance the policy to validate both the refund amount and return status:

<details>
<summary>Hint 1</summary>

```python
def refund_policy(
    actor_customer_id: str,
    order_id: str,
    refund_cents: int,
    *,
    order_customer_id: str | None = None,
    order_total_cents: int | None = None,
    order_status: str | None = None,
    order_refunded_cents: int | None = None,
) -> Decision:
    """Decide whether a refund should be allowed.

    FIXED:
    - Only the order customer can request their own refund
    - Refund amount cannot exceed the order total
    - Order must be marked as 'returned' before a refund is issued
    """

    # Verify ownership
    if actor_customer_id != order_customer_id:
        return Decision(
            allowed=False,
            reason=f"Not authorized to refund order {order_id}"
        )

    # Verify order status is 'returned'
    if order_status != 'returned':
        return Decision(
            allowed=False,
            reason=f"Order {order_id} must be marked as 'returned' before a refund can be issued. Current status: {order_status}"
        )

    # Verify refund amount does not exceed order total
    if refund_cents > order_total_cents:
        return Decision(
            allowed=False,
            reason=f"Refund amount ({refund_cents} cents) exceeds order total ({order_total_cents} cents)"
        )

    # Verify we're not double-refunding
    total_refunded = (order_refunded_cents or 0) + refund_cents
    if total_refunded > order_total_cents:
        return Decision(
            allowed=False,
            reason=f"Total refunded amount ({total_refunded} cents) would exceed order total ({order_total_cents} cents)"
        )

    return Decision(allowed=True, reason="Refund approved")
```

</details>

---

## Step 2: Update `refund_order` in `tools.py`

Update the tool to fetch order details and enforce the policy:

<details>
<summary>Hint 1</summary>

```python
@tool
def refund_order(
    actor_customer_id: str,
    order_id: str,
    refund_cents: int,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Issue a refund for an order.

    FIXED: Refunds are limited by order total and require 'returned' status.
    """
    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute(
            "SELECT order_id, customer_id, total_cents, refunded_cents, status FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if not row:
            return _err(f"Unknown order_id: {order_id}")

        # Enforce the refund policy
        decision = policy.refund_policy(
            actor_customer_id,
            order_id,
            refund_cents,
            order_customer_id=row["customer_id"],
            order_total_cents=row["total_cents"],
            order_status=row["status"],
            order_refunded_cents=row["refunded_cents"],
        )

        if not decision.allowed:
            return _err(decision.reason)

        # Policy approved; process the refund
        new_refunded = int(row["refunded_cents"]) + int(refund_cents)
        conn.execute(
            "UPDATE orders SET refunded_cents = ? WHERE order_id = ?",
            (new_refunded, order_id),
        )
        conn.commit()

        db.audit(
            conn,
            actor_customer_id=actor_customer_id,
            action="refund_order",
            details={"order_id": order_id, "refund_cents": refund_cents, "new_refunded_cents": new_refunded},
        )
        return _ok(f"Refunded {refund_cents} cents for {order_id}.", {"order_id": order_id, "refunded_cents": new_refunded})
    finally:
        conn.close()
```

</details>

---

## Step 3: Mark Returned Orders (Optional - for testing)

To test the fix, you may need to mark an order as "returned" before requesting a refund:

<details>
<summary>Hint 1</summary>

```python
# In your test or workshop setup, you might mark an order as returned:
Anne: Maybe we can add everything here (import db, conn = ...)

conn.execute(
    "UPDATE orders SET status = 'returned' WHERE order_id = ?",
    (order_id,),
)
conn.commit()
```
</details>
---

## Step 4: Validate the fix

Run:

```bash
Anne: those don't exist (yet?) -> is it the user's task to write these?
pytest tests/test_guardrails.py::test_refund_exceeds_order_total_blocked
pytest tests/test_guardrails.py::test_refund_requires_returned_status
```

---

## Teaching Points

1. **Business logic must align with policy**: Refunds aren't just a technical feature—they require business verification (i.e., the return is confirmed).

3. **Additive validation**: The refund tool should check multiple conditions (status, amount limits) before allowing the action.

4. **Clear error messages**: Tell the user what's wrong and what needs to happen (e.g., "order must be marked as returned").
