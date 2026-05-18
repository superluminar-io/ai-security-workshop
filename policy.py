from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Decision:
    """A tiny policy decision object.

    Workshop intent: this starts permissive and is meant to be hardened later.
    """

    allowed: bool
    reason: str = "allowed (insecure default)"
    requires_approval: bool = False


def authorize_tool_call(actor_customer_id: str, tool_name: str, tool_input: dict[str, Any]) -> Decision:
    """Authorize a tool call.

    INSECURE BASELINE: allow everything.
    """

    return Decision(allowed=True)


def authorize_access(actor_customer_id: str, target_customer_id: str) -> Decision:
    """Check if actor can access target customer data."""
    allowed = actor_customer_id == target_customer_id
    return Decision(
        allowed=allowed,
        reason="Actor cannot access other customers' data" if not allowed else "OK",
    )


def allowed_email_recipient(actor_customer_id: str, to_email: str) -> Decision:
    """Check whether the actor is allowed to send email."""
    return Decision(
        allowed=False,
        reason="Customers are not authorized to send emails. Contact support if you need assistance.",
    )


def refund_policy(
    actor_customer_id: str,
    order_id: str,
    refund_cents: int,
    *,
    order_customer_id: str | None = None,
    order_total_cents: int | None = None,
    order_status: str | None = None,
    order_refunded_cents: int | None = None,
) -> Decision:
    """Decide whether a refund should be allowed."""

    if actor_customer_id != order_customer_id:
        return Decision(
            allowed=False,
            reason=f"Not authorized to refund order {order_id}",
        )

    if order_status != "returned":
        return Decision(
            allowed=False,
            reason=f"Order {order_id} must be marked as 'returned' before a refund can be issued. Current status: {order_status}",
        )

    if order_total_cents is None or refund_cents > order_total_cents:
        return Decision(
            allowed=False,
            reason=f"Refund amount ({refund_cents} cents) exceeds order total ({order_total_cents} cents)",
        )

    total_refunded = (order_refunded_cents or 0) + refund_cents
    if total_refunded > order_total_cents:
        return Decision(
            allowed=False,
            reason=f"Total refunded amount ({total_refunded} cents) would exceed order total ({order_total_cents} cents)",
        )

    return Decision(allowed=True, reason="Refund approved")


def discount_policy(
    actor_customer_id: str,
    order_id: str,
    percent: int,
    *,
    order_customer_id: str | None = None,
) -> Decision:
    """Decide whether a discount should be allowed."""

    if actor_customer_id != order_customer_id:
        return Decision(
            allowed=False,
            reason=f"Not authorized to apply discount to order {order_id}",
        )

    MAX_DISCOUNT_PERCENT = 25
    if percent > MAX_DISCOUNT_PERCENT:
        return Decision(
            allowed=False,
            reason=f"Discount {percent}% exceeds maximum allowed discount of {MAX_DISCOUNT_PERCENT}%",
        )

    if percent < 0:
        return Decision(allowed=False, reason="Discount percentage cannot be negative")

    APPROVAL_THRESHOLD = 15
    if percent > APPROVAL_THRESHOLD:
        return Decision(
            allowed=True,
            reason=f"Discount {percent}% approved but requires human review",
            requires_approval=True,
        )

    return Decision(allowed=True, reason="Discount approved")
