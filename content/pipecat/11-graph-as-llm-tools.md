---
title: The call flow is a graph, and every edge is a tool
summary: Dograh turns the graph you draw into model tool calls. Each edge becomes a function, the node prompt becomes the system prompt, and a transition swaps both. You run a 120-line version.
time: 30 min
---

This is the core idea of Dograh. Understand it and the builder, the engine and the live highlight all make sense.

## The idea

You draw nodes: Start, Agent, End. You draw edges between them. Each edge has a **label** and a **condition** written in plain language, such as "Caller gave a day and a time".

At run time, only one node is active. The model sees:

- that node's prompt, as the system prompt,
- one **tool** for each edge leaving the node, named from the edge label, described by the edge condition.

When the model decides the condition is true, it calls the tool. The engine moves to the next node, swaps the prompt and the tools, and the model carries on. The graph is not a rules engine. The language model is the judge of every condition. The graph only decides what the model is allowed to see and do at each step.

<figure>
<svg viewBox="0 0 900 300" role="img" aria-labelledby="t11 d11">
  <title id="t11">A graph becomes tools</title>
  <desc>On the left, a Greeting node with two outgoing edges labeled Wants to book and Wants a person. On the right, the model's view while on the Greeting node: the Greeting prompt as system prompt and two tools, wants_to_book and wants_a_person, with the edge conditions as descriptions.</desc>
  <defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box hot" x="20" y="110" width="130" height="60" rx="10"/><text x="85" y="146">Greeting</text>
    <rect class="box" x="250" y="40" width="130" height="56" rx="10"/><text x="315" y="73">Book</text>
    <rect class="box" x="250" y="184" width="130" height="56" rx="10"/><text x="315" y="217">Human</text>
  </g>
  <path class="arrow" d="M150 128 L246 76" marker-end="url(#ah)"/>
  <path class="arrow" d="M150 152 L246 210" marker-end="url(#ah)"/>
  <text x="170" y="94" font-size="12" class="small">"Wants to book"</text>
  <text x="165" y="206" font-size="12" class="small">"Wants a person"</text>
  <path class="arrow" stroke-dasharray="5 5" d="M400 140 H470" marker-end="url(#ah)"/>
  <text x="435" y="130" font-size="12" class="small" text-anchor="middle">becomes</text>
  <rect class="box" x="480" y="30" width="400" height="230" rx="12"/>
  <text x="496" y="56" font-size="14" font-weight="700">What the model sees on Greeting</text>
  <text x="496" y="84" font-size="13">system prompt: "Greet the caller. Ask what they need."</text>
  <text x="496" y="120" font-size="13" font-weight="700">tool wants_to_book</text>
  <text x="512" y="140" font-size="12" class="small">"Caller wants an appointment"</text>
  <text x="496" y="176" font-size="13" font-weight="700">tool wants_a_person</text>
  <text x="512" y="196" font-size="12" class="small">"Caller asks for a human"</text>
  <text x="496" y="240" font-size="12" class="small">Name = edge label, lower-cased, non-letters become "_".</text>
</svg>
<figcaption>The conversion in <code>workflow_graph.py</code> (the name) and <code>pipecat_engine_context_composer.py</code> (the description).</figcaption>
</figure>

## The data

The saved graph is plain JSON. A real test fixture from `api/tests/dto_fixtures/clean.json`:

```json
{"nodes":[
 {"id":"s","type":"startCall","position":{"x":0,"y":0},"data":{"name":"Start","prompt":"Greet the caller."}},
 {"id":"a","type":"agentNode","position":{"x":200,"y":0},"data":{"name":"Agent","prompt":"Continue the conversation."}},
 {"id":"e","type":"endCall","position":{"x":400,"y":0},"data":{"name":"End","prompt":"Say goodbye."}}],
 "edges":[
 {"id":"s-a","source":"s","target":"a","data":{"label":"start to agent","condition":"always"}},
 {"id":"a-e","source":"a","target":"e","data":{"label":"agent to end","condition":"always"}}]}
```

There are seven node types (`api/services/workflow/dto.py:34`): `startCall`, `agentNode`, `endCall`, `globalNode`, `trigger`, `webhook` and `qa`. The first four shape the conversation. A **global node** holds a prompt prepended to every node that opts in, which is where you put the persona. A **trigger** is an API entry point. A **webhook** and **QA** run after the call.

The edge data holds the label, the condition, and optional **transition speech**: text or a recording played right before moving on, to cover the model's thinking time. The builder's hint says it is "not attached in Conversation Context".

Validation (`WorkflowGraph._validate_graph`) checks node counts and connection counts from each node type's spec, requires a prompt on the four conversational types, and rejects two edges leaving one node whose labels sanitize to the same tool name. **Cycles are allowed.** The acyclic check is commented out with a TODO (`workflow_graph.py:334` to `342`).

## The prompt and the tools

