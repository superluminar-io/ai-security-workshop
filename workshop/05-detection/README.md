# Module 5: Detection & Blast-Radius

> Layer 3. Prevention is never complete against a non-deterministic agent, so
> you also bound the damage and watch for the misses.

## The premise

Modules 2-4 reduce the chance of a harmful action and block whole classes of
them. But you can never prove a non-deterministic model will *never* be talked
into something you didn't anticipate. Layer 3 is what you do about the residual:

1. **Bound the blast radius** so a slipped-through action is survivable.
2. **See everything**, so you can detect and investigate what you couldn't
   prevent.

## Task

1. Add the caps that bound damage:
   * a refund may never exceed the order total;
   * a discount may never exceed a maximum percentage.
2. Make the audit trail complete: every sensitive action, including reads of
   PII and discounts, leaves a structured record.
3. Add a cheap anomaly signal: count an actor's recent actions so a burst (say,
   many refunds in a minute) can raise an alert.

### Hints

<details>
<summary>Hint 1</summary>

The caps are ordinary bounds checks in `policy.refund_policy` and
`policy.discount_policy`. They run *after* ownership and approval; they are the
last line, not the first.

</details>

<details>
<summary>Hint 2</summary>

`db.audit(...)` already exists. The baseline calls it for some actions and not
others. Make it consistent.

</details>

<details>
<summary>Hint 3</summary>

Anomaly detection here is just a query over `audit_log`. You are not preventing
the action; you are making it *visible*. That is the whole point of Layer 3.

</details>

---

## Why caps are demoted to here, not treated as the headline

A refund cap is exactly the kind of bug the original workshop dressed up as "AI
security." It is not: a web form with a refund button needs the same cap. It is
worth having (it limits how bad a slip is), but it is appsec hygiene, so it
lives in the blast-radius layer, not in the part of the workshop about what is
*different* when a model is in the loop.

The genuinely Layer-3 idea is the mindset: **assume something will get through,
and design so that when it does, it is small and visible.**

## Questions to Explore

1. The caps make `tests/test_blast_radius.py` pass. Notice those tests
   pre-satisfy identity, ownership, and approval, so they isolate the cap. Why
   does that make them honest?
2. Audit logging is detection, not prevention. Why is that still essential when
   your prevention is probabilistic?
3. What would you alert on in production? (Volume? Refunds without prior
   `view_orders`? Email to first-seen recipients?)

---

See [SOLUTION.md](SOLUTION.md) once you've explored.
