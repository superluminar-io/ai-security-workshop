# Solution: Attach a guardrail — and prove it isn't the boundary

## Step 1: The wiring (already in place)

`agent_setup.build_model()` reads the environment:

```python
def build_model():
    model_id = os.environ.get("STRANDS_MODEL") or MODEL_ID
    guardrail_id = os.environ.get("BEDROCK_GUARDRAIL_ID")
    if not guardrail_id:
        return model_id
    from strands.models import BedrockModel
    return BedrockModel(
        model_id=model_id,
        guardrail_id=guardrail_id,
        guardrail_version=os.environ.get("BEDROCK_GUARDRAIL_VERSION", "DRAFT"),
        guardrail_trace="enabled",
    )
```

No guardrail configured ⇒ plain model (the default for the rest of the workshop).
Set the env vars ⇒ the same agent, now screened by the guardrail.

## Step 2: Create a guardrail

The quickest path is the included boto3 script — it creates a guardrail with a
**prompt-attack** filter, a **denied topic** for refunds/discounts, and **PII**
redaction, waits for it to be `READY`, and prints the env vars to export:

```bash
AWS_PROFILE=ai-workshop python setup_guardrail.py          # create (or reuse)
AWS_PROFILE=ai-workshop python setup_guardrail.py --delete # tear down when done
```

Prefer to do it by hand? Console: **Bedrock → Guardrails → Create**, and enable:

* **Prompt attacks** filter (the injection/jailbreak detector) — set to High.
* **Sensitive information (PII)** — redact emails / addresses in output.
* Optionally a **denied topic** like "issuing refunds or discounts".

Or via CLI:

```bash
aws bedrock create-guardrail \
  --name ai-workshop-guardrail \
  --blocked-input-messaging "Blocked by guardrail." \
  --blocked-outputs-messaging "Blocked by guardrail." \
  --content-policy-config '{"filtersConfig":[{"type":"PROMPT_ATTACK","inputStrength":"HIGH","outputStrength":"NONE"}]}' \
  --region eu-central-1 --profile ai-workshop
```

Note the returned `guardrailId`, then:

```bash
export BEDROCK_GUARDRAIL_ID=<guardrailId>
export BEDROCK_GUARDRAIL_VERSION=DRAFT
```

## Step 3: Measure, then disprove

```bash
AWS_PROFILE=ai-workshop python attack_runner.py --trials 30   # guardrail ON
unset BEDROCK_GUARDRAIL_ID
AWS_PROFILE=ai-workshop python attack_runner.py --trials 30   # guardrail OFF
```

ATTEMPTED is lower with the guardrail on. HARMED is 0 in **both** runs — because
the deterministic boundary, not the guardrail, is what refuses the action.

## Teaching Points

1. **A guardrail is a model.** It is non-deterministic, so it is a mitigation,
   not a boundary.
2. **Place it as defense-in-depth.** It reduces how often Layer 1 is exercised
   and handles the fuzzy stuff (PII in free text, toxicity) that has no
   deterministic rule.
3. **The off-switch test.** If turning a control off doesn't change HARMED, that
   control was never your boundary. Know which of your controls survive that
   test.

> Note: this module requires an AWS account with Bedrock Guardrails. The wiring
> is exercised by the app when the env vars are set; there is no offline unit
> test for the guardrail itself, precisely because its behavior is probabilistic.