`compose_system_prompt_for_node` joins the global prompt and the node prompt with a blank line, then renders `{{variables}}` from the call context. `compose_functions_for_node` adds, in order, the knowledge-base tool if documents are attached, then custom and MCP tools, then one function per outgoing edge:

```python
get_function_schema(edge.get_function_name(), edge.condition)
```

The edge **condition text is the tool description**. That is the only place the condition is "evaluated". Write conditions the way you would write a tool description.

## The transition

The heart of `pipecat_engine.py` (`_create_transition_func`, lines 457 to 544), trimmed:

```python
async def transition_func(function_call_params):
    await self._perform_variable_extraction_if_needed(self.active_agent.current_node, ...)
    # queue transition speech (recording or text), muting the user
    await self.set_node(transition_to_node, origin_visit_id=agent.visit_id)
    is_end_node = agent.workflow.nodes[transition_to_node].is_end
    if is_end_node:
        closing_speech = self.speech_playback.expect_response(source=agent.llm)
        self._mute_pipeline = True
    async def on_context_updated():
        if is_end_node:
            await closing_speech.wait()
            if self.agent_can_act(agent):
                await self.end_call_with_reason(EndTaskReason.END_CALL.value)
    await function_call_params.result_callback({"status": "done"},
        properties=FunctionCallResultProperties(on_context_updated=on_context_updated))
```

Read the order:

1. **Extract variables** from the conversation so far, with a separate model, in the background by default. This is how "budget" or "appointment time" get saved.
2. **`set_node`** swaps the prompt and tools **before** the tool result goes back. The follow-up model call already runs on the new node. It also fires the node-transition event the UI listens for.
3. For an **end node**, wait until the closing line has been spoken, then hang up. That uses the `on_context_updated` hook from [lesson 5](lesson:pipecat/services-and-tool-calls).

`set_node` first refuses requests from a retired agent visit (`origin_visit_id`), so a late tool call from an old node cannot move the call.

The system prompt is swapped through `llm._update_settings(LLMSettings(system_instruction=...))`, **not** by appending a message. That keeps the history clean, and it is one of the places Dograh reaches into a private method of Pipecat.

## Two timing fixes in the fork

A transition tool can fire in the middle of the model's sentence. Dograh's fork added `is_node_transition` to `register_function`. When a response has exactly one transition tool and some speakable text, Pipecat **defers the tool until the bot finishes speaking** (`BotStoppedSpeakingFrame`). An interruption or shutdown drops the deferred call. A generation counter blocks stale responses. Also `NodeTransitionStartedFrame` is uninterruptible, and makes the user aggregator commit pending text before the handoff.

## Run a small version

`code/pipecat/mini_workflow.py` rebuilds this in standard-library Python: same JSON shape, same tool-name rule, same duplicate check, prompt and tool swap, and the transition event. The "model" is a keyword matcher so the run repeats. We ran it:

```text
validate(good graph): []
validate(duplicate edge label): [{'kind': 'edge', 'id': 's', 'message': "duplicate tool name 'wants_to_book'"}]

caller: 'hi, I want an appointment'
  node=Greeting  tools=['wants_to_book', 'wants_a_person']
  model calls: wants_to_book

caller: 'tuesday works, ten in the morning, one day and one time is fine'
  node=Book  tools=['slot_chosen']
  model calls: slot_chosen

caller: 'thanks'
  node=Goodbye  tools=[]
  model calls: None

events a UI would receive:
  {"type": "rtf-node-transition", "payload": {"node_id": "s", "node_name": "Greeting", ...}}
  {"type": "rtf-node-transition", "payload": {"node_id": "b", "node_name": "Book", ...}}
  {"type": "rtf-node-transition", "payload": {"node_id": "e", "node_name": "Goodbye", ...}}
```

(We shortened the event lines to fit.) Notice that on the second turn the model's tool list is only `slot_chosen`. The model cannot jump to "Human" from here. That narrowing is the safety feature of the whole design.

## Strengths and costs

**Strengths.** Non-programmers can edit conversation flow. Every step has a small prompt and a small tool list, which tends to make models more reliable than one giant prompt (our reading, not a measurement). Node names make logs and traces readable: Dograh's spans are named `llm-<node>`.

**Costs.** The model must correctly judge conditions, so wrong or fuzzy edge text means wrong transitions. Cycles are allowed with no guard. Debugging a bad transition means reading the model's tool choice in a trace.

:::try
Edit `GRAPH` in `mini_workflow.py`. Add a node "Reschedule" reachable from Book, with the condition "Caller wants a different day". Add a caller line that triggers it. Then add a second edge from Book with the same label and run `validate`.
:::

:::check Why does set_node swap the prompt and tools before the tool result is returned?
So the next model call, triggered by the result, already runs with the new node's prompt and tools. Swapping after would let the model answer once with the old node's rules.
:::

:::check Where is an edge condition actually evaluated?
By the language model, as the description of the transition tool. Dograh has no rules engine for it.
:::
