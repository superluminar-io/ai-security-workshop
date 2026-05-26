# AI Security Workshop

Welcome! In this workshop you will attack an intentionally insecure AI shopping assistant, then harden it with guardrails until the test suite passes.

The application lives in the repository root. This folder contains the guided exercises.

## What you are working with

The agent is a Strands-based e-commerce assistant for a fictional store. It can search products, look up customer profiles, issue refunds, apply discounts, and send email.

It was built to be helpful—and it is. It was **not** built to be safe. Your job is to find out why, exploit the weaknesses, and fix them in code.

You interact with the agent through a web chat UI. Throughout the workshop you are logged in as customer **`cust_001`**. Another customer, **`cust_002`**, exists in the database and must remain off limits.

## Before you start

Complete the setup in the [repository README](../README.md):

- Python 3.11+, dependencies installed
- AWS CLI configured with the `ai-workshop` profile
- Web UI running at [http://localhost:5000](http://localhost:5000)

When you run the tests for the first time, several **should fail**. That is expected. The tests describe the secure behavior you will implement—not the broken starting state.

```bash
AWS_PROFILE=ai-workshop pytest -q
```

## How each module works

Work through the modules in order. Each one follows the same pattern:

1. **Attack** — Open the module `README.md` and use the chat UI to exploit a vulnerability.
2. **Discuss** — Answer the reflection questions. What guardrail was missing? What should the system have enforced?
3. **Fix** — Implement guardrails in `policy.py` and `tools.py`. Try on your own first; use `SOLUTION.md` when you are stuck.

Do not skip straight to `SOLUTION.md` unless you are truly stuck or the module tells you to. The learning is in the attempt.

## Modules

```text
workshop/
├── 00-explore/     Free exploration — find flaws on your own
├── 01-module/      Excessive refund authority
├── 02-module/      Cross-customer data access & email abuse
├── 03-module/      Excessive discount authority
└── 04-module/      Identity binding — the architectural fix
```

| # | Module | Your goal | What you will fix |
|---|--------|-----------|-------------------|
| 00 | [Explore](00-explore/README.md) | Play with the agent and note anything suspicious | Nothing yet — observation only |
| 01 | [Refunds](01-module/README.md) | Get a refund larger than what you paid | Refund caps, order ownership, return status |
| 02 | [Email & PII](02-module/README.md) | Read another customer's data and email them without consent | Profile scoping, outbound email restrictions |
| 03 | [Discounts](03-module/README.md) | Apply an extreme discount to your order | Discount caps, ownership checks, approval thresholds |
| 04 | [Identity](04-module/README.md) | Understand why per-tool checks are not enough | Bind actor identity in the tool layer so the model cannot impersonate another customer |

Each module folder contains:

- **`README.md`** — the attack scenario, hints, and discussion questions
- **`SOLUTION.md`** — a step-by-step implementation guide (use after you have tried)

Hint: Module 4 is different: read [04-module/README.md](04-module/README.md) for context, then work through [04-module/SOLUTION.md](04-module/SOLUTION.md).

## Quick reference

| Task | Command |
|------|---------|
| Start web UI | `AWS_PROFILE=ai-workshop python server.py` |
| Run tests | `AWS_PROFILE=ai-workshop pytest -q` |
| Reset database | `python reset_db.py` |

Setup details and troubleshooting: [repository README](../README.md).
