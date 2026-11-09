---
title: Testing and observability
summary: Test an agent without a phone, a room or an API key, then see what it did on real calls. Console mode, the text debugger, the pytest framework with a scripted fake LLM, judges, mock_tools and its argument gotcha, OpenTelemetry, session reports and recordings on a self-hosted stack.
time: 30 min
---

You reword one line of the instructions and ship. Two days later a caller says the agent stopped looking up orders. Nothing crashed and the logs look normal. The agent just stopped calling the tool. Calling the agent after every change by hand doesn't scale. You need checks that run in seconds. When something slips through anyway, you need a record of what the agent did on that call.

## Four layers of checks

LiveKit gives you three tools that run without a room: console mode or Agent Console, the CLI debugger, and unit tests ([Debugging and testing](https://docs.livekit.io/testing/overview)). Add live calls on top and you get a pyramid. Cheap, fast checks at the bottom run on every commit. Slow, real checks at the top run less often.

<figure>
<svg viewBox="0 0 800 300" role="img" aria-labelledby="t-test-pyr d-test-pyr">
  <title id="t-test-pyr">The testing pyramid for a voice agent</title>
  <desc id="d-test-pyr">Four stacked layers. At the bottom and widest, scripted unit tests with pytest and a fake LLM run offline and free on every commit. Above them, tests with a real LLM and judges cost tokens but check wording and intent. Above that, console mode and the text debugger, where you drive the agent by hand. At the top and narrowest, live calls over the real network with real speech recognition. An arrow on the right points up from faster and cheaper to more realistic.</desc>
  <defs><marker id="ah-test" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box hot" x="220" y="20" width="160" height="56" rx="8"/><text x="300" y="44">Live calls</text><text x="300" y="64" font-size="12" class="small">real network, real STT</text>
    <rect class="box" x="160" y="84" width="280" height="56" rx="8"/><text x="300" y="108">Console and text debugger</text><text x="300" y="128" font-size="12" class="small">you drive it, turn by turn</text>
    <rect class="box" x="100" y="148" width="400" height="56" rx="8"/><text x="300" y="172">Real-LLM tests with judges</text><text x="300" y="192" font-size="12" class="small">cost tokens, check wording and intent</text>
    <rect class="box" x="40" y="212" width="520" height="56" rx="8"/><text x="300" y="236">Scripted unit tests (pytest + fake LLM)</text><text x="300" y="256" font-size="12" class="small">offline, free, every commit: this lesson's lab</text>
  </g>
  <path class="arrow" d="M600 262 V30" marker-end="url(#ah-test)"/>
  <g font-size="12" class="small">
    <text x="614" y="40">more realistic,</text><text x="614" y="56">slower, costlier</text>
    <text x="614" y="244">faster, cheaper,</text><text x="614" y="260">run on every change</text>
  </g>
</svg>
<figcaption>Push each check as low as it can go. A tool-call bug belongs in a scripted test. Endpointing and accents only show up near the top.</figcaption>
</figure>

## Console mode and the text debugger

**Console mode** (`lk agent console`) runs one session in your terminal with no LiveKit server. You talk through your microphone, or type with `--text`. `--record` saves the session to disk ([Startup modes](https://docs.livekit.io/agents/server/startup-modes)).

The **CLI agent debugger** is built for scripts and coding agents. `lk agent debugger start` launches your agent in the background. Each `say` sends one turn and prints the tool calls, their results and the reply. `--json` gives one JSON document per turn and a non-zero exit code on errors. Text mode needs no project credentials and joins no room ([CLI Agent Debugger](https://docs.livekit.io/testing/debugger)). The docs list it for `lk` v2.19.0 and later. The lab has v2.19.3.

## The pytest framework

The same `AgentSession` runs in a test with no room. `session.run(user_input=...)` runs one turn in text mode and returns a **RunResult**, the ordered list of events in that turn: messages, function calls, function outputs, handoffs ([Unit tests](https://docs.livekit.io/testing/unit-tests)). `result.expect` lets you walk it:

- `next_event().is_message(role=...)`, `.is_function_call(name=..., arguments=...)`, `.is_function_call_output()`, `.is_agent_handoff(new_agent_type=...)`
- `skip_next(n)`, `skip_next_event_if(type=...)`, `next_event(type="function_call")`
- `expect[0]`, `expect[-1]`, and `contains_message()` / `contains_function_call()` over a slice
- `no_more_events()` to fail on anything unexpected at the end

For behavior you can't match exactly, chain `.judge(llm, intent="...")`. A **judge** is an LLM that reads one message and decides whether it fits the intent. `JudgeGroup` (Python only) runs several judges over the whole `session.history`. There are eight built in, from `accuracy_judge` to `tool_use_judge`. It returns `score`, `all_passed` and per-judge `reasoning`. To run a deterministic check, subclass `Judge`.

## The lab: a scripted LLM

Every docs example passes `inference.LLM(...)`, which is LiveKit Cloud. We wanted tests that run with no key at all, so `code/livekit/scripted_llm.py` is a ~40-line fake written against the plugin interface. `LLM.chat()` returns an `LLMStream` whose `_run()` pushes `ChatChunk`s:

```python
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
```

Look at the regex in rule 2. The tool returns a dict, but `last.output` is text, a Python repr of that dict. That is what a real LLM sees too. `code/livekit/test_agent.py` drives it:

```python
async with AgentSession(llm=ScriptedLLM()) as session:
    await session.start(Support())
    result = await session.run(user_input="Where is order 4417?")
    result.expect.next_event().is_function_call(name="lookup_order", arguments={"order_id": "4417"})
    result.expect.next_event().is_function_call_output()
    result.expect.next_event().is_message(role="assistant")
    result.expect.no_more_events()
    assert "shipped" in session.history.items[-1].text_content
...
with mock_tools(Support, {"lookup_order": lambda ctx, order_id: {"order_id": order_id, "status": "delayed"}}):
    result = await session.run(user_input="Where is order 9?")
result.expect.contains_function_call(name="lookup_order")
assert "delayed" in session.history.items[-1].text_content
```

Real output (`out/test_agent.txt`), offline, with `livekit-agents` 1.8.11:

```text
test_agent.py::test_calls_the_tool_and_reads_the_result PASSED           [ 33%]
test_agent.py::test_with_a_mocked_tool PASSED                            [ 66%]
test_agent.py::test_small_talk_needs_no_tool PASSED                      [100%]
============================== 3 passed in 2.40s ===============================
```

A scripted LLM is useful because it is deterministic and free. The same input gives the same events every run, so a failure means your code changed, not the model's mood. It tests the plumbing: your tool signatures, argument parsing, what the tool returns, how the session strings turns together. It can't tell you whether a real model will call `lookup_order` when a caller says "where's my stuff". It has no language understanding, only two regexes. For behavior, run the same tests against a real model and grade the replies with judges. Self-hosted, pass a plugin LLM (your OpenAI key, or a local model behind an OpenAI-compatible `base_url`) to `judge()` and `JudgeGroup` instead of `inference.LLM`.

:::warn mock_tools passes ctx first
The docs say a mock "receives only the parameters it declares" and that `RunContext` is dropped ([Unit tests](https://docs.livekit.io/testing/unit-tests)). On 1.8.11 we saw something else. With `lambda order_id: ...`, the mock received the RunContext as `order_id`. A keyword-only mock raised an internal error. `lambda ctx, order_id: ...` works, and the test above passes with it. The source shows why: `_run_mock` in `livekit/agents/voice/run_result.py` cuts the real call's positional arguments to the mock's count (`trimmed_args = fnc_args[:max_positional]`), and the RunContext comes first. Name the context as the first parameter of every mock.
:::

## Observability you run yourself

**Agent observability** (the Insights tab, session timelines, PII redaction) only works with LiveKit Cloud media servers ([Observability](https://docs.livekit.io/testing/observability)). Self-hosted, you build it from three parts ([Build your own](https://docs.livekit.io/testing/observability/build)).

**OpenTelemetry traces.** Build a `TracerProvider` with an OTLP exporter and pass it to `livekit.agents.telemetry.set_tracer_provider(provider, metadata=..., allow_pii=...)` before the session starts. Point it with `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS`. Since Agents 1.7.0, content attributes carry an `lk.pii.` prefix (`lk.pii.user_input`, `lk.pii.function_tool.arguments`, and 10 more). 1.8.0 moved spans to the OpenTelemetry GenAI conventions. Old dashboard queries stop matching without any error. `allow_pii=False` strips content before your exporter sees it ([OpenTelemetry traces](https://docs.livekit.io/testing/observability/tracing)).

**Data hooks** ([Data hooks](https://docs.livekit.io/testing/observability/data)):

- `session.history` holds the whole conversation. The `conversation_item_added` event fires per item, which is what a live dashboard needs.
- `ctx.make_session_report()` inside `on_session_end` builds one JSON report: identifiers, history, events, options. The docs say it runs in your process and calls nothing in LiveKit Cloud. It must finish within `session_end_timeout` (300 s by default on `AgentServer`; the docs page still says `WorkerOptions`).
- `ChatMessage.metrics` gives per-turn latency, such as `e2e_latency`, `llm_node_ttft` and `tts_node_ttfb`. `session_usage_updated` and `session.usage` give token and duration totals. The session-level `metrics_collected` event is deprecated. The per-plugin one is not.

**Recordings** come from Egress, for example a room composite recorder started when the agent joins ([Record audio and video](https://docs.livekit.io/testing/observability/recording)).

There is one more knob, from the package source rather than the docs. `AgentServer(prometheus_port=...)` exposes Prometheus metrics on `:<port>/metrics` (`livekit/agents/worker.py`). It is separate from the server's `prometheus: {port: 6789}` in `livekit.yaml`.

:::note Self-hosted vs Cloud
Cloud-only: Agent Console, Agent insights, PII redaction, Agent Simulations, `lk agent debugger --audio` (it speaks through LiveKit Inference TTS), and `inference.LLM` for judges. Self-hosted: console mode, the debugger in text mode, pytest with a plugin LLM or a scripted one, `set_tracer_provider` to your own OTLP backend, `make_session_report()`, and Egress recordings.
:::

:::tip CLI
From the [agent testing reference](https://docs.livekit.io/reference/developer-tools/livekit-cli/agent/testing) and [Startup modes](https://docs.livekit.io/agents/server/startup-modes):

```bash
lk agent console --text
lk agent debugger start
lk agent debugger say "Where is order 4417?"
lk agent debugger chat-history
lk agent debugger say --json "What are your hours?" | jq -r '.reply'
lk agent debugger stop
```
:::

:::try
In `code/livekit`, run `pytest -q test_agent.py` and see 3 passed. Change the mock to `lambda order_id: {"order_id": order_id, "status": "delayed"}`, add `print(type(order_id))` through a small named function, and run it again. What type arrives? Then make `ScriptedLLM` skip the tool for "order 4417" and see which assertion fails first.
:::

:::note What we did not test
We ran only `test_agent.py` with the scripted LLM. We didn't run console mode, `lk agent debugger`, judges or `JudgeGroup` against a real model, OpenTelemetry export, `make_session_report()`, the agent server's Prometheus port, or an Egress recording of an agent session. Those come from the docs and the package source (`livekit-agents` 1.8.11).
:::

:::say
Pin tool calls and plumbing with fast scripted tests, check wording with a real model and judges, and see live calls through your own OpenTelemetry traces and session reports.
:::

:::check Your scripted-LLM tests all pass, but callers say the agent never looks up orders. How can both be true?
The fake LLM always calls the tool when it sees "order 123". A real model decides from the instructions and the user's words. Add a test with a real LLM that sends realistic phrasing and asserts `is_function_call(name="lookup_order")`.
:::

:::check Why does `lambda order_id: ...` break as a mock on 1.8.11?
The mock gets the real tool's positional arguments in order, cut to the number it declares, and the RunContext is first. So `order_id` receives the context. Declare `ctx` first.
:::
