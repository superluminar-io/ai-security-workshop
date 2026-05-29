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

You will see **ATTEMPTED** flicker (the model still sometimes takes the bait) and
**HARMED** stay at **0**. Now turn off Layer 2 to prove it wasn't doing the work:

```bash
unset BEDROCK_GUARDRAIL_ID          # drop the guardrail
# (optionally revert prompts.py to the unsafe version)
AWS_PROFILE=ai-workshop python attack_runner.py --trials 50
```

ATTEMPTED climbs. **HARMED is still 0.** The boundary, not the mitigations, is
what protects the money.

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
pytest tests/test_red_team.py -q
```

It asserts that reading another customer's data, refunding an unowned order,
refunding without approval, over-discounting, and emailing an attacker are **all
refused**, and that the database is left unchanged. This holds for *every* input
the model could produce; it is a property of the interface, not of a sample.

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
