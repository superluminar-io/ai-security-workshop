from __future__ import annotations

import os

import tools as ecomm_tools
from prompts import SYSTEM_PROMPT

MODEL_ID = "eu.amazon.nova-2-lite-v1:0"

# The tools registered with the agent. Read-only catalog tools carry no identity;
# the identity-bearing operations are the `*_tool` wrappers, which take the actor
# from the session, never from the model (Module 2).
AGENT_TOOLS = [
    ecomm_tools.search_products,
    ecomm_tools.list_products,
    ecomm_tools.get_product_details,
    ecomm_tools.get_customer_profile_tool,
    ecomm_tools.list_orders_tool,
    ecomm_tools.refund_order_tool,
    ecomm_tools.apply_discount_tool,
    ecomm_tools.send_email_tool,
]


def build_model():
    """Return the model for the agent.

    If BEDROCK_GUARDRAIL_ID is set (Module 4), the model is wrapped in a Bedrock
    Guardrail. A guardrail is a *probabilistic* Layer-2 mitigation: it lowers the
    rate of harmful inputs/outputs but cannot be a boundary, because it is itself
    a model. The boundary lives in tools.py/policy.py and holds regardless of
    what either model does.
    """
    model_id = os.environ.get("STRANDS_MODEL") or MODEL_ID
    guardrail_id = os.environ.get("BEDROCK_GUARDRAIL_ID")
    if not guardrail_id:
        return model_id

    from strands.models import BedrockModel

    return BedrockModel(
        model_id=model_id,
        guardrail_id=guardrail_id,
        guardrail_version=os.environ.get("BEDROCK_GUARDRAIL_VERSION", "DRAFT"),
        guardrail_trace="enabled",
    )


def build_agent(system_prompt: str | None = None, model=None):
    """Construct the Strands agent. Imported lazily so non-LLM code paths and the
    test suite do not require strands or AWS credentials.

    `system_prompt` overrides the default prompt (the Module 1 framing demo uses
    it). `model` overrides the model provider; tests pass a `ScriptedModel` to
    drive the real agent loop deterministically with no Bedrock. Callers normally
    omit both.
    """
    from strands import Agent

    return Agent(
        model=model if model is not None else build_model(),
        system_prompt=SYSTEM_PROMPT if system_prompt is None else system_prompt,
        callback_handler=None,
        tools=list(AGENT_TOOLS),
    )
