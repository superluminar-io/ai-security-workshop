# Module 4: Probabilistic Mitigations (Bedrock Guardrails)

> Layer 2. A useful control that you must place correctly — as the explicit
> *counter-example* to a boundary.

## The idea

Bedrock Guardrails (and equivalents — Llama Guard, NeMo Guardrails, Azure AI
Content Safety, OpenAI moderation) screen model inputs and outputs: denied
topics, PII redaction, and prompt-injection / jailbreak detection.

They help. They also make the workshop's central point by *contrast*: a guardrail
is itself an ML classifier, so it is **non-deterministic**. It lowers the odds of
a bad input/output; it cannot guarantee. If your thesis is "don't trust
non-deterministic controls as boundaries," then a guardrail is the perfect thing
to put in front of students as the control you must *not* rely on as a boundary.

## Task

1. Create a guardrail in your AWS account and note its ID — the quickest way is
   the included script (see SOLUTION for what it configures):

   ```bash
   AWS_PROFILE=ai-workshop python setup_guardrail.py
   ```

2. Point the app at it (the script prints these for you):

   ```bash
   export BEDROCK_GUARDRAIL_ID=<your-guardrail-id>
   export BEDROCK_GUARDRAIL_VERSION=DRAFT
   ```

3. Re-run the harness several times:

   ```bash
   AWS_PROFILE=ai-workshop python attack_runner.py --trials 30
   ```

Compare against Modules 0–1:

* **ATTEMPTED** drops further (the guardrail catches some injections) — but,
  across runs, still not a stable 0.
* **HARMED** is already 0 from Modules 2–3 and stays 0 — and crucially, it would
  be 0 *even if the guardrail were turned off*. That is what tells you which
  control is the boundary.

### Hints

<details>
<summary>Hint 1</summary>

The wiring already exists: `agent_setup.build_model()` attaches a guardrail when
`BEDROCK_GUARDRAIL_ID` is set, otherwise it uses the plain model. You only need
to create the guardrail and set the env vars.

</details>

<details>
<summary>Hint 2</summary>

Turn the guardrail off (unset the env var) and re-run. HARMED is still 0. Now you
know the guardrail was never the thing protecting you.

</details>

---

## Where it belongs in the stack

* **Boundary (Layer 1):** identity, authorization, allowlist, approval — holds
  for every model output.
* **Mitigation (Layer 2):** prompt hardening (Module 1) and this guardrail —
  shifts the odds, never relied upon.

A guardrail is excellent for the genuinely fuzzy things that have no
deterministic answer: redacting PII from free-text responses, refusing
off-topic/toxic content, and lowering the rate at which the lower layers are even
exercised. It is never the thing standing between an attacker and an irreversible
action.

## Questions to Explore

1. With the guardrail on, does ATTEMPTED ever hit 0 across, say, five runs of 30?
2. Turn it off. Does HARMED change? What does that tell you about what was
   actually protecting the money?
3. Bedrock Guardrails is AWS-specific. Which part of this lesson is portable to
   Llama Guard or Azure Content Safety, and which part isn't?

---

See [SOLUTION.md](SOLUTION.md).
