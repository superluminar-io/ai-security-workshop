from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import db
import policy

if TYPE_CHECKING:
    # The type checker always sees the real Strands symbols, so `tool` keeps its
    # decorator type and `ToolContext` is a usable type in annotations.
    from strands import tool
    from strands.types.tools import ToolContext
else:
    try:
        from strands import tool
        from strands.types.tools import ToolContext
    except Exception:  # pragma: no cover - allows running without strands installed

        def tool(fn=None, **_kwargs):
            if fn is None:
                return lambda f: f
            return fn

        ToolContext = Any


DEFAULT_DB_PATH = os.environ.get("ECOMM_DB", "ecomm.sqlite")


def _db_path(db_path: str | None) -> str:
    return db_path or DEFAULT_DB_PATH


def _ok(text: str, data: Any | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"status": "success", "content": [{"text": text}]}
    if data is not None:
        out['content'][0]["json"] = {"data": data}
    return out


def _err(text: str, data: Any | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"status": "error", "content": [{"text": text}]}
    if data is not None:
        out["data"] = data
    return out


# ---------------------------------------------------------------------------
# Module 2, the identity boundary.
#
# There are two kinds of function below:
#
#   * Trusted core functions (get_customer_profile, refund_order, ...) take
#     `actor_customer_id` as an explicit argument. They are called only by
#     trusted callers that bind identity out-of-band: the CLI command mode
#     (from an env var), the tests (from a fixture), and the LLM-facing
#     wrappers (from the session).
#
#   * LLM-facing wrappers (`*_tool`) are the ONLY functions registered with the
#     agent. They expose just the business parameters and read identity from the
#     authenticated session via `tool_context.invocation_state`. The model never
#     sees an actor field, so it cannot assert or change who it is acting for, 
#     not by being asked nicely, and not via prompt injection.
#
# This is the difference between an agent and a button: a button gets identity
# from the session cookie automatically; the agent must do the same. The model
# proposes intent; the system supplies identity.
# ---------------------------------------------------------------------------


def _session(tool_context: ToolContext) -> tuple[str | None, str | None]:
    """Pull trusted session facts (actor, db path) injected by the application.

    Returns (actor_customer_id, db_path). actor is None if there is no
    authenticated session, in which case wrappers fail closed.
    """
    state = getattr(tool_context, "invocation_state", None) or {}
    return state.get("actor_customer_id"), state.get("db_path")


# --- Read-only product catalog tools (no actor; safe to call directly) ------


@tool
def search_products(query: str, *, db_path: str | None = None) -> dict[str, Any]:
    """Search for products by keyword.

    Args:
        query: Free-text search string.
        db_path: Optional SQLite path (used by tests).
    """
    conn = db.connect(_db_path(db_path))
    try:
        like = f"%{query}%"
        rows = conn.execute(
            """
            SELECT sku, name, price_cents
            FROM products
            WHERE name LIKE ? OR description LIKE ?
            ORDER BY sku
            LIMIT 10
            """,
            (like, like),
        ).fetchall()
        items = [dict(r) for r in rows]
        return _ok(f"Found {len(items)} product(s).", items)
    finally:
        conn.close()


@tool
def list_products(*, db_path: str | None = None) -> dict[str, Any]:
    """List all products.

    Args:
        db_path: Optional SQLite path (used by tests).
    """
    conn = db.connect(_db_path(db_path))
    try:
        rows = conn.execute(
            """
            SELECT sku, name, price_cents
            FROM products
            ORDER BY sku
            """,
        ).fetchall()
        items = [dict(r) for r in rows]
        return _ok(f"Found {len(items)} product(s).", items)
    finally:
        conn.close()


@tool
def get_product_details(sku: str, *, db_path: str | None = None) -> dict[str, Any]:
    """Get product details by SKU (includes untrusted description text).

    Args:
        sku: The product SKU.
        db_path: Optional SQLite path (used by tests).
    """
    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute("SELECT sku, name, description, price_cents FROM products WHERE sku = ?", (sku,)).fetchone()
        if not row:
            return _err(f"Unknown SKU: {sku}")
        return _ok(f"Details for {sku}.", dict(row))
    finally:
        conn.close()


