from __future__ import annotations

import json
import os
from typing import Any

import db
from prompts import SYSTEM_PROMPT

import tools as ecomm_tools
from wrap import make_tool

ACTOR_CUSTOMER_ID = os.environ.get("ACTOR_CUSTOMER_ID", "cust_001")
DB_PATH = os.environ.get("ECOMM_DB", "ecomm.sqlite")

# Model ID for LLM mode (Bedrock). Override with STRANDS_MODEL env var if needed.
MODEL_ID = "eu.amazon.nova-2-lite-v1:0"


def _print_result(result: dict[str, Any]) -> None:
    status = result.get("status", "unknown")
    blocks = result.get("content") or []
    text = ""
    if isinstance(blocks, list) and blocks and isinstance(blocks[0], dict):
        text = blocks[0].get("text", "")
    print(f"[{status}] {text}".strip())
    if "data" in result:
        print(json.dumps(result["data"], indent=2, sort_keys=True))


def _command_mode() -> None:
    print("Insecure e-commerce assistant (workshop baseline)")
    print(f"DB: {DB_PATH}")
    print(f"Logged in as: {ACTOR_CUSTOMER_ID}")
    print("")
    print("Commands:")
    print("  search <query>")
    print("  product <sku>")
    print("  profile <customer_id>")
    print("  orders [customer_id]")
    print("  refund <order_id> <refund_cents>")
    print("  discount <order_id> <percent>")
    print("  email <to_email> <subject> | <body>")
    print("  quit")
    print("")

    while True:
        raw = input("> ").strip()
        if not raw:
            continue
        if raw in {"q", "quit", "exit"}:
            break

        try:
            if raw.startswith("search "):
                q = raw.removeprefix("search ").strip()
                _print_result(ecomm_tools.search_products(q, db_path=DB_PATH))
            elif raw.startswith("product "):
                sku = raw.removeprefix("product ").strip()
                _print_result(ecomm_tools.get_product_details(sku, db_path=DB_PATH))
            elif raw.startswith("profile "):
                cid = raw.removeprefix("profile ").strip()
                _print_result(ecomm_tools.get_customer_profile(ACTOR_CUSTOMER_ID, cid, db_path=DB_PATH))
            elif raw.startswith("orders"):
                cid = raw.removeprefix("orders").strip()
                _print_result(ecomm_tools.list_orders(ACTOR_CUSTOMER_ID, cid if cid else None, db_path=DB_PATH))
            elif raw.startswith("refund "):
                parts = raw.split()
                if len(parts) != 3:
                    raise ValueError("Usage: refund <order_id> <refund_cents>")
                _print_result(
                    ecomm_tools.refund_order(ACTOR_CUSTOMER_ID, parts[1], int(parts[2]), db_path=DB_PATH)
                )
            elif raw.startswith("discount "):
                parts = raw.split()
                if len(parts) != 3:
                    raise ValueError("Usage: discount <order_id> <percent>")
                _print_result(ecomm_tools.apply_discount(ACTOR_CUSTOMER_ID, parts[1], int(parts[2]), db_path=DB_PATH))
            elif raw.startswith("email "):
                payload = raw.removeprefix("email ").strip()
                if "|" not in payload:
                    raise ValueError("Usage: email <to_email> <subject> | <body>")
                left, body = payload.split("|", 1)
                left_parts = left.strip().split(" ", 1)
                if len(left_parts) != 2:
                    raise ValueError("Usage: email <to_email> <subject> | <body>")
                to_email, subject = left_parts[0].strip(), left_parts[1].strip()
                _print_result(
                    ecomm_tools.send_email(ACTOR_CUSTOMER_ID, to_email, subject, body.strip(), db_path=DB_PATH)
                )
            else:
                print("Unknown command. Try `search <query>` or `quit`.")
        except Exception as e:
            print(f"[error] {type(e).__name__}: {e}")


def _llm_mode() -> None:
    from strands import Agent  # type: ignore[import-not-found]  # imported only when needed

    model = os.environ.get("STRANDS_MODEL") or MODEL_ID
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        callback_handler=None,
        tools=[
            ecomm_tools.search_products,
            ecomm_tools.list_products,
            ecomm_tools.get_product_details,
            make_tool(ecomm_tools.get_customer_profile_provider, ACTOR_CUSTOMER_ID),
            ecomm_tools.list_orders,
            ecomm_tools.refund_order,
            ecomm_tools.apply_discount,
            ecomm_tools.send_email,
        ],
    )

    print("LLM mode enabled. Type messages; `quit` to exit.")
    print(f"Logged in as: {ACTOR_CUSTOMER_ID}")
    print("")
    while True:
        raw = input("> ").strip()
        if not raw:
            continue
        if raw in {"q", "quit", "exit"}:
            break
        result = agent(raw, invocation_state={"actor_customer_id": ACTOR_CUSTOMER_ID, "db_path": DB_PATH})
        # AgentResult has a message with content blocks; print best-effort
        try:
            msg = result["message"]
            content = msg.get("content") or []
            text = ""
            if isinstance(content, list) and content and isinstance(content[0], dict):
                text = content[0].get("text", "")
            print(text)
        except Exception:
            print(result)


def main() -> None:
    db.initialize(DB_PATH)
    # Default to LLM mode, but allow opting out.
    if os.environ.get("ENABLE_LLM") != "0":
        try:
            _llm_mode()
            return
        except Exception as e:
            print(
                f"[warn] LLM mode unavailable ({type(e).__name__}: {e}). "
                "Falling back to command mode. "
                "Set ENABLE_LLM=0 to skip trying LLM mode.\n"
            )
    _command_mode()


if __name__ == "__main__":
    main()

