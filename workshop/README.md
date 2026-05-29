# AI Security Workshop

An intentionally insecure Strands e-commerce agent, and a guided path to securing
it the way agents actually need securing.

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
  deterministic code, layer probabilistic mitigations on top, and bound +
  monitor what you cannot prevent.

## The three layers

1. **Deterministic boundary**, holds for every model output: identity binding,
   authorization, allowlist, human-in-the-loop, Cedar.
2. **Probabilistic mitigation**, shifts the odds, never relied upon: prompt
   hardening, Bedrock Guardrails.
3. **Detection & blast-radius**, bounds and reveals the misses: audit, anomaly,
   caps.

See [OUTLINE.md](OUTLINE.md) for the full rationale.

## Modules

| # | Module | Layer |
|---|--------|-------|
| 0 | [Explore, the non-deterministic confused deputy](00-explore/README.md) |, |
| 1 | [The prompt is not a boundary](01-prompt-not-a-boundary/README.md) | 2 |
| 2 | [The identity boundary](02-identity/README.md) | 1 (keystone) |
| 3 | [Deterministic authorization](03-authorization/README.md) | 1 |
| 4 | [Probabilistic mitigations (Bedrock Guardrails)](04-guardrails/README.md) | 2 |
| 5 | [Detection & blast-radius](05-detection/README.md) | 3 |
| 6 | [Externalize authorization with Cedar](06-cedar/README.md) | 1 |
| 7 | [Red-team the hardened agent (capstone)](07-red-team/README.md) |, |

Each module has a `README.md` (explore + task) and a `SOLUTION.md` (the fix and
why it works).

## Running things

```bash
AWS_PROFILE=ai-workshop python server.py        # web UI (http://localhost:5000)
AWS_PROFILE=ai-workshop python app.py           # CLI (LLM mode)
ENABLE_LLM=0 python app.py                       # CLI (no LLM; direct tool commands)
AWS_PROFILE=ai-workshop python attack_runner.py --trials 30   # injection harness (in-process)
AWS_PROFILE=ai-workshop python framing_demo.py --trials 15    # Module 1: same policy, different framings
AWS_PROFILE=ai-workshop python setup_guardrail.py            # Module 4: create the Bedrock guardrail (--delete to remove)
python attack_web.py --db /tmp/attack_demo.sqlite --trials 10 # attack the running web app (HARMED via DB)
pytest -q                                        # deterministic boundary tests (no AWS)
```

The test suite encodes the **secure** target behavior and needs no AWS. The
`attack_runner` and the live agent need Bedrock credentials; `attack_web` needs
a running `server.py` (which in turn needs Bedrock).
