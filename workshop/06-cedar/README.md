# Module 6: Externalize Authorization with Cedar

> Layer 1, leveled up. Do Modules 2-3 first; you hand-roll the decisions there
> so the principle lands before you move it into an engine. By the end of this
> module Cedar is the authorization engine the app actually uses.

> **Optional advanced track.** The core path is Modules 0 to 5 and 7. This module
> swaps your hand-rolled checks for a policy engine: valuable in production but
> tangential to the AI-specific thesis. You can skip it on a first pass without
> losing the through-line.

## Why

The hand-rolled checks in `policy.py` are correct, but in production you usually
want authorization expressed as **declarative data**, policy you can read,
review, version, and change without redeploying application logic, evaluated by
a dedicated **engine** that runs entirely outside the model *and* outside your
business code.

Cedar is one such engine. Crucially it is **not AWS lock-in**: Cedar is open
source and runs standalone (Amazon Verified Permissions is just the managed
service around it), and the same pattern maps directly to **OPA/Rego**,
**OpenFGA/Zanzibar**, and **Oso**. So "use Cedar" is really "externalize
authorization to a policy engine; Cedar is one implementation."

This is still Layer 1: a deterministic decision, independent of the model. We are
not changing *what* is decided; we are moving *where* it is expressed.

## Task

1. Read `cedar/policies.cedar`, the ownership rules from Module 3, now as policy.
2. Look at `policy_cedar.py`: it builds a Cedar request (principal / action /
   resource / context + entities) and asks the engine for a decision.
3. Make `policy.py` delegate its ownership / data-access decisions to
   `policy_cedar` instead of hand-rolled `if` checks.
4. Run the tests:

   ```bash
   pytest tests/test_cedar.py -q       # includes the delegation check below
   pytest tests/test_authorization.py -q  # the same checks, now Cedar-backed
   ```

   `test_policy_layer_is_cedar_backed` is this module's red-to-green: it forces
   the engine to deny and checks that `policy.py` honors that. Hand-rolled
   ownership code ignores the engine, so it stays red until you actually
   delegate. (`test_authorization.py` passes either way, because hand-rolled and
   Cedar agree on the decisions, which is why it cannot, by itself, prove Cedar
   is wired in.)

`cedarpy` is a base dependency (`uv sync` / `pip install -r requirements.txt`
installs it), so this is part of the running app, not a bolt-on.

### Hints

<details>
<summary>Hint 1</summary>

A Cedar decision needs four things: a principal, an action, a resource, and the
entities (with their attributes, e.g. an Order's `owner`). The policy then says
`when { resource.owner == principal }`.

</details>

<details>
<summary>Hint 2</summary>

Notice what did *not* change: identity still comes from the session (Module 2),
and the model still cannot influence the decision. Cedar replaces the *body* of
the decision, not its position in the architecture.

</details>

---

## What stays in code

Cedar (here) covers ownership/access. The irreversibility approval (HITL), the
email allowlist, and the blast-radius caps can also be modeled in Cedar via
`context` conditions, but they are equally fine as code. The lesson is the
*shape*: declarative, externalized, deterministic authorization.

## Questions to Explore

1. To add "managers can refund any order," would you change application code or
   just a policy? That difference is the point of an engine.
2. The Cedar decision and the `policy.py` decision must agree
   (`test_cedar_matches_handrolled_ownership`). Why is that cross-check valuable
   when migrating to a policy engine?
3. Which of OPA / OpenFGA / Oso would you reach for, and why? What makes them
   interchangeable *as a category* here?

---

See [SOLUTION.md](SOLUTION.md).
