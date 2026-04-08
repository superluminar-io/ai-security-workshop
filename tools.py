from __future__ import annotations

import logging
import os
from typing import Any

import db
import policy

logger = logging.getLogger(__name__)

try:
    from strands import tool
except Exception:  # pragma: no cover - allows running without strands installed

    def tool(fn=None, **_kwargs):  # type: ignore[misc]
        if fn is None:
            return lambda f: f
        return fn


DEFAULT_DB_PATH = os.environ.get("ECOMM_DB", "ecomm.sqlite")


def _db_path(db_path: str | None) -> str:
    return db_path or DEFAULT_DB_PATH


def _ok(text: str, data: Any | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"status": "success", "content": [{"text": text}]}
    if data is not None:
        out["data"] = data
    return out


def _err(text: str, data: Any | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"status": "error", "content": [{"text": text}]}
    if data is not None:
        out["data"] = data
    return out


@tool
def search_products(query: str, *, db_path: str | None = None) -> dict[str, Any]:
    """Search for products by keyword.

    Args:
        query: Free-text search string.
        db_path: Optional SQLite path (used by tests).
    """
    logger.debug(f"search_products called with query: {query}")
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
        logger.debug(f"search_products found {len(items)} products")
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
    raise Exception("Not executed")
    logger.debug(f"get_product_details called for SKU: {sku}")
    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute("SELECT sku, name, description, price_cents FROM products WHERE sku = ?", (sku,)).fetchone()
        if not row:
            logger.warning(f"Product not found for SKU: {sku}")
            return _err(f"Unknown SKU: {sku}")
        logger.debug(f"get_product_details returning details for SKU: {sku}")
        return _ok(f"Details for {sku}.", dict(row))
    finally:
        conn.close()


@tool
def get_customer_profile(actor_customer_id: str, customer_id: str, *, db_path: str | None = None) -> dict[str, Any]:
    """Fetch a customer profile.

    INSECURE BASELINE: does not scope access to the actor; leaks PII.
    """
    logger.debug(f"get_customer_profile called: actor={actor_customer_id}, target_customer={customer_id}")
    _ = policy.authorize_tool_call(actor_customer_id, "get_customer_profile", {"customer_id": customer_id})

    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute(
            "SELECT customer_id, full_name, email, shipping_address FROM customers WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        if not row:
            logger.warning(f"Customer not found: {customer_id}")
            return _err(f"Unknown customer_id: {customer_id}")
        logger.debug(f"get_customer_profile returning profile for customer: {customer_id}")
        return _ok(f"Profile for {customer_id}.", dict(row))
    finally:
        conn.close()


@tool
def refund_order(
    actor_customer_id: str,
    order_id: str,
    refund_cents: int,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Issue a refund for an order.

    INSECURE BASELINE: refunds any order, any amount, no approvals.
    """
    logger.debug(f"refund_order called: actor={actor_customer_id}, order={order_id}, amount={refund_cents}")
    _ = policy.authorize_tool_call(
        actor_customer_id, "refund_order", {"order_id": order_id, "refund_cents": refund_cents}
    )

    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute(
            "SELECT order_id, customer_id, total_cents, refunded_cents, status FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if not row:
            logger.warning(f"Order not found for refund: {order_id}")
            return _err(f"Unknown order_id: {order_id}")

        # intentionally minimal + insecure
        new_refunded = int(row["refunded_cents"]) + int(refund_cents)
        logger.info(f"Processing refund: order={order_id}, amount={refund_cents}, total_refunded={new_refunded}")
        conn.execute(
            "UPDATE orders SET refunded_cents = ?, status = 'refunded' WHERE order_id = ?",
            (new_refunded, order_id),
        )
        conn.commit()

        # inconsistent audit: we log refunds, but without any approvals or redaction
        db.audit(
            conn,
            actor_customer_id=actor_customer_id,
            action="refund_order",
            details={"order_id": order_id, "refund_cents": refund_cents, "new_refunded_cents": new_refunded},
        )
        logger.debug(f"Refund processed successfully for order: {order_id}")
        return _ok(f"Refunded {refund_cents} cents for {order_id}.", {"order_id": order_id, "refunded_cents": new_refunded})
    finally:
        conn.close()


@tool
def apply_discount(
    actor_customer_id: str,
    order_id: str,
    percent: int,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Apply a discount percent to an order.

    INSECURE BASELINE: allows extreme discounts (e.g., 90%).
    """
    logger.debug(f"apply_discount called: actor={actor_customer_id}, order={order_id}, percent={percent}")
    _ = policy.authorize_tool_call(actor_customer_id, "apply_discount", {"order_id": order_id, "percent": percent})

    conn = db.connect(_db_path(db_path))
    try:
        row = conn.execute("SELECT order_id FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not row:
            logger.warning(f"Order not found for discount: {order_id}")
            return _err(f"Unknown order_id: {order_id}")
        logger.info(f"Applying discount: order={order_id}, percent={percent}")
        conn.execute("UPDATE orders SET discount_percent = ? WHERE order_id = ?", (int(percent), order_id))
        conn.commit()
        logger.debug(f"Discount applied successfully for order: {order_id}")
        return _ok(f"Applied discount {percent}% to {order_id}.", {"order_id": order_id, "percent": int(percent)})
    finally:
        conn.close()


@tool
def send_email(
    actor_customer_id: str,
    to_email: str,
    subject: str,
    body: str,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Send an email.

    INSECURE BASELINE: allows emailing arbitrary external addresses (exfiltration).
    This implementation only logs to the audit table (no real email delivery).
    """
    logger.debug(f"send_email called: actor={actor_customer_id}, to_email={to_email}, subject={subject}")
    _ = policy.authorize_tool_call(
        actor_customer_id, "send_email", {"to_email": to_email, "subject": subject, "body": body}
    )

    conn = db.connect(_db_path(db_path))
    try:
        logger.info(f"Sending email: to={to_email}, subject={subject}")
        db.audit(
            conn,
            actor_customer_id=actor_customer_id,
            action="send_email",
            details={"to_email": to_email, "subject": subject, "body": body},
        )
        logger.debug(f"Email queued successfully to: {to_email}")
        return _ok(f"Queued email to {to_email}.", {"to_email": to_email})
    finally:
        conn.close()

