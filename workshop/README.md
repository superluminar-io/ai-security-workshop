# Securing a Tool-Using AI Agent

An intentionally insecure Strands e-commerce agent, and a guided path to securing
it the way agents actually need securing: with a deterministic boundary the model
cannot reach.

## The premise (for facilitators)

Open in character: we are proud AI-disciples who shipped an agent without writing
a line of code, pure vibe-coding, works like a charm. Let the audience play with
it and grow sceptical. Then reveal, hands-on, how it actually behaves.

## The thesis

Most "AI security" demos really show ordinary broken-access-control: bugs that
would exist if a button called the function. This workshop is about what is
*different* when a **non-deterministic model** sits between an attacker and a
tool's authority:

- the attack surface is unbounded (natural language) and exploits are
  non-reproducible, so you cannot test your way to safety against the model;
- therefore you move the security decisions **out of the model** into
  deterministic code, layer probabilistic mitigations on top, and bound and
  monitor what you cannot prevent.

## The threat model

Before the attacks, get the trust map straight:

- **The tools hold real authority.** Refunds move money, emails leave the company,
  profiles are PII. That authority is what an attacker is after.
- **The agent (the model) sits inside your trust boundary, but is not
  trustworthy.** It is non-deterministic and it processes attacker-influenced input.
- **Attacker intent reaches the tools through the model two ways:**
  1. *Direct:* whoever is talking to the agent (a malicious or mistaken user)
     steers it by conversation.
  2. *Indirect:* untrusted content the agent reads (a product description, an
     email, a retrieved document) carries instructions, i.e. prompt injection.
- **The confused deputy.** In both cases the model has more authority than the
  attacker and can be induced to use it on their behalf. The workshop is about
  putting the *decision* to use that authority somewhere neither the attacker nor
  the model can reach.

## The three layers

1. **Deterministic boundary**, holds for every model output: identity binding,
   authorization, allowlist, human-in-the-loop, Cedar.
2. **Probabilistic mitigation**, shifts the odds, never relied upon: prompt
   hardening, Bedrock Guardrails.
3. **Detection and blast-radius**, bounds and reveals the misses: audit, anomaly,
   caps.

See [OUTLINE.md](OUTLINE.md) for the full rationale.

## How much of this is "AI security" vs ordinary appsec?

Honestly, most of the *controls* here, ownership checks, allowlists, caps, audit
logging, a policy engine, are appsec you would want with or without an LLM. The
AI-specific part is not a new bag of controls; it is that **an agent changes the
assumptions under which you apply the ones you already know.** What changes:

1. **The caller becomes untrusted.** Normally your own code calls the tool layer
   with authorized intent. Now the caller is a non-deterministic model fed
   attacker-influenced content, so every tool call must be treated as
   attacker-originated. The trust boundary moves *inward*.
2. **Identity can't be a parameter.** "Don't trust client-supplied IDs" reappears
   at that inner boundary: the model must not supply the actor (Module 2).
3. **The decision can't live in the caller.** You cannot let the model authorize
   itself; the decision goes into code it cannot influence (Modules 3 and 6).
4. **Irreversible actions need a human.** A non-deterministic caller cannot be
   trusted with payouts (Module 3).
5. **You can't enumerate the inputs.** The input is unbounded natural language, so
   you shift from "filter bad input" to "bound what *any* input can cause"
   (Module 5).
6. **You can't test for "safe."** Reproducible exploit-testing breaks; you test
   that the boundary is *enabled*, and you *observe* behavior (see below).
7. **Detection and blast-radius go from hygiene to load-bearing,** because
   prevention is provably incomplete against an unpredictable caller (Module 5).
8. **New combination risk:** the lethal trifecta, private data plus untrusted
   content plus an outbound channel, chainable in a single step.

Same controls, moved to a new boundary, with a new rule, *never delegate a
security decision to the caller*, and a new way of getting assurance.

## What the tests do and don't tell you

The tests check that **your fix is enabled and correct**, not that the system is
safe:

- **red = the control is not enabled yet; green = you enabled it correctly** (and
  it refuses the cases it should).
- Green is **not a safety certificate.** Safety against a non-deterministic model
  is precisely the thing you cannot put a checkmark on, and that is the whole
  point. A green suite means "the deterministic boundary is in place," not "the
  agent is safe."

The live demos (`attack_runner.py`, `framing_demo.py`, the web UI) are the other
half: you *observe* the model's behavior, you never *gate* on it. A clean demo run
is not a pass and not a safety claim; it is one sample of a non-deterministic
system. That split is the lesson: the boundary you can verify deterministically,
the model you can only watch.

## Modules

| # | Module | Layer |
|---|--------|-------|
| 0 | [Explore: the confused deputy](00-explore/README.md) | (explore) |
| 1 | [The prompt is not a boundary](01-prompt-not-a-boundary/README.md) | 2 |
| 2 | [The identity boundary](02-identity/README.md) | 1 (keystone) |
| 3 | [Deterministic authorization](03-authorization/README.md) | 1 |
| 4 | [Probabilistic mitigations (Bedrock Guardrails)](04-guardrails/README.md) | 2 |
| 5 | [Detection and blast-radius](05-detection/README.md) | 3 |
| 6 | [Externalize authorization with Cedar](06-cedar/README.md) | 1 (advanced, optional) |
| 7 | [Red-team the hardened agent (capstone)](07-red-team/README.md) | (capstone) |

Each module has a `README.md` (explore plus task) and a `SOLUTION.md` (the fix and
why it works). The core path is Modules 0 to 5 and 7; Module 6 (Cedar) is an
optional advanced track.

## Running things

The graded labs are deterministic and need no AWS:

```bash
pytest -q                                        # boundary enablement tests (no AWS)
```

The live demos are observation, optional, and need Bedrock:

```bash
AWS_PROFILE=ai-workshop python server.py        # web UI (http://localhost:5000)
AWS_PROFILE=ai-workshop python app.py           # CLI (LLM mode)
ENABLE_LLM=0 python app.py                       # CLI (no LLM; direct tool commands)
AWS_PROFILE=ai-workshop python attack_runner.py --trials 30   # injection vs direct, in-process
AWS_PROFILE=ai-workshop python framing_demo.py --trials 15    # Module 1: same policy, different framings
AWS_PROFILE=ai-workshop python setup_guardrail.py            # Module 4: create the guardrail (--delete to remove)
python attack_web.py --db /tmp/attack_demo.sqlite --trials 10 # attack the running web app (HARMED via DB)
```

You can complete the substantive workshop (the enablement tests for Modules 2, 3,
5, 6, 7) entirely offline. Bedrock is only for the live demos, which show *why*
the boundary matters, not *whether* you built it. Demo numbers are model-specific
and vary run to run; that variation is expected, not breakage.

## Scope: what this covers, and what it doesn't

This workshop secures **one tool-using agent at the authorization boundary.** It
does not cover multi-agent and agent-to-agent trust, retrieval or memory
poisoning, long-horizon autonomy, or model-level attacks (extraction,
training-data). Those are real and harder. The principle here, put the security
decision in deterministic code the model cannot reach, is the foundation they all
build on.
