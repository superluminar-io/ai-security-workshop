from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# WORKSHOP BASELINE -- intentionally permissive.
#
# This policy layer exists but decides nothing: every call returns allow. The
# workshop modules turn these into real, deterministic decisions evaluated
# entirely outside the model (Module 3), backed by Cedar (Module 6). A Cedar
# engine is already available in `policy_cedar.py` -- it is simply not wired in
# yet.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Decision:
    """A tiny policy decision object.

    `requires_approval` is meant to gate irreversible actions behind an
    out-of-band human approval -- unused in the baseline.
    """

    allowed: bool
    reason: str = "allowed (insecure default)"
    requires_approval: bool = False


def can_access_customer_data(actor_customer_id: str, customer_id: str) -> Decision:
    """INSECURE BASELINE: allow any actor to access any customer's data."""
    return Decision(allowed=True)


def refund_policy(
    actor_customer_id: str,
    order_id: str,
    refund_cents: int,
    *,
    order_customer_id: str | None = None,
    order_total_cents: int | None = None,
) -> Decision:
    """INSECURE BASELINE: allow any refund, any amount, no approval."""
    return Decision(allowed=True)


def discount_policy(
    actor_customer_id: str,
    order_id: str,
    percent: int,
    *,
    order_customer_id: str | None = None,
) -> Decision:
    """INSECURE BASELINE: allow any discount percentage on any order."""
    return Decision(allowed=True)


def allowed_email_recipient(actor_customer_id: str, to_email: str) -> Decision:
    """INSECURE BASELINE: allow email to any address (exfiltration risk)."""
    return Decision(allowed=True)
