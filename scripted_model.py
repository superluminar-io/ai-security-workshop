"""A model you control, for driving the real agent loop deterministically.

This is NOT a realistic attacker (nobody swaps out your model). It is a
verification device: it emits a fixed sequence of tool calls so a test can run
them through the *real* agent, tool registration, dispatch, and invocation_state
included, with no Bedrock. That lets us check the deterministic boundary is
actually wired into the request path, not merely present in the cores.

Used by tests/test_wiring.py. It proves a control is *enabled in the live path*,
never that the system is "safe".
"""

from __future__ import annotations

import json
from typing import Any

from strands.models.model import Model


class ScriptedModel(Model):
    """Emit the given tool calls, one per turn, then end the conversation.

    Args:
        tool_calls: list of (tool_name, input_dict) the "model" will emit.
    """

    def __init__(self, tool_calls: list[tuple[str, dict]]):
        self._tool_calls = list(tool_calls)
        self._i = 0

    def update_config(self, **model_config: Any) -> None:
        pass

    def get_config(self) -> dict:
        return {}

    async def structured_output(self, *args: Any, **kwargs: Any):
        raise NotImplementedError("ScriptedModel does not support structured_output")
        yield  # pragma: no cover  (keeps this an async generator)

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        if self._i < len(self._tool_calls):
            name, tool_input = self._tool_calls[self._i]
            self._i += 1
            tool_use_id = f"scripted-{self._i}"
            yield {"messageStart": {"role": "assistant"}}
            yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": tool_use_id, "name": name}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(tool_input)}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"messageStart": {"role": "assistant"}}
            yield {"contentBlockDelta": {"delta": {"text": "done"}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
