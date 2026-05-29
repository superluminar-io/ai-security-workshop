from __future__ import annotations

import logging
import os
import threading
from typing import Any

import db
from prompts import SYSTEM_PROMPT
import tools as ecomm_tools

from bedrock_agentcore.runtime import BedrockAgentCoreApp

logger = logging.getLogger(__name__)

DB_PATH = "/tmp/ecomm.sqlite"
MODEL_ID = os.environ.get("STRANDS_MODEL", "eu.amazon.nova-2-lite-v1:0")

db.initialize(DB_PATH)

app = BedrockAgentCoreApp()

_agent = None
_agent_lock = threading.Lock()


def _get_agent():
    global _agent
    if _agent is None:
        with _agent_lock:
            if _agent is None:
                from strands import Agent
                from strands.models import BedrockModel

                model = BedrockModel(model_id=MODEL_ID, max_tokens=3000)
                _agent = Agent(
                    model=model,
                    system_prompt=SYSTEM_PROMPT,
                    callback_handler=None,
                    tools=[
                        ecomm_tools.search_products,
                        ecomm_tools.list_products,
                        ecomm_tools.get_product_details,
                        ecomm_tools.get_customer_profile,
                        ecomm_tools.list_orders,
                        ecomm_tools.refund_order,
                        ecomm_tools.apply_discount,
                        ecomm_tools.send_email,
                    ],
                )
    return _agent


def _extract_text(result: Any) -> str:
    try:
        msg = result.message if hasattr(result, "message") else result
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", []) or []
        if isinstance(content, list) and content and isinstance(content[0], dict):
            return content[0].get("text", "")
    except Exception as exc:
        logger.warning("Failed to extract text from agent result: %s", exc)
    return ""


def _handle(payload: dict) -> dict:
    agent = _get_agent()
    message = payload.get("prompt", "")
    actor_customer_id = payload.get("actorCustomerId", "cust_001")
    result = agent(
        message,
        invocation_state={"actor_customer_id": actor_customer_id, "db_path": DB_PATH},
    )
    return {"result": _extract_text(result)}


@app.entrypoint
def invoke(payload: dict) -> dict:
    return _handle(payload)


if __name__ == "__main__":
    app.run()
