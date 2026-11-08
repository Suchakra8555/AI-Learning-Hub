"""Test an agent's behaviour with LiveKit's test framework. No server, no audio, no key.

Run:  pytest -q test_agent.py
"""
import pytest
from livekit.agents import Agent, AgentSession, RunContext, function_tool, mock_tools

from scripted_llm import ScriptedLLM


class Support(Agent):
    def __init__(self):
        super().__init__(instructions="You help callers check their orders.")

    @function_tool
    async def lookup_order(self, ctx: RunContext, order_id: str) -> dict:
        """Look up an order's status by its id."""
        return {"order_id": order_id, "status": "shipped"}   # shortcut: real code calls your backend


@pytest.mark.asyncio
async def test_calls_the_tool_and_reads_the_result():
    async with AgentSession(llm=ScriptedLLM()) as session:
        await session.start(Support())
        result = await session.run(user_input="Where is order 4417?")
        result.expect.next_event().is_function_call(name="lookup_order", arguments={"order_id": "4417"})
        result.expect.next_event().is_function_call_output()
        result.expect.next_event().is_message(role="assistant")
        result.expect.no_more_events()
        assert "shipped" in session.history.items[-1].text_content


@pytest.mark.asyncio
async def test_with_a_mocked_tool():
    async with AgentSession(llm=ScriptedLLM()) as session:
        await session.start(Support())
        # mocks get the real tool's positional args in order, ctx first. `lambda order_id:` would get the RunContext.
        with mock_tools(Support, {"lookup_order": lambda ctx, order_id: {"order_id": order_id, "status": "delayed"}}):
            result = await session.run(user_input="Where is order 9?")
        result.expect.contains_function_call(name="lookup_order")
        assert "delayed" in session.history.items[-1].text_content


@pytest.mark.asyncio
async def test_small_talk_needs_no_tool():
    async with AgentSession(llm=ScriptedLLM()) as session:
        await session.start(Support())
        result = await session.run(user_input="hello")
        result.expect.next_event().is_message(role="assistant")
        result.expect.no_more_events()
