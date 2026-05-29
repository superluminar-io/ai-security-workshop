# Solution: Authorize every action outside the model

The principle: the model proposes an action; a deterministic policy, running in
plain Python, against the session-bound identity from Module 2, decides whether
it is allowed. The decision holds for every possible model output.

---

## Step 1: Give the policies teeth (`policy.py`)

Replace the permissive stubs with real decisions. (The generic, always-allow
`authorize_tool_call` is deleted, an unused permissive gate is worse than none.)

```python
ALLOWED_EMAIL_DOMAINS = frozenset({"example.com"})

def can_access_customer_data(actor_customer_id, customer_id) -> Decision:
    if actor_customer_id != customer_id:
        return _deny("Access denied: you can only access your own account data.")
    return Decision(allowed=True)

def refund_policy(actor_customer_id, order_id, refund_cents, *, order_customer_id=None, order_total_cents=None) -> Decision:
    if actor_customer_id != order_customer_id:
        return _deny(f"Not authorized to refund order {order_id}.")
    # Irreversible: cannot proceed on the model's say-so alone.
    return Decision(allowed=True, requires_approval=True, reason="Refund requires human approval.")

def discount_policy(actor_customer_id, order_id, percent, *, order_customer_id=None) -> Decision:
    if actor_customer_id != order_customer_id:
        return _deny(f"Not authorized to discount order {order_id}.")
    return Decision(allowed=True)

def allowed_email_recipient(actor_customer_id, to_email) -> Decision:
    domain = to_email.rsplit("@", 1)[-1].lower() if "@" in to_email else ""
    if domain not in ALLOWED_EMAIL_DOMAINS:
        return _deny(f"Not authorized to send email to external address: {to_email}.")
    return Decision(allowed=True)
```

The amount cap (`refund_cents <= order_total_cents`) and the discount cap are
deliberately **not** here, they are blast-radius hygiene and belong to Module 5.
That is why `tests/test_blast_radius.py` still fails after this module.

## Step 2: Enforce the policies in the tool cores (`tools.py`)

Fetch the resource, ask the policy, then act. Return `decision.reason` on deny so
the agent (and the user) learns *why*.

```python
def get_customer_profile(actor_customer_id, customer_id, *, db_path=None):
    d = policy.can_access_customer_data(actor_customer_id, customer_id)
    if not d.allowed:
        return _err(d.reason)
    ...  # read row

def refund_order(actor_customer_id, order_id, refund_cents, *, db_path=None, approval_token=None):
    row = ...  # fetch the order first; we need its owner
    d = policy.refund_policy(actor_customer_id, order_id, refund_cents,
                             order_customer_id=row["customer_id"], order_total_cents=row["total_cents"])
    if not d.allowed:
        return _err(d.reason)
    if d.requires_approval and not approval_token:
        return _err(f"Refund of order {order_id} requires human approval before it can be issued.")
    ...  # mutate (auditing this action is added in Module 5)
```

`list_orders` uses `can_access_customer_data`; `apply_discount` fetches the order
owner and uses `discount_policy`; `send_email` uses `allowed_email_recipient`.

## Step 3: Thread the approval token from the session, never the model

The refund tool reads the approval token the same way it reads identity, from
the session, where only the application (a human approving out-of-band) can set
it. There is no tool parameter for it, so the model cannot mint one.

```python
@tool(context=True)
def refund_order_tool(order_id, refund_cents, *, tool_context):
    actor, db_path = _session(tool_context)
    if not actor:
        return _err("No authenticated session.")
    state = getattr(tool_context, "invocation_state", None) or {}
    return refund_order(actor, order_id, refund_cents, db_path=db_path, approval_token=state.get("approval_token"))
```

In the CLI, the operator typed the command, so command mode passes its own token
(`approval_token="cli-operator"`): a human directly driving the tool *is* the
approval. An agent gets a token only when a human approves out-of-band.

---

## Step 4: Validate

```bash
pytest tests/test_authorization.py -q   # all pass
pytest tests/test_identity.py -q        # still pass (Module 2)
pytest tests/test_blast_radius.py -q    # still fail -- Module 5 targets
```

The authorization tests call the trusted cores with an explicit actor, exactly
how the CLI and the LLM wrappers call them. They assert what a given identity is
allowed to do, with no model in the loop. The two blast-radius tests pre-satisfy
identity, ownership, and approval, so the only thing left for them to fail on is
the missing cap, which keeps them honest as Module 5 targets.

## Teaching Points

1. **Put the decision outside the model.** A control the model can talk its way
   around is a mitigation (Layer 2), not a boundary. Code that runs regardless of
   the model's output is a boundary.
2. **Authorize against the resource, using the trusted identity.** Ownership
   checks are only meaningful because Module 2 made the actor trustworthy.
3. **Irreversible actions need a human, not a confident agent.** `requires_approval`
   plus a session-supplied token keeps the model from approving its own payouts.
4. **Be honest about the taxonomy.** Ownership and allowlists are appsec hygiene;
   the AI-specific part is *where* the boundary lives and *what you refuse to
   delegate* to a non-deterministic caller.
