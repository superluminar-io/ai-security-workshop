from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from strands.agent.agent_result import AgentResult

import db
from prompts import SYSTEM_PROMPT

import tools as ecomm_tools

logger = logging.getLogger(__name__)

ACTOR_CUSTOMER_ID = os.environ.get("ACTOR_CUSTOMER_ID", "cust_001")
DB_PATH = os.environ.get("ECOMM_DB", "ecomm.sqlite")

# Model ID for LLM mode (Bedrock). Override with STRANDS_MODEL env var if needed.
MODEL_ID = "eu.meta.llama3-2-3b-instruct-v1:0"


def _print_result(result: dict[str, Any]) -> None:
    status = result.get("status", "unknown")
    blocks = result.get("content") or []
    text = ""
    if isinstance(blocks, list) and blocks and isinstance(blocks[0], dict):
        text = blocks[0].get("text", "")
    print(f"[{status}] {text}".strip())
    if "data" in result:
        print(json.dumps(result["data"], indent=2, sort_keys=True))
    logger.debug(f"Result: status={status}, has_data={'data' in result}")


def _command_mode() -> None:
    logger.info("Entering command mode")
    logger.debug(f"Database path: {DB_PATH}, Actor: {ACTOR_CUSTOMER_ID}")
    print("Insecure e-commerce assistant (workshop baseline)")
    print(f"DB: {DB_PATH}")
    print(f"Logged in as: {ACTOR_CUSTOMER_ID}")
    print("")
    print("Commands:")
    print("  search <query>")
    print("  product <sku>")
    print("  profile <customer_id>")
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
                logger.debug(f"Executing search command with query: {q}")
                _print_result(ecomm_tools.search_products(q, db_path=DB_PATH))
            elif raw.startswith("product "):
                sku = raw.removeprefix("product ").strip()
                logger.debug(f"Executing product command for SKU: {sku}")
                _print_result(ecomm_tools.get_product_details(sku, db_path=DB_PATH))
            elif raw.startswith("profile "):
                cid = raw.removeprefix("profile ").strip()
                logger.debug(f"Executing profile command for customer: {cid}")
                _print_result(ecomm_tools.get_customer_profile(ACTOR_CUSTOMER_ID, cid, db_path=DB_PATH))
            elif raw.startswith("refund "):
                parts = raw.split()
                if len(parts) != 3:
                    raise ValueError("Usage: refund <order_id> <refund_cents>")
                logger.debug(f"Executing refund command for order: {parts[1]}, amount: {parts[2]}")
                _print_result(
                    ecomm_tools.refund_order(ACTOR_CUSTOMER_ID, parts[1], int(parts[2]), db_path=DB_PATH)
                )
            elif raw.startswith("discount "):
                parts = raw.split()
                if len(parts) != 3:
                    raise ValueError("Usage: discount <order_id> <percent>")
                logger.debug(f"Executing discount command for order: {parts[1]}, percent: {parts[2]}")
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
                logger.debug(f"Executing email command to: {to_email}, subject: {subject}")
                _print_result(
                    ecomm_tools.send_email(ACTOR_CUSTOMER_ID, to_email, subject, body.strip(), db_path=DB_PATH)
                )
            else:
                print("Unknown command. Try `search <query>` or `quit`.")
        except Exception as e:
            logger.exception(f"Command execution failed: {type(e).__name__}")
            print(f"[error] {type(e).__name__}: {e}")


def _llm_mode() -> None:
    from strands import Agent  # type: ignore[import-not-found]  # imported only when needed
    from strands.models.sagemaker import SageMakerAIModel


    logger.info("Entering LLM mode")
    model_id = os.environ.get("STRANDS_MODEL") or MODEL_ID
    logger.debug(f"Using LLM model: {model_id}")

    model = SageMakerAIModel(
        endpoint_config={
            "endpoint_name": "huggingface-pytorch-tgi-inference-2026-04-08-13-07-06-328",
            "region_name": "eu-central-1",
            },
        payload_config={
            "max_tokens": 1000,
            "temperature": 0.7,
            "stream": True,
        },
    )

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        callback_handler=None,

        tools=[
            ecomm_tools.search_products,
            ecomm_tools.get_product_details,
            ecomm_tools.get_customer_profile,
            ecomm_tools.refund_order,
            ecomm_tools.apply_discount,
            ecomm_tools.send_email,
        ],
    )
    logger.debug("Agent initialized with 6 tools")

    print("LLM mode enabled. Type messages; `quit` to exit.")
    print(f"Logged in as: {ACTOR_CUSTOMER_ID}")
    print("")
    while True:
        raw = input("> ").strip()
        if not raw:
            continue
        if raw in {"q", "quit", "exit"}:
            logger.info("User exiting LLM mode")
            break
        logger.debug(f"Processing LLM user input: {raw[:100]}...")
        result: AgentResult = agent(raw, invocation_state={"actor_customer_id": ACTOR_CUSTOMER_ID, "db_path": DB_PATH})

        def result_msg(result) -> str:
            if isinstance(result, str):
                return result
            result = result.__dict__ if isinstance(result, AgentResult) else result
            print(json.dumps(result, indent=2, default=str))
            print(f"type of arg: {type(result)}, keys: { result.keys()}")
            msg = result["message"]
            content = msg.get("content") or []
            text = msg
            text=json.dumps(msg)
            return text
            if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
                text = content[0].get("text", "")

            return text

        o = json.dumps(result, default=str, indent=2)
        with open("last_agent_result.json", "w") as f:
            f.write(o)
        logger.debug(f"Agent returned result with status: {json.dumps(result, default=str, indent=2)}")
        # AgentResult has a message with content blocks; print best-effort
        try:
            text = result_msg(result)
            print(text)
        except Exception as e:
            logger.exception("Error processing agent result")
            print(result)


def _setup_logging() -> None:
    """Configure logging based on LOG_LEVEL environment variable (default: INFO)."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info(f"Logging configured with level: {log_level}")


def main() -> None:
    _setup_logging()
    logger.info("Application starting")
    logger.debug(f"Database path: {DB_PATH}, Actor customer ID: {ACTOR_CUSTOMER_ID}")

    db.initialize(DB_PATH)
    logger.debug("Database initialized")

    # Default to LLM mode, but allow opting out.
    if os.environ.get("ENABLE_LLM") != "0":
        try:
            logger.info("Attempting to start LLM mode")
            _llm_mode()
            return
        except Exception as e:
            logger.warning(
                f"LLM mode unavailable ({type(e).__name__}: {e}). Falling back to command mode. "
                "Set ENABLE_LLM=0 to skip trying LLM mode.",
                exc_info=True
            )
            print(
                f"[warn] LLM mode unavailable ({type(e).__name__}: {e}). "
                "Falling back to command mode. "
                "Set ENABLE_LLM=0 to skip trying LLM mode.\n"
            )
    logger.info("Starting command mode")
    _command_mode()
    logger.info("Application shutting down")


if __name__ == "__main__":
    main()

