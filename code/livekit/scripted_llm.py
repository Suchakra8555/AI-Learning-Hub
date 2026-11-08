"""A fake LLM that follows a script, so agent tests run with no API key.

It implements the same plugin interface as the OpenAI or Anthropic plugins:
an LLM whose chat() returns an LLMStream that pushes ChatChunks.
# shortcut: two hard-coded rules. Real tests use a real model, or a judge.
"""
import json
import re
import uuid

from livekit.agents import APIConnectOptions, llm
from livekit.agents.llm import ChatChunk, ChoiceDelta, FunctionToolCall


class ScriptedLLM(llm.LLM):
    def chat(self, *, chat_ctx, tools=None, conn_options=APIConnectOptions(), **_):
        return _Stream(self, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options)


class _Stream(llm.LLMStream):
    async def _run(self) -> None:
        last = self._chat_ctx.items[-1]
        if last.type == "function_call_output":                       # rule 2: speak the tool result
            status = re.search(r"status.{0,4}?(\w+)", last.output).group(1)  # output arrives as text
            text = f"Your order is {status}."
            self._event_ch.send_nowait(ChatChunk(id="1", delta=ChoiceDelta(role="assistant", content=text)))
            return
        said = last.text_content or "" if last.type == "message" else ""
        m = re.search(r"order (\d+)", said)
        if m:                                                          # rule 1: call the tool
            call = FunctionToolCall(name="lookup_order", arguments=json.dumps({"order_id": m.group(1)}),
                                    call_id=uuid.uuid4().hex[:8])
            self._event_ch.send_nowait(ChatChunk(id="1", delta=ChoiceDelta(role="assistant", tool_calls=[call])))
            return
        self._event_ch.send_nowait(ChatChunk(id="1", delta=ChoiceDelta(role="assistant", content="How can I help?")))
