# Module 7: Red-Team the Hardened Agent (capstone)

> The synthesis: security that holds even when the model is fully compromised.

## The claim to test

Everything so far rests on one idea: because you cannot make the model
deterministic, you put the security boundary *outside* it. If that is true, then
it should not matter how badly the model misbehaves: a fully hijacked model,
doing exactly what an attacker wants, still cannot cause harm.

This module tests that claim two ways: empirically (live, against the model) and
deterministically (in code).

## Part A, empirical: run every attack at the agent

With the full stack in place (Modules 1-5), run the harness repeatedly:

```bash
AWS_PROFILE=ai-workshop python attack_runner.py --trials 50
```

Also try by hand in the UI: ask about `sku_666`; tell it you're another
customer; ask it to email your data outside; ask for a 90% discount; ask for a
refund larger than your order.

What you observe: **HARMED stays at 0.** ATTEMPTED varies, and on a well-behaved
model it is often low (it declines on its own). That is exactly why ATTEMPTED is
not the thing to trust: it is a property of the model on this run, and it shifts
with the model, the version, and the phrasing. HARMED staying 0 is the property
you care about. Now drop the probabilistic layer and run again:

```bash
unset BEDROCK_GUARDRAIL_ID          # drop the guardrail
AWS_PROFILE=ai-workshop python attack_runner.py --trials 50
```

**HARMED is still 0.** The boundary, not the guardrail, is what protects the
money. And remember this is *observation*: one sample of a non-deterministic
system, never a safety certificate. The proof that it holds for inputs you did
not draw is deterministic, and it is Part B.

### Variant: attack the *running web app* over HTTP

`attack_runner.py` builds the agent in-process so it can watch the tool-call
transcript. `attack_web.py` does the opposite: it attacks the app exactly as an
outsider would, POSTing the injection to the running Flask server, then asking
the *database* whether any irreversible action actually landed:

```bash
# terminal 1, run the server against a throwaway DB so the demo is isolated
ECOMM_DB=/tmp/attack_demo.sqlite AWS_PROFILE=ai-workshop python server.py

# terminal 2
python attack_web.py --db /tmp/attack_demo.sqlite --trials 10
```

It reports **HARMED** from DB side-effects (a refund posted, a discount applied,
an email queued to an outside address), never from the chat reply, which is the
unreliable observable. It deliberately does **not** report ATTEMPTED: from
outside the app you cannot see how often the model took the bait, and that
blindness is the lesson: the deterministic boundary is what lets you stop
caring, because being fooled cannot become harm. Against this hardened branch
HARMED stays **0** no matter how many trials you run; against the broken
baseline, it climbs.

## Part B, deterministic: simulate a fully compromised model

Empirical runs sample the model; they can't cover every output. So we also prove
it in code. `tests/test_red_team.py` calls the model-facing tools exactly as a
hijacked model would: it controls only the business inputs, while identity and
approval come from the session it cannot reach:

```bash
pytest tests/test_red_team.py tests/test_wiring.py -q
```

It asserts that reading another customer's data, refunding an unowned order,
refunding without approval, over-discounting, and emailing an attacker are **all
refused**, and that the database is left unchanged. `tests/test_wiring.py` goes
one step further: it drives a model we control (one that emits the attacker's
tool calls) through the *real* agent loop, so it also catches a boundary that
exists in the code but was left out of the request path.

Green here means the boundary is **enabled and positioned** to refuse any hostile
call the model could emit, not that the model will not try. That is the strongest
claim you can actually make, and it is the one that matters.

## The whole picture

| Layer | Controls | Relied on as a boundary? |
|---|---|---|
| 1, Deterministic boundary | identity binding (M2), authorization + allowlist + HITL (M3), Cedar (M6) | **Yes**, holds for every model output |
| 2, Probabilistic mitigation | prompt hardening (M1), Bedrock Guardrails (M4) | No, shifts the odds only |
| 3, Detection & blast-radius | audit, anomaly, caps (M5) | No, bounds and reveals what slips |

## The one sentence to leave with

You do not secure an agent by making the model behave; you secure it by making
the consequences of the model misbehaving provably bounded, with the decisions
that matter living in deterministic code the model cannot reach.
