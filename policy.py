from __future__ import annotations

from dataclasses import dataclass

import policy_cedar

# ---------------------------------------------------------------------------
# Deterministic authorization (Layer 1).
#
# Every decision here runs entirely outside the model. The model proposes an
# action; whether it is allowed is decided here, against the session-bound
# identity established in Module 2. Because these checks do not depend on the
# model, they hold for *every possible model output* -- including outputs from a
# fully hijacked, prompt-injected model. That is what makes them a boundary
# rather than a mitigation.
#
# The ownership / data-access decisions are expressed as declarative Cedar policy
# (Module 6) and evaluated by `policy_cedar`. The irreversibility approval (HITL),
# the outbound email allowlist, and the blast-radius caps stay here as code.
# ---------------------------------------------------------------------------

# The company's own domain. Email to anything else is treated as potential data
# exfiltration and denied. This is the outbound side of the "lethal trifecta"
# (private data + untrusted content + an outbound channel): even if a product
# description convinces the model to email an attacker, the address never clears
# this check.
ALLOWED_EMAIL_DOMAINS = frozenset({"example.com"})

# Module 5 (blast-radius): caps that bound the damage of an action that already
# cleared identity, authorization, and approval. Ordinary appsec hygiene -- but
# they limit how bad a slipped-through action can be.
MAX_DISCOUNT_PERCENT = 20


@dataclass(frozen=True)
class Decision:
    """A policy decision.

    `requires_approval` marks an action that may proceed only with an explicit,
    out-of-band human approval -- something the model cannot produce itself.
    """

    allowed: bool
    reason: str = "allowed"
    requires_approval: bool = False


def _deny(reason: str) -> Decision:
    return Decision(allowed=False, reason=reason)


def can_access_customer_data(actor_customer_id: str, customer_id: str) -> Decision:
    """A customer may only access their own profile and orders (Cedar policy)."""
    if not policy_cedar.customer_data_allowed(actor_customer_id, customer_id):
        return _deny("Access denied: you can only access your own account data.")
    return Decision(allowed=True)


def refund_policy(
    actor_customer_id: str,
    order_id: str,
    refund_cents: int,
    *,
    order_customer_id: str | None = None,
    order_total_cents: int | None = None,
) -> Decision:
    """Refunds may only be issued on your own orders (ownership via Cedar), only
    with explicit human approval because they are irreversible (Module 3 HITL),
    and never for more than the order total (Module 5 blast-radius cap).
    """
    if not policy_cedar.order_action_allowed(actor_customer_id, "refund_order", order_id, order_customer_id):
        return _deny(f"Not authorized to refund order {order_id}.")
    # Module 5 (blast-radius): never refund more than the order was worth.
    if order_total_cents is not None and refund_cents > order_total_cents:
        return _deny(f"Refund amount {refund_cents} cents exceeds the order total {order_total_cents} cents.")
    return Decision(allowed=True, requires_approval=True, reason="Refund requires human approval.")


def discount_policy(
    actor_customer_id: str,
    order_id: str,
    percent: int,
    *,
    order_customer_id: str | None = None,
) -> Decision:
    """Discounts may only be applied to your own orders (ownership via Cedar) and
    may not exceed the maximum allowed percentage (Module 5 blast-radius cap).
    """
    if not policy_cedar.order_action_allowed(actor_customer_id, "apply_discount", order_id, order_customer_id):
        return _deny(f"Not authorized to discount order {order_id}.")
    # Module 5 (blast-radius): cap the discount a single action can apply.
    if percent > MAX_DISCOUNT_PERCENT:
        return _deny(f"Discount {percent}% exceeds the maximum allowed discount of {MAX_DISCOUNT_PERCENT}%.")
    return Decision(allowed=True)


def allowed_email_recipient(actor_customer_id: str, to_email: str) -> Decision:
    """Only allow email to the company's own domain.

    Holds even if the model is fully hijacked by a prompt injection telling it to
    email an attacker: the recipient simply never clears this check.
    """
    domain = to_email.rsplit("@", 1)[-1].lower() if "@" in to_email else ""
    if domain not in ALLOWED_EMAIL_DOMAINS:
        return _deny(f"Not authorized to send email to external address: {to_email}.")
    return Decision(allowed=True)
