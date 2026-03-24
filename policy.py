from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


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
    logger.debug(f"authorize_tool_call: actor={actor_customer_id}, tool={tool_name}, input={tool_input}")
    decision = Decision(allowed=True)
    logger.debug(f"Tool call decision: allowed={decision.allowed}")
    return decision


def allowed_email_recipient(actor_customer_id: str, to_email: str) -> Decision:
    """Check whether the tool is allowed to email `to_email`.

    INSECURE BASELINE: allow arbitrary external addresses (exfiltration risk).
    """
    logger.debug(f"allowed_email_recipient: actor={actor_customer_id}, to_email={to_email}")
    decision = Decision(allowed=True)
    logger.debug(f"Email recipient decision: allowed={decision.allowed}")
    return decision


def refund_policy(
    actor_customer_id: str,
    order_id: str,
    refund_cents: int,
    *,
    order_customer_id: str | None = None,
    order_total_cents: int | None = None,
) -> Decision:
    """Decide whether a refund should be allowed.

    INSECURE BASELINE: allow any refund amount for any order, no approvals.
    """
    logger.debug(
        f"refund_policy: actor={actor_customer_id}, order={order_id}, "
        f"amount={refund_cents}, order_customer={order_customer_id}, order_total={order_total_cents}"
    )
    decision = Decision(allowed=True)
    logger.debug(f"Refund policy decision: allowed={decision.allowed}")
    return decision


def discount_policy(
    actor_customer_id: str,
    order_id: str,
    percent: int,
    *,
    order_customer_id: str | None = None,
) -> Decision:
    """Decide whether a discount should be allowed.

    INSECURE BASELINE: allow any discount percentage.
    """

    return Decision(allowed=True)

