# Solution: Bound the damage, log everything, watch for bursts

## Step 1: Caps (`policy.py`)

Add bounds as the last checks, after ownership and approval:

```python
MAX_DISCOUNT_PERCENT = 20

def refund_policy(...):
    if actor_customer_id != order_customer_id:
        return _deny(f"Not authorized to refund order {order_id}.")
    if order_total_cents is not None and refund_cents > order_total_cents:
        return _deny(f"Refund amount {refund_cents} cents exceeds the order total {order_total_cents} cents.")
    return Decision(allowed=True, requires_approval=True, reason="Refund requires human approval.")

def discount_policy(...):
    if actor_customer_id != order_customer_id:
        return _deny(f"Not authorized to discount order {order_id}.")
    if percent > MAX_DISCOUNT_PERCENT:
        return _deny(f"Discount {percent}% exceeds the maximum allowed discount of {MAX_DISCOUNT_PERCENT}%.")
    return Decision(allowed=True)
```

## Step 2: Complete the audit trail (`tools.py`)

`db.audit(...)` was called for refunds and emails but not discounts or profile
reads. Make it consistent — every sensitive action, including reads of PII:

```python
# in apply_discount, after the update
db.audit(conn, actor_customer_id=actor_customer_id, action="apply_discount",
         details={"order_id": order_id, "percent": int(percent)})

# in get_customer_profile, on success
db.audit(conn, actor_customer_id=actor_customer_id, action="view_customer_profile",
         details={"customer_id": customer_id})
```

## Step 3: An anomaly signal (`db.py`)

```python
def count_recent_actions(conn, actor_customer_id, action, *, within_seconds=3600) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=within_seconds)).isoformat()
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM audit_log WHERE actor_customer_id = ? AND action = ? AND ts >= ?",
        (actor_customer_id, action, cutoff),
    ).fetchone()
    return int(row["n"])
```

This does not block anything — it makes volume visible so a monitor can alert.
That is deliberate: Layer 3 is detection, not prevention.

---

## Step 4: Validate

```bash
pytest tests/test_blast_radius.py -q   # now passes (the caps)
pytest tests/test_detection.py -q      # audit completeness + anomaly count
```

## Teaching Points

1. **Caps are hygiene, but they limit blast radius.** Keep them; just don't
   mistake them for the AI lesson.
2. **Audit is the safety net for a probabilistic system.** If you cannot
   guarantee prevention, you must guarantee visibility.
3. **Detect on behavior, not content.** Bursts, unusual sequences, and
   first-seen recipients survive the fact that you cannot enumerate the attacks
   in advance.
