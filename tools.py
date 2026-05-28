from __future__ import annotations

import os
from typing import Any

import db

try:
    from strands import tool
    from strands.types.tools import ToolContext
except Exception:  # pragma: no cover - allows running without strands installed

    def tool(fn=None, **_kwargs):  # type: ignore[misc]
        if fn is None:
            return lambda f: f
        return fn

    ToolContext = Any  # type: ignore[assignment,misc]


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
# WORKSHOP BASELINE -- intentionally insecure. See workshop/ for the modules
# that fix this. The tests in tests/ encode the SECURE target behavior, so they
# are EXPECTED TO FAIL against this file until you do the work.
#
# Each identity-bearing operation has a trusted core plus an LLM-facing
# `*_tool` wrapper. In this baseline the wrappers leak authority in two ways the
# modules will fix:
#   * the actor identity is a tool parameter the MODEL fills in (Module 2), and
#   * no policy is enforced in the cores (Module 3), no caps/audit (Module 5).
# ---------------------------------------------------------------------------


# --- Read-only product catalog tools (no actor) ----------------------------


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
    """Trusted core: fetch a customer profile.

    INSECURE BASELINE: no access scoping -- any actor can read any customer's PII.
    """
    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute(
            "SELECT customer_id, full_name, email, shipping_address FROM customers WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        if not row:
            return _err(f"Unknown customer_id: {customer_id}")
        return _ok(f"Profile for {customer_id}.", dict(row))
    finally:
        conn.close()


@tool(context=True, name="get_customer_profile")
def get_customer_profile_tool(
    customer_id: str, actor_customer_id: str = "cust_001", *, tool_context: ToolContext
) -> dict[str, Any]:
    """Fetch a customer profile.

    Args:
        customer_id: The customer whose profile to fetch.
        actor_customer_id: The customer making the request.
    """
    # INSECURE BASELINE: identity comes from the model-supplied argument.
    return get_customer_profile(actor_customer_id, customer_id, db_path=tool_context.invocation_state.get("db_path"))


# --- Orders -----------------------------------------------------------------


def list_orders(actor_customer_id: str, customer_id: str | None = None, *, db_path: str | None = None) -> dict[str, Any]:
    """Trusted core: list orders for a customer.

    INSECURE BASELINE: no scoping -- lists any customer's orders if you name them.
    """
    if customer_id is None:
        customer_id = actor_customer_id

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
def list_orders_tool(
    customer_id: str | None = None, actor_customer_id: str = "cust_001", *, tool_context: ToolContext
) -> dict[str, Any]:
    """List orders for a customer.

    Args:
        customer_id: Customer to list orders for. Defaults to the current customer.
        actor_customer_id: The customer making the request.
    """
    # INSECURE BASELINE: identity comes from the model-supplied argument.
    return list_orders(actor_customer_id, customer_id, db_path=tool_context.invocation_state.get("db_path"))


# --- Refunds ----------------------------------------------------------------


def refund_order(
    actor_customer_id: str,
    order_id: str,
    refund_cents: int,
    *,
    db_path: str | None = None,
    approval_token: str | None = None,
) -> dict[str, Any]:
    """Trusted core: issue a refund.

    INSECURE BASELINE: refunds any order, any amount, no ownership check, no
    approval, no cap, no audit. (`approval_token` is accepted but ignored.)
    """
    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute(
            "SELECT order_id, customer_id, total_cents, refunded_cents, status FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if not row:
            return _err(f"Unknown order_id: {order_id}")

        new_refunded = int(row["refunded_cents"]) + int(refund_cents)
        conn.execute(
            "UPDATE orders SET refunded_cents = ?, status = 'refunded' WHERE order_id = ?",
            (new_refunded, order_id),
        )
        conn.commit()
        return _ok(f"Refunded {refund_cents} cents for {order_id}.", {"order_id": order_id, "refunded_cents": new_refunded})
    finally:
        conn.close()


@tool(context=True, name="refund_order")
def refund_order_tool(
    order_id: str, refund_cents: int, actor_customer_id: str = "cust_001", *, tool_context: ToolContext
) -> dict[str, Any]:
    """Issue a refund for an order.

    Args:
        order_id: The order to refund.
        refund_cents: The refund amount in cents.
        actor_customer_id: The customer making the request.
    """
    # INSECURE BASELINE: identity comes from the model-supplied argument.
    return refund_order(actor_customer_id, order_id, refund_cents, db_path=tool_context.invocation_state.get("db_path"))


# --- Discounts --------------------------------------------------------------


def apply_discount(
    actor_customer_id: str,
    order_id: str,
    percent: int,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Trusted core: apply a discount.

    INSECURE BASELINE: any order, any percentage, no ownership check, no cap, no audit.
    """
    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute("SELECT order_id FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not row:
            return _err(f"Unknown order_id: {order_id}")
        conn.execute("UPDATE orders SET discount_percent = ? WHERE order_id = ?", (int(percent), order_id))
        conn.commit()
        return _ok(f"Applied discount {percent}% to {order_id}.", {"order_id": order_id, "percent": int(percent)})
    finally:
        conn.close()


@tool(context=True, name="apply_discount")
def apply_discount_tool(
    order_id: str, percent: int, actor_customer_id: str = "cust_001", *, tool_context: ToolContext
) -> dict[str, Any]:
    """Apply a discount percent to an order.

    Args:
        order_id: The order to discount.
        percent: The discount percentage.
        actor_customer_id: The customer making the request.
    """
    # INSECURE BASELINE: identity comes from the model-supplied argument.
    return apply_discount(actor_customer_id, order_id, percent, db_path=tool_context.invocation_state.get("db_path"))


# --- Email ------------------------------------------------------------------


def send_email(
    actor_customer_id: str,
    to_email: str,
    subject: str,
    body: str,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Trusted core: send an email.

    INSECURE BASELINE: emails any address (exfiltration). Only logs to the audit
    table (no real delivery).
    """
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
def send_email_tool(
    to_email: str, subject: str, body: str, actor_customer_id: str = "cust_001", *, tool_context: ToolContext
) -> dict[str, Any]:
    """Send an email.

    Args:
        to_email: Recipient address.
        subject: Email subject.
        body: Email body.
        actor_customer_id: The customer making the request.
    """
    # INSECURE BASELINE: identity comes from the model-supplied argument.
    return send_email(actor_customer_id, to_email, subject, body, db_path=tool_context.invocation_state.get("db_path"))
