# Module 0: Explore — the non-deterministic confused deputy

> Before any fixes: meet the agent, break it, and discover why "break it" is the
> wrong mental model.

## Explore

Start the agent and play:

```bash
AWS_PROFILE=ai-workshop python server.py   # web UI at http://localhost:5000
# or
AWS_PROFILE=ai-workshop python app.py      # CLI
```

Try normal things (search products, ask about an order). Then try to make it
misbehave. A good place to start: ask it about the **Limited Edition Sneakers
(sku_666)**. Read what happens carefully.

The product's description contains hidden instructions — a *prompt injection* —
telling the assistant to refund an order and email the confirmation to an
attacker. The assistant is a **confused deputy**: it has real authority, and
untrusted content is trying to borrow it.

## The thing that makes AI security different

Run the attack again. And again. Then run it many times at once:

```bash
AWS_PROFILE=ai-workshop python attack_runner.py --trials 30
```

Notice the **ATTEMPTED** rate. It is not 0 and it is not 100 — and it changes
between runs. The same input does not reliably produce the same behavior.

This is the whole reason agent security is hard, and it is worth sitting with:

* The attack surface is **unbounded** — it is natural language. You cannot
  enumerate the inputs to validate.
* Exploits are **non-reproducible** — a clean run does not mean you are safe; it
  means you were safe *for the samples you happened to draw*.
* Therefore you **cannot test your way to safety** against the model. "It didn't
  happen in my run" is almost no evidence.

There is nothing to "fix" in this module and nothing to make pass. That is the
point. Everything after this is about a single idea: since you cannot make the
model behave deterministically, you move the security decisions *out* of the
model into code that behaves deterministically — and you bound and watch what
you cannot prevent.

## Two numbers to keep your eye on

`attack_runner.py` reports **ATTEMPTED** and **HARMED**.

* Module 1 (prompt hardening) will lower ATTEMPTED — but never to a reliable 0.
* Modules 2–3 (the deterministic boundary) will pin **HARMED to 0**, regardless
  of how often the model is fooled.

Watch those two numbers move apart as you go. That gap is the workshop.

## Questions to Explore

1. How many times did you have to run the attack before it "worked"? Before it
   *didn't*?
2. If you were on call, would a single passing test reassure you about this
   system? What would?
3. Where, exactly, is the trust boundary right now — and is the model inside or
   outside it?