# --- Customer profile -------------------------------------------------------


def get_customer_profile(actor_customer_id: str, customer_id: str, *, db_path: str | None = None) -> dict[str, Any]:
    """Trusted core: fetch a customer profile on behalf of `actor_customer_id`.

    A customer may only read their own profile (Module 3 scoping).
    """
    d = policy.can_access_customer_data(actor_customer_id, customer_id)
    if not d.allowed:
        return _err(d.reason)

    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute(
            "SELECT customer_id, full_name, email, shipping_address FROM customers WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        if not row:
            return _err(f"Unknown customer_id: {customer_id}")
        # Module 5: reads of PII are sensitive and are audited too.
        db.audit(
            conn,
            actor_customer_id=actor_customer_id,
            action="view_customer_profile",
            details={"customer_id": customer_id},
        )
        return _ok(f"Profile for {customer_id}.", dict(row))
    finally:
        conn.close()


@tool(context=True, name="get_customer_profile")
def get_customer_profile_tool(customer_id: str, *, tool_context: ToolContext) -> dict[str, Any]:
    """Fetch a customer profile.

    Args:
        customer_id: The customer whose profile to fetch.
    """
    actor, db_path = _session(tool_context)
    if not actor:
        return _err("No authenticated session.")
    return get_customer_profile(actor, customer_id, db_path=db_path)


# --- Orders -----------------------------------------------------------------


def list_orders(actor_customer_id: str, customer_id: str | None = None, *, db_path: str | None = None) -> dict[str, Any]:
    """Trusted core: list orders for a customer on behalf of `actor_customer_id`.

    Args:
        actor_customer_id: The customer making the request (bound by the caller).
        customer_id: The customer ID to list orders for (defaults to the actor).
        db_path: Optional SQLite path (used by tests).
    """
    if customer_id is None:
        customer_id = actor_customer_id

    d = policy.can_access_customer_data(actor_customer_id, customer_id)
    if not d.allowed:
        return _err(d.reason)

    conn = db.connect(_db_path(db_path))
    try:
        rows = conn.execute(
            """
            SELECT order_id, sku, qty, total_cents, discount_percent, refunded_cents, status, created_at
            FROM orders
            WHERE customer_id = ?
            ORDER BY created_at DESC
            """,
            (customer_id,),
        ).fetchall()

        orders = [dict(r) for r in rows]
        if not orders:
            return _ok(f"No orders found for customer {customer_id}.", [])

        return _ok(f"Found {len(orders)} order(s) for customer {customer_id}.", orders)
    finally:
        conn.close()


@tool(context=True, name="list_orders")
def list_orders_tool(customer_id: str | None = None, *, tool_context: ToolContext) -> dict[str, Any]:
    """List orders for a customer.

    Args:
        customer_id: Customer to list orders for. Defaults to the current customer.
    """
    actor, db_path = _session(tool_context)
    if not actor:
        return _err("No authenticated session.")
    return list_orders(actor, customer_id, db_path=db_path)


# --- Refunds ----------------------------------------------------------------


def refund_order(
    actor_customer_id: str,
    order_id: str,
    refund_cents: int,
    *,
    db_path: str | None = None,
    approval_token: str | None = None,
) -> dict[str, Any]:
    """Trusted core: issue a refund on behalf of `actor_customer_id`.

    Ownership, the irreversibility approval requirement, and the amount cap are
    decided by policy.refund_policy (Modules 3 and 5). The approval token comes
    from the session, never the model.
    """
    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute(
            "SELECT order_id, customer_id, total_cents, refunded_cents, status FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if not row:
            return _err(f"Unknown order_id: {order_id}")

        d = policy.refund_policy(
            actor_customer_id,
            order_id,
            refund_cents,
            order_customer_id=row["customer_id"],
            order_total_cents=row["total_cents"],
        )
        if not d.allowed:
            return _err(d.reason)
        if d.requires_approval and not approval_token:
            return _err(f"Refund of order {order_id} requires human approval before it can be issued.")

        new_refunded = int(row["refunded_cents"]) + int(refund_cents)
        conn.execute(
            "UPDATE orders SET refunded_cents = ?, status = 'refunded' WHERE order_id = ?",
            (new_refunded, order_id),
        )
        conn.commit()

        db.audit(
            conn,
            actor_customer_id=actor_customer_id,
            action="refund_order",
            details={
                "order_id": order_id,
                "refund_cents": refund_cents,
                "new_refunded_cents": new_refunded,
                "approved": bool(approval_token),
            },
        )
        return _ok(f"Refunded {refund_cents} cents for {order_id}.", {"order_id": order_id, "refunded_cents": new_refunded})
    finally:
        conn.close()


@tool(context=True, name="refund_order")
def refund_order_tool(order_id: str, refund_cents: int, *, tool_context: ToolContext) -> dict[str, Any]:
    """Issue a refund for an order.

    Args:
        order_id: The order to refund.
        refund_cents: The refund amount in cents.
    """
    actor, db_path = _session(tool_context)
    if not actor:
        return _err("No authenticated session.")
    # The approval token, like the actor, comes only from the session -- a human
    # approving out-of-band. The model has no way to mint one.
    state = getattr(tool_context, "invocation_state", None) or {}
    return refund_order(actor, order_id, refund_cents, db_path=db_path, approval_token=state.get("approval_token"))


# --- Discounts --------------------------------------------------------------


def apply_discount(
    actor_customer_id: str,
    order_id: str,
    percent: int,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Trusted core: apply a discount on behalf of `actor_customer_id`.

    Ownership (Module 3) and the maximum-discount cap (Module 5) are enforced via
    policy.discount_policy. The action is audited (Module 5).
    """
    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute("SELECT order_id, customer_id FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not row:
            return _err(f"Unknown order_id: {order_id}")
        d = policy.discount_policy(actor_customer_id, order_id, percent, order_customer_id=row["customer_id"])
        if not d.allowed:
            return _err(d.reason)
        conn.execute("UPDATE orders SET discount_percent = ? WHERE order_id = ?", (int(percent), order_id))
        conn.commit()
        db.audit(
            conn,
            actor_customer_id=actor_customer_id,
            action="apply_discount",
            details={"order_id": order_id, "percent": int(percent)},
        )
        return _ok(f"Applied discount {percent}% to {order_id}.", {"order_id": order_id, "percent": int(percent)})
    finally:
        conn.close()


@tool(context=True, name="apply_discount")
def apply_discount_tool(order_id: str, percent: int, *, tool_context: ToolContext) -> dict[str, Any]:
    """Apply a discount percent to an order.

    Args:
        order_id: The order to discount.
        percent: The discount percentage.
    """
    actor, db_path = _session(tool_context)
    if not actor:
        return _err("No authenticated session.")
    return apply_discount(actor, order_id, percent, db_path=db_path)


# --- Email ------------------------------------------------------------------


def send_email(
    actor_customer_id: str,
    to_email: str,
    subject: str,
    body: str,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Trusted core: send an email on behalf of `actor_customer_id`.

    Module 3: email may only go to the company's own domain. Arbitrary external
    recipients are treated as exfiltration and refused. Only logs to the audit
    table (no real delivery).
    """
    d = policy.allowed_email_recipient(actor_customer_id, to_email)
    if not d.allowed:
        return _err(d.reason)

    conn = db.connect(_db_path(db_path))
    try:
        db.audit(
            conn,
            actor_customer_id=actor_customer_id,
            action="send_email",
            details={"to_email": to_email, "subject": subject, "body": body},
        )
        return _ok(f"Queued email to {to_email}.", {"to_email": to_email})
    finally:
        conn.close()


@tool(context=True, name="send_email")
def send_email_tool(to_email: str, subject: str, body: str, *, tool_context: ToolContext) -> dict[str, Any]:
    """Send an email.

    Args:
        to_email: Recipient address.
        subject: Email subject.
        body: Email body.
    """
    actor, db_path = _session(tool_context)
    if not actor:
        return _err("No authenticated session.")
    return send_email(actor, to_email, subject, body, db_path=db_path)
