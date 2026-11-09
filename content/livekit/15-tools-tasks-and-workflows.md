---
title: Tools, tasks and workflows
summary: How an agent does things instead of just talking. Function tools and the loop that runs them, async tools, MCP, tasks with typed results, handoffs, task groups, and the prebuilt pieces, with real output from the lab tests.
time: 30 min
---

Your agent answers questions well. Then a caller says "cancel order 4417", and you need it to call your backend, wait, read back the result, and not cancel the wrong order because someone coughed. Next week product wants a consent step before every call and a billing specialist that takes over for refunds. One long prompt can't do all of that reliably. This lesson covers the pieces LiveKit Agents gives you: **tools** (functions the LLM can call), **tasks** (short sub-conversations that return a typed result), and **handoffs** (passing the whole session to another agent). Versions: `livekit-agents` 1.8.11, Python. Everything here runs inside the agent process, so it works the same on a self-hosted server.

## Function tools

A **function tool** is an `async` method with the `@function_tool` decorator. The function name becomes the tool name, the docstring becomes the description, and the type hints become the argument schema ([Function tools](https://docs.livekit.io/agents/logic/tools/definition)). The first argument after `self` is a **`RunContext`**, which gives the tool the `session`, the `function_call`, the `speech_handle` and your `userdata`. Here is the tool from `code/livekit/test_agent.py`:

```python
class Support(Agent):
    def __init__(self):
        super().__init__(instructions="You help callers check their orders.")

    @function_tool
    async def lookup_order(self, ctx: RunContext, order_id: str) -> dict:
        """Look up an order's status by its id."""
        return {"order_id": order_id, "status": "shipped"}   # shortcut: real code calls your backend
```

The return value is turned into a string before the LLM sees it. Returning `None` finishes the tool silently with no reply. The lab tests drive it offline with a scripted fake LLM (see [Testing and observability](lesson:livekit/testing-and-observability)). Real output, `out/test_agent.txt`:

```text
test_agent.py::test_calls_the_tool_and_reads_the_result PASSED           [ 33%]
test_agent.py::test_with_a_mocked_tool PASSED                            [ 66%]
test_agent.py::test_small_talk_needs_no_tool PASSED                      [100%]
============================== 3 passed in 2.40s ===============================
```

The first test checks the exact event order: `function_call`, then `function_call_output`, then an assistant message. Errors go back to the model too. Raise **`ToolError`** (from `livekit.agents.llm`) with a message the model can act on. Any other exception becomes a generic message, so server details don't leak into the call ([error handling](https://docs.livekit.io/agents/logic/tools/definition#error-handling)). We checked both on a scratch copy of the tests: a `ToolError("No order 0. Ask the caller to read the number again.")` reached the model as that exact text with `is_error=True`, and a `RuntimeError("db password is hunter2")` reached it as:

```text
unexpected exception -> 'An internal error occurred' is_error: True
```

Other knobs on the decorator: `name`, `description`, `raw_schema` (a full JSON schema when a signature won't do), and `flags`. `ToolFlag.IGNORE_ON_ENTER` hides a tool during the greeting in `on_enter`; `ToolFlag.CANCELLABLE` lets the LLM cancel it while it runs. `agent.update_tools([...])` swaps the tool list at runtime and replaces *all* tools, including decorated ones. A **`Toolset`** groups tools under one id so you can add or remove them together ([Toolsets](https://docs.livekit.io/agents/logic/tools/toolsets)).

## The tool loop

<figure>
<svg viewBox="0 0 780 300" role="img" aria-labelledby="t-tl d-tl">
  <title id="t-tl">The tool loop inside one agent turn</title>
  <desc id="d-tl">The user's turn goes to the LLM. If the LLM returns tool calls, the framework runs them, appends the calls and their outputs to the chat context, and calls the LLM again. This repeats up to max_tool_steps extra rounds. After that the framework makes one final LLM call with tool_choice none, and the text reply goes to TTS.</desc>
  <defs><marker id="ah-tl" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="16" y="40" width="130" height="50" rx="10"/><text x="81" y="70">User turn</text>
    <rect class="box hot" x="196" y="40" width="130" height="50" rx="10"/><text x="261" y="70">LLM</text>
    <rect class="box" x="400" y="40" width="160" height="50" rx="10"/><text x="480" y="70">Run the tools</text>
    <rect class="box" x="400" y="170" width="160" height="50" rx="10"/><text x="480" y="192">Outputs added</text><text x="480" y="210" font-size="12" class="small">to the chat context</text>
    <rect class="box" x="196" y="230" width="190" height="50" rx="10"/><text x="291" y="252">Final LLM call</text><text x="291" y="270" font-size="12" class="small">tool_choice="none"</text>
    <rect class="box" x="620" y="40" width="140" height="50" rx="10"/><text x="690" y="70">Reply → TTS</text>
  </g>
  <path class="arrow" d="M146 65 H192" marker-end="url(#ah-tl)"/>
  <path class="arrow" d="M326 65 H396" marker-end="url(#ah-tl)"/>
  <path class="arrow" d="M480 90 V166" marker-end="url(#ah-tl)"/>
  <path class="arrow" d="M400 195 C330 195 270 150 262 94" marker-end="url(#ah-tl)"/>
  <path class="arrow" d="M560 195 C600 195 600 250 390 255" marker-end="url(#ah-tl)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M261 40 C261 10 690 10 690 36" marker-end="url(#ah-tl)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="361" y="58">tool calls</text>
    <text x="470" y="24">plain text: speak it</text>
    <text x="300" y="150">next round</text>
    <text x="660" y="230">limit reached</text>
  </g>
</svg>
<figcaption>Each round the model either answers or calls tools. After the step limit, one last call is made with tool use switched off.</figcaption>
</figure>

`max_tool_steps` on `AgentSession` caps the loop. The default is 3 ([Tool loop design](https://docs.livekit.io/agents/logic/tools/design)). To see what the number means, we gave a scratch session a fake LLM that calls a tool every time it is asked, and logged each LLM call:

```text
  llm call: tools=2 tool_choice=NOT_GIVEN
  llm call: tools=2 tool_choice=auto
  llm call: tools=2 tool_choice=auto
  llm call: tools=2 tool_choice=auto
  llm call: tools=2 tool_choice=none
max_tool_steps=3: ['function_call', 'function_call_output', 'function_call', 'function_call_output', 'function_call', 'function_call_output', 'function_call', 'function_call_output'] -> ['hi']
```

So the default allowed four rounds of tool calls (the first plus three more), and then a fifth call with `tool_choice="none"`. The tool list is still sent on that last call. A real provider honors `none`. Our fake ignored it, so it produced no reply at all. The source checks `num_steps >= max_tool_steps + 1` and logs "maximum number of function calls steps reached".

The design guide asks for 5 to 10 tools per agent; past 10, wrong picks get more common. Merge overlapping tools into one with a parameter. Write descriptions that say when *not* to call the tool. Return speech-ready strings ("3 slots at 1 PM, 2:30 PM and 4 PM"), not raw JSON or UUIDs.

## Interruptions, slow tools, MCP

By default a user can interrupt while a tool runs, and the tool keeps running anyway. For a tool that *writes* (an order, a payment, a message), call `ctx.disallow_interruptions()` first so the agent's turn finishes ([Interruptions](https://docs.livekit.io/agents/logic/tools/definition#interruptions)). For a read you'd rather abandon, `await ctx.speech_handle.wait_if_not_interrupted([task])` and cancel the task yourself if `speech_handle.interrupted` is set.

An **async tool** keeps the conversation going while it works. The first `await ctx.update("Searching flights...")` makes it non-blocking. The LLM voices the update, and the final `return` arrives later as a follow-up ([Async tools](https://docs.livekit.io/agents/logic/tools/async)). `async with ctx.with_filler("Still searching.", delay=5):` plays a fixed line through `say()` if the session sits idle for 5 s. `on_duplicate` decides what happens when the LLM calls a tool that's already running: `allow` (default), `reject`, `replace` (needs `CANCELLABLE`) or `confirm`. The installed source also has a `duplicate_scope` argument, `"name"` (default) or `"name_and_args"`. Tools on an `Agent` drop their pending updates at a handoff. Wrap them in an `AsyncToolset` on the `AgentSession` to keep them across handoffs.

**MCP** (Model Context Protocol) lets you mount another server's tools. Wrap the server in an `MCPToolset` and put it in `tools` ([MCP](https://docs.livekit.io/agents/logic/tools/mcp)):

```python
from livekit.agents import mcp      # needs: uv add "livekit-agents[mcp]~=1.8"

tools = [
    mcp.MCPToolset(id="crm", mcp_server=mcp.MCPServerHTTP("http://127.0.0.1:9000/mcp")),
    mcp.MCPToolset(id="files", mcp_server=mcp.MCPServerStdio(command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/srv/docs"])),
]
```

A URL ending in `/mcp` uses streamable HTTP, and one ending in `/sse` uses Server-Sent Events. One MCP server can add 30 or more tools, so filter them. When the data lives in the user's browser (location, a form), **forward the tool to the frontend** with `room.local_participant.perform_rpc(...)` and raise `ToolError` if it fails ([Forwarding](https://docs.livekit.io/agents/logic/tools/forwarding)).

## Handoffs, tasks and task groups

<figure>
<svg viewBox="0 0 780 290" role="img" aria-labelledby="t-hg d-hg">
  <title id="t-hg">Handoff, task and task group compared</title>
  <desc id="d-hg">Handoff: Agent A returns Agent B from a tool and never gets control back. Task: Agent A awaits a task, the task takes control until it calls complete with a typed result, then control returns to Agent A. Task group: Agent A runs task 1, 2 and 3 in order, the user can go back to an earlier task, and a summary returns to Agent A.</desc>
  <defs><marker id="ah-hg" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="13" font-weight="700"><text x="16" y="30">Handoff</text><text x="16" y="120">Task</text><text x="16" y="210">Task group</text></g>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="130" y="40" width="120" height="40" rx="8"/><text x="190" y="65">Agent A</text>
    <rect class="box hot" x="330" y="40" width="430" height="40" rx="8"/><text x="545" y="65">Agent B, for the rest of the session</text>
    <rect class="box" x="130" y="130" width="120" height="40" rx="8"/><text x="190" y="155">Agent A</text>
    <rect class="box hot" x="330" y="130" width="200" height="40" rx="8"/><text x="430" y="155">Task → complete(T)</text>
    <rect class="box" x="610" y="130" width="150" height="40" rx="8"/><text x="685" y="155">Agent A again</text>
    <rect class="box" x="130" y="220" width="120" height="40" rx="8"/><text x="190" y="245">Agent A</text>
    <rect class="box hot" x="300" y="220" width="80" height="40" rx="8"/><text x="340" y="245">Task 1</text>
    <rect class="box hot" x="400" y="220" width="80" height="40" rx="8"/><text x="440" y="245">Task 2</text>
    <rect class="box hot" x="500" y="220" width="80" height="40" rx="8"/><text x="540" y="245">Task 3</text>
    <rect class="box" x="640" y="220" width="120" height="40" rx="8"/><text x="700" y="245">Agent A</text>
  </g>
  <path class="arrow" d="M250 60 H326" marker-end="url(#ah-hg)"/>
  <path class="arrow" d="M250 150 H326" marker-end="url(#ah-hg)"/>
  <path class="arrow" d="M530 150 H606" marker-end="url(#ah-hg)"/>
  <path class="arrow" d="M250 240 H296" marker-end="url(#ah-hg)"/>
  <path class="arrow" d="M380 240 H396" marker-end="url(#ah-hg)"/>
  <path class="arrow" d="M480 240 H496" marker-end="url(#ah-hg)"/>
  <path class="arrow" d="M580 240 H636" marker-end="url(#ah-hg)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M540 260 C540 284 340 284 340 264" marker-end="url(#ah-hg)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="545" y="98">empty context unless you pass chat_ctx</text>
    <text x="430" y="188">awaited in on_enter, on_exit or a tool</text>
    <text x="568" y="196">typed result</text>
    <text x="440" y="284">user goes back to fix an answer</text>
    <text x="608" y="212">summary</text>
  </g>
</svg>
<figcaption>A handoff gives control away for good. A task borrows it and gives back a value. A task group runs tasks in order, allows going back, and hands back a summary.</figcaption>
</figure>

A **handoff** happens when a tool returns another `Agent`, alone or as `(agent, "message for the LLM")`. The new agent starts with an **empty chat context** unless you pass `chat_ctx` ([Agents and handoffs](https://docs.livekit.io/agents/logic/agents-handoffs)). Shared state goes in **`userdata`**, a dataclass you set on `AgentSession[T](userdata=...)` and read as `ctx.userdata` in tools. A **task** is an `AgentTask[T]`. It takes control until it calls `self.complete(value)`, and it can only be awaited from `on_enter`, `on_exit` or a tool body; anywhere else raises `RuntimeError` ([Tasks](https://docs.livekit.io/agents/logic/tasks)). We checked that this imports and constructs with 1.8.11. It was not run through a live session:

```python
class CollectConsent(AgentTask[bool]):
    def __init__(self, chat_ctx=None):
        super().__init__(instructions="Ask for consent to record. Get a clear yes or no.", chat_ctx=chat_ctx)

    @function_tool
    async def consent_given(self) -> None:
        """Call when the user agrees to recording."""
        self.complete(True)
class Support(Agent):
    async def on_enter(self) -> None:
        recorded = await CollectConsent(chat_ctx=self.chat_ctx)       # a task: borrows control
    @function_tool
    async def cancel_order(self, ctx: RunContext[CallState], order_id: str) -> str:
        """Cancel an order. Only call this after the caller confirmed the id out loud."""
        ctx.disallow_interruptions()                                  # a write
        if not order_id.isdigit():
            raise ToolError("Order ids are digits only. Ask the caller to read it again.")
        return f"Order {order_id} is cancelled."
    @function_tool
    async def transfer_to_billing(self, ctx: RunContext[CallState]):
        """Transfer the caller to billing for refund questions."""
        return Billing(chat_ctx=self.chat_ctx.copy(exclude_instructions=True)), "Transferring to billing."
```

A **`TaskGroup`** (from `livekit.agents.beta.workflows`, marked experimental) runs tasks in order with one shared context. It lets the user go back to an earlier step, then summarizes the result into the parent's context (`summarize_chat_ctx=True` by default).

The workflows guide says to **start with one agent and a few tools**, and to split only for a concrete reason: the prompt has grown too long, phases need different tools, a step needs its own multi-turn loop, or users need to go back ([Workflows](https://docs.livekit.io/agents/logic/workflows)). In the **supervisor pattern**, one agent stays in charge and runs specialist tasks ([Supervisor](https://docs.livekit.io/agents/logic/patterns/supervisor)). In **subagent delegation**, a fast model keeps talking while an async tool asks a slower reasoning model, and the answer arrives a turn later ([Subagent delegation](https://docs.livekit.io/agents/logic/patterns/subagent-delegation)).

## Prebuilt tasks and tools

`livekit.agents.beta.workflows` ships `GetNameTask`, `GetEmailTask`, `GetAddressTask`, `GetDOBTask`, `GetPhoneNumberTask`, `GetCreditCardTask` (itself a task group), `GetDtmfTask` (keypad or spoken digits) and `WarmTransferTask` (dials a human over SIP, plays hold music, briefs them, then connects the caller). `livekit.agents.beta.tools` has `EndCallTool` (pass `EndCallTool().tools` to the agent) and `send_dtmf_events` ([Prebuilt tasks](https://docs.livekit.io/agents/prebuilt/tasks), [Prebuilt tools](https://docs.livekit.io/agents/prebuilt/tools)). All of them are beta. Customize them with `extra_instructions`.

:::note Self-hosted vs Cloud
Tools, tasks, handoffs, MCP and the prebuilt tasks all run in your agent process and work self-hosted. `WarmTransferTask` needs SIP, which the self-hosted `livekit/sip` service provides. The same module has a `TwilioConnectorWarmTransferTask`, but connectors are Cloud-only. The docs' examples use `inference.LLM(...)`, which is LiveKit Inference and Cloud-only; pass a plugin LLM with your own key instead. Agent Builder, which generates tasks in the browser, and Agent Simulations are Cloud-only too.
:::

:::tip CLI
The text-mode debugger works against a self-hosted setup and prints each tool call, its arguments and its result ([CLI Agent Debugger](https://docs.livekit.io/testing/debugger)):

- `lk agent debugger start`, then `lk agent debugger say "Book me a table for two tonight"`
- `lk agent debugger chat-history` (tool calls, handoffs, instruction and tool changes)
- `lk agent debugger status` (active agent and its tools) and `lk agent debugger events`
- `lk agent console --text`
:::

:::try
In a copy of `code/livekit/test_agent.py`, make `lookup_order` raise `ToolError("No order 0. Ask the caller to read the number again.")` when `order_id == "0"`. Add a test for "Where is order 0?" that expects `is_function_call_output(is_error=True)`. Run it. `scripted_llm.py` crashes with `AttributeError: 'NoneType' object has no attribute 'group'`, because rule 2 expects a status in every tool output. Guard the regex, run it again, and print the output text the model received.
:::

:::warn Interrupting a tool does not stop it
A user's "wait, no" stops the agent's speech, but the tool runs to the end. For a write, that means the order may be cancelled while the agent never says so. Call `ctx.disallow_interruptions()` in every tool that writes, and gate it on a confirmation the model must report (a `read_back: bool` argument the code checks).
:::

:::note What we did not test
We ran `test_agent.py` (3 passed) and two scratch experiments with fake LLMs: the `ToolError` and internal-error outputs, and the `max_tool_steps` count. We didn't run a real LLM, async tools, MCP (`from livekit.agents import mcp` fails without the `[mcp]` extra in our venv), RPC forwarding, task groups or any prebuilt task. The task and handoff snippet was checked to import and construct, not to run in a session.
:::

:::say
Tools let the model act, the loop repeats until it answers or hits `max_tool_steps`, tasks borrow control and return a typed value, and handoffs give control away with an empty context unless you pass one.
:::

:::check The LLM keeps calling tools. With the default settings, how many tool rounds run, and what happens next?
Four rounds: the first plus `max_tool_steps` (3) more. Then the framework makes one more LLM call with `tool_choice="none"`, so the model has to answer with what it has.
:::

:::check You hand off from a triage agent to a billing agent, and billing asks for the order number again. Why?
A new agent starts with an empty chat context. Pass `chat_ctx=self.chat_ctx.copy(exclude_instructions=True)` to carry the conversation, or put the order number in `userdata`.
:::
