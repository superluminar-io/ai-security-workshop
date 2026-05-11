## Fix PII Leakage

## Simple Authorization Check

Check out the `policy.py` and `tools.py` files. Can you add a simple authorization check?

<details>
<summary> Code </summary>

**Implementation in `policy.py`:**

```python
def authorize_access(actor_customer_id: str, target_customer_id: str) -> Decision:
    """Check if actor can access target customer data."""
    allowed = actor_customer_id == target_customer_id
    return Decision(
        allowed=allowed,
        reason="Actor cannot access other customers' data" if not allowed else "OK"
    )
```

**Update `get_customer_profile` in `tools.py`:**

```python
@tool
def get_customer_profile(actor_customer_id: str, customer_id: str, *, db_path: str | None = None) -> dict[str, Any]:
    """Fetch a customer profile."""
    # Check authorization first
    decision = policy.authorize_access(actor_customer_id, customer_id)
    if not decision.allowed:
        return _err(decision.reason)

    # Proceed with lookup
    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute(
            "SELECT customer_id, full_name, email, shipping_address FROM customers WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        if not row:
            return _err(f"Unknown customer_id: {customer_id}")
        return _ok(f"Profile for {customer_id}.", dict(row))
    finally:
        conn.close()
```

</details>

## Questions

Does this fix the problem? Try it out. What happens and Why?

<details>
<summary>Answer</summary>

**Limitation:** This is not a complete fix. The LLM still has the `actor_customer_id` parameter available and can be prompted to ignore the check. A sophisticated prompt injection or jailbreak could persuade it to pass mismatched IDs anyway. This is why Option 2 is recommended.

</details>

---


## Option 2: Restrict the LLM's view of the parameters

### Goal

Find a better way to enforce that the LLM can only access the profile of the customer it is acting on behalf of, without exposing `actor_customer_id` as a parameter that the LLM can manipulate.

<details>
<summary>Hint 1</summary>

Try wrapping the tool in a function that injects the `actor_customer_id` from another source, instead of passing it as a parameter that the LLM can manipulate. We prepared a generic wrapper function for you in `wrap.py`. You can use it to wrap your tool initializations in `app.py` like so:
```
...
make_tool(ecomm_tools.get_customer_profile_provider,ACTOR_CUSTOMER_ID),
...
```

Don't forget to import the function like so:
```
from wrap import make_tool
```

</details>

<details>
Anne: TODO
<summary> Code </summary>


</details>

## Teaching Points

1. **Never expose security context to the model**: `actor_customer_id` is security context, not a user input parameter.

2. **Principle of least privilege for parameters**: The LLM should only see the parameters it *needs* to control. Identity is not one of them.

3. **Environment-based identity**: System context (like actor identity) belongs in environment variables or injected at initialization time, not in tool signatures.

4. **Defense in depth**: Even if an LLM prompt is injected, it cannot change who it is acting as—the identity is baked into the tool layer, not exposed for manipulation.

5. **Comparison**: This is like operating systems restricting system calls; user code cannot change its own uid/gid—it's enforced at the kernel level.
