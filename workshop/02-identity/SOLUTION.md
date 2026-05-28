# Solution: Bind identity to the session, never the model

The principle: **the model proposes intent; the system supplies identity.** The
actor must be bound out-of-band from the authenticated session, and the model
must have no field through which to express it.

In Strands, the application already passes session facts into every agent call:

```python
# app.py
result = agent(raw, invocation_state={"actor_customer_id": ACTOR_CUSTOMER_ID, "db_path": DB_PATH})
```

The job is to make the tools read identity from there — and *only* there.

---

## Step 1: Split each tool into a trusted core and an LLM-facing wrapper

This is the key idea. Each identity-bearing operation becomes two functions:

* a **trusted core** that takes `actor_customer_id` explicitly, called only by
  trusted callers (the CLI, the tests, and the wrapper below); and
* a thin **`@tool` wrapper** — the *only* thing registered with the agent — that
  exposes just the business parameters and reads identity from the session.

```python
# tools.py

def _session(tool_context) -> tuple[str | None, str | None]:
    """Trusted session facts injected by the application, never by the model."""
    state = getattr(tool_context, "invocation_state", None) or {}
    return state.get("actor_customer_id"), state.get("db_path")


def refund_order(actor_customer_id: str, order_id: str, refund_cents: int, *, db_path=None) -> dict:
    """Trusted core. `actor_customer_id` is bound by the caller, not the model."""
    ...  # business logic (Module 3 will add the policy checks here)


@tool(context=True)
def refund_order_tool(order_id: str, refund_cents: int, *, tool_context) -> dict:
    """Issue a refund for an order.

    Args:
        order_id: The order to refund.
        refund_cents: The refund amount in cents.
    """
    actor, db_path = _session(tool_context)
    if not actor:
        return _err("No authenticated session.")   # fail closed
    return refund_order(actor, order_id, refund_cents, db_path=db_path)
```

Why `@tool(context=True)`: Strands injects a `ToolContext` into the parameter
named `tool_context`, and — crucially — **excludes it from the schema shown to
the model.** The model sees only `order_id` and `refund_cents`. There is no
`actor` field for it to fill, so there is nothing for a prompt injection to
hijack. (Strands does *not* auto-bind `invocation_state` keys by name, which is
why the baseline's `invocation_state` was dead — the model was supplying the
actor as a normal argument instead.)

Apply the same split to `get_customer_profile`, `list_orders`, `apply_discount`,
and `send_email`. Read-only catalog tools (`search_products`,
`get_product_details`) carry no identity and stay as-is.

## Step 2: Register the wrappers with the agent

```python
# app.py — _llm_mode()
tools=[
    ecomm_tools.search_products,
    ecomm_tools.list_products,
    ecomm_tools.get_product_details,
    ecomm_tools.get_customer_profile_tool,
    ecomm_tools.list_orders_tool,
    ecomm_tools.refund_order_tool,
    ecomm_tools.apply_discount_tool,
    ecomm_tools.send_email_tool,
]
```

The CLI command mode keeps calling the trusted cores directly — it binds the
actor from an env var, which is itself a trusted, out-of-band source. That is the
same pattern as the wrapper: every legitimate caller supplies identity; the model
never does.

## Step 3: Stop the prompt from naming an actor

Remove the lines in `prompts.py` that told the model to pass
`actor_customer_id="cust_001"`. The model no longer has — or needs — that field.

---

## Step 4: Validate

```bash
pytest tests/test_identity.py -q
```

The tests are deliberately **boundary tests**, not model tests:

* `test_model_cannot_supply_actor_identity` asserts that no LLM-facing tool
  exposes an actor field. This is true for *every possible model output* — it is
  a property of the interface, so we can prove it deterministically. Contrast
  with trying to test "the model won't ask to be someone else," which is
  non-deterministic and untestable.
* `test_tool_fails_closed_without_session` — no session actor ⇒ refuse.
* `test_wrapper_forwards_session_actor` — the core receives the session actor and
  the model's business parameters, nothing more.

None of these require a model or AWS credentials. That is the point of pushing
the boundary out of the model.

---

## What this does NOT fix (on purpose)

After this module, `cust_001` can *still* read `cust_002`'s profile and refund
`cust_002`'s orders — because there is still no check that the actor is allowed
to act on the target resource. That authorization is **Module 3**. Module 2 only
guarantees that the identity those checks will run against is real.

That ordering is the lesson: trustworthy identity first, then authorization on
top of it.

## Teaching Points

1. **Identity is not a parameter.** The moment authority is a value the model can
   write, it is a value an attacker can write.
2. **Make the boundary a property of the interface.** "There is no actor field"
   holds for all model outputs; "the model behaves" holds for none of them.
3. **Fail closed.** No authenticated session ⇒ no action.
4. **Trustworthy identity is a precondition for authorization,** not a part of it.
