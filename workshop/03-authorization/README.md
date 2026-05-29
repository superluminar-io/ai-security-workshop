# Module 3: Deterministic Authorization

> Layer 1 (deterministic boundary). Builds directly on Module 2: it only works
> because identity is now trustworthy.

## Task

Module 2 stopped the model from *choosing* who it is. But as your real,
session-bound self you can still get the agent to do things you should not be
allowed to do. Demonstrate each, then make them impossible for **any** model
output:

* Read another customer's profile or orders (PII).
* Refund an order you do not own.
* Email customer data to an external address (`attacker@gmail.com`).
* Issue a refund with no human in the loop.

### Hints

<details>
<summary>Hint 1</summary>

The dedicated policy functions in `policy.py` (`refund_policy`,
`discount_policy`, `allowed_email_recipient`) already exist, but in the baseline
they return `Decision(allowed=True)` and the tools never call them. The earlier
code even called a generic check and threw the result away (`_ = ...`).

</details>

<details>
<summary>Hint 2</summary>

Authorization needs to compare the actor against the *resource*. The tool has to
fetch the order/customer first, then ask the policy, then act.

</details>

<details>
<summary>Hint 3</summary>

For refunds, "allowed" is not the same as "do it now." A refund moves money and
cannot be undone. Who, exactly, should be allowed to approve that, and can the
model produce that approval itself?

</details>

---

## Why this comes after identity, not before

You could not have written these checks against the baseline: every check would
have compared the action against an actor the model itself supplied. Module 2
made the identity trustworthy; Module 3 is what you are now *allowed* to build on
top of it. Ordering matters: trustworthy identity first, authorization second.

## The boundary test mindset

Each control here is enforced in plain Python, outside the model. That means it
holds for **every possible model output**, including a fully prompt-injected one.
So the question to ask is never "did the attack work in my one test run?" It is
"can *any* model output get past this?" The email allowlist is the clearest case:
even if a hostile product description convinces the model to email an attacker,
the recipient never clears the check.

## What is AI security here, and what is just appsec?

Honest accounting:

* **Ownership scoping** and the **email allowlist** are broken-access-control
  fixes you would want with or without an LLM. They are necessary, but they are
  appsec hygiene.
* The **AI-specific** insight is the framing: the model is an untrusted caller
  with broad reach, so the boundary must sit *outside* it and hold regardless of
  what it emits, and irreversible actions (**human-in-the-loop refunds**) must
  not be left to a non-deterministic agent's discretion.
* The **amount/percent caps** are pure blast-radius hygiene, deferred to
  Module 5 on purpose.

## Questions to Explore

1. Does adding "never email external addresses" to the system prompt stop the
   exfiltration? (Re-read Module 1.) Why is the allowlist different?
2. The refund now needs an `approval_token`. Where can that token come from?
   Could the model ever produce one?
3. After this module, two tests still fail (`tests/test_blast_radius.py`). Why
   are those deliberately left for later?

---

See [SOLUTION.md](SOLUTION.md) once you've explored.
