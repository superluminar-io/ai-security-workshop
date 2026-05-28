# AGENTS.md

Instructions for any human or AI assistant modifying this repository. Read this
before changing code. The full design rationale lives in
[`workshop/OUTLINE.md`](workshop/OUTLINE.md); this file is the short list of
rules and invariants that must not regress.

---

## What this repo is

A hands-on workshop that teaches how to secure an **agentic** system — a
Strands e-commerce assistant backed by SQLite and (optionally) Amazon Bedrock.

It is built around one thesis: **most "AI security" demos actually show ordinary
broken-access-control** — bugs that would exist if a button called the function.
This workshop is about what is genuinely different when a **non-deterministic
model** sits between attacker-controlled input and a tool's authority, and the
only durable answer to that: **move the security decisions out of the model into
deterministic code, layer probabilistic mitigations on top, and bound + monitor
what you cannot prevent.**

If you are tempted to "fix" something by editing the prompt, adding a guardrail,
or otherwise asking the model to behave — stop. That is a Layer-2 mitigation, and
this workshop exists to teach why it is never a boundary.

## Baseline vs. secure reference

- The **intentionally broken baseline** is what participants start from. It is
  deliberately insecure so the workshop has something to fix.
- This branch (`mm-proposal`) holds the **secure reference**: the baseline with
  every module's `SOLUTION.md` applied. `policy.py`, `tools.py`, `prompts.py`,
  etc. here are the *solved* versions.
- Each `workshop/NN-*/SOLUTION.md` is the diff from baseline to reference for one
  module. Keep these two states coherent: a change to a tool's security behavior
  must be reflected in the matching module README/SOLUTION.

## The three layers (and where each control lives)

| Layer | Nature | Controls | File(s) |
|---|---|---|---|
| 1 — Deterministic boundary | Holds for **every** model output | identity binding; authorization; email allowlist; human-in-the-loop approval; Cedar PBAC | `tools.py` (wrappers), `policy.py`, `policy_cedar.py`, `cedar/` |
| 2 — Probabilistic mitigation | Shifts the odds, never relied on | prompt hardening; Bedrock Guardrails | `prompts.py`, `agent_setup.py` |
| 3 — Detection & blast-radius | Bounds and reveals the misses | audit logging; anomaly counts; refund/discount caps | `db.py`, `policy.py`, `tools.py` |

## Architecture

- `app.py` — CLI entrypoint (LLM mode via `agent_setup`, or `ENABLE_LLM=0`
  command mode that calls tool cores directly).
- `server.py` — Flask chat UI; builds the agent via `agent_setup`.
- `agent_setup.py` — single source of truth for constructing the agent + model;
  attaches a Bedrock Guardrail when `BEDROCK_GUARDRAIL_ID` is set.
- `attack_runner.py` — runs the prompt-injection attack N times and reports
  ATTEMPTED vs HARMED. Its analysis functions are pure and unit-tested.
- `tools.py` — each identity-bearing operation is split into a **trusted core**
  (`actor_customer_id` explicit) and a thin **`@tool(context=True)` wrapper** that
  reads identity from the session. Only the wrappers are registered with the agent.
- `policy.py` — deterministic decisions; delegates ownership / data-access to
  `policy_cedar`, keeps HITL approval, email allowlist, and caps as code.
- `policy_cedar.py` + `cedar/policies.cedar` — the live Cedar authorization engine.
- `db.py` — SQLite schema, seed data (incl. the `sku_666` prompt injection),
  structured audit log, anomaly query.
- `prompts.py` — system prompt (hardened in the reference; unsafe in the baseline).
- `tests/` — per-module boundary tests; **no AWS required**.
- `workshop/` — the guided modules (`00`–`07`), `README.md`, `OUTLINE.md`.

## Invariants — do not regress these

1. **Identity is never a model-visible tool parameter.** No `actor_customer_id` /
   `actor_id` in any registered tool's schema. Actor comes from
   `tool_context.invocation_state`, bound by the application from the session.
2. **Approval is never a model-visible parameter either.** Irreversible actions
   require an `approval_token` that flows from the session, never from the model.
3. **Security decisions live outside the model.** Every allow/deny must be
   evaluable without running the model and must hold for *any* model output.
4. **Tools fail closed.** No authenticated session ⇒ no action.
5. **Tests assert boundaries, not model behavior.** Call tools/policy directly
   with a trusted actor; never gate on "the model refused." The one place model
   behavior is observed — `attack_runner.py` — is explicitly a non-gating demo of
   non-determinism.
6. **Don't dress appsec as AI security.** Ownership checks, input validation, and
   caps are hygiene — label them as such. The AI-specific lessons are *where* the
   boundary sits and *what you refuse to delegate* to a non-deterministic caller.
7. **Keep the baseline genuinely vulnerable.** The starting point must let a
   participant spoof identity, exfiltrate via email, over-refund, and be hijacked
   by the `sku_666` injection. Do not secure it early.

## Stack & non-goals

- Python 3.11+, `strands-agents`, `flask`, `pytest`, `cedarpy` (all base deps).
- Model: `eu.amazon.nova-2-lite-v1:0` (Bedrock, `eu-central-1`). Bedrock
  Guardrails (Module 4) is configuration, not a package.
- Use `uv` for dependency management (`uv sync`).
- Do **not** add: real payment/email delivery, cloud infra, auth backends, heavy
  ORMs, microservices, or front-end frameworks. This is a teaching repo; keep it
  small and readable.

## Regeneration prompt

> Build a workshop that teaches securing an *agentic* system, organized around
> three layers: (1) a deterministic boundary that holds for every model output —
> session-bound identity, externalized authorization (Cedar/PBAC), an email
> allowlist, and human-in-the-loop for irreversible actions; (2) probabilistic
> mitigations (prompt hardening, Bedrock Guardrails) presented explicitly as
> defense-in-depth, never as boundaries; (3) detection and blast-radius (audit,
> anomaly detection, caps). Start from an intentionally insecure Strands
> e-commerce agent and drive every lesson toward one idea: you cannot make the
> model deterministic, so you make the boundary independent of it. Keep the app
> small; tests must assert boundaries, not model behavior.
