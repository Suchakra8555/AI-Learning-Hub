---
title: The live call view: how a node lights up
summary: Follow one event from a Pipecat frame to a highlighted node on the canvas, and then to the stored transcript you can replay. Dograh uses its own rtf- messages, not Pipecat's RTVI.
time: 25 min
---

When you press Test Audio in Dograh, the canvas follows the call. The current node gets a ring and the view pans to it. A transcript scrolls beside it. Tool calls appear as cards. After the call, the same transcript can be replayed. This lesson traces how.

## The path of one event

<figure>
<svg viewBox="0 0 900 330" role="img" aria-labelledby="t13 d13">
  <title id="t13">From node change to highlighted node</title>
  <desc>Seven steps. The engine's set_node sends a node transition callback. The callback builds an rtf-node-transition message and calls the registered WebSocket sender. The browser's signaling WebSocket receives it. The hook calls onNodeTransition. The render component sets the active runtime node id. It injects runtime_active into that node's data and calls fitView. The BaseNode draws a ring. The same event is also saved to the run's log buffer.</desc>
  <defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="12" text-anchor="middle">
    <rect class="box hot" x="10" y="30" width="190" height="64" rx="10"/><text x="105" y="56">PipecatEngine.set_node</text><text x="105" y="74" class="small">pipecat_engine.py:1094</text>
    <rect class="box" x="250" y="30" width="190" height="64" rx="10"/><text x="345" y="56">send_node_transition</text><text x="345" y="74" class="small">run_pipeline.py:862</text>
    <rect class="box" x="490" y="30" width="190" height="64" rx="10"/><text x="585" y="56">ws_sender(message)</text><text x="585" y="74" class="small">signaling WebSocket</text>
    <rect class="box hot" x="710" y="30" width="180" height="64" rx="10"/><text x="800" y="56">useWebSocketRTC</text><text x="800" y="74" class="small">case 'rtf-node-transition'</text>
    <rect class="box" x="710" y="160" width="180" height="64" rx="10"/><text x="800" y="186">RenderWorkflow</text><text x="800" y="204" class="small">handleRuntimeNodeTransition</text>
    <rect class="box" x="490" y="160" width="190" height="64" rx="10"/><text x="585" y="186">displayNodes</text><text x="585" y="204" class="small">data.runtime_active = true</text>
    <rect class="box hot" x="250" y="160" width="190" height="64" rx="10"/><text x="345" y="186">BaseNode</text><text x="345" y="204" class="small">sky-blue ring</text>
    <rect class="box" x="10" y="160" width="190" height="64" rx="10"/><text x="105" y="186">Run logs buffer</text><text x="105" y="204" class="small">stored for replay</text>
    <rect class="box" x="710" y="260" width="180" height="56" rx="10"/><text x="800" y="284">fitView on that node</text><text x="800" y="302" class="small">pan and zoom, 350 ms</text>
  </g>
  <path class="arrow" d="M200 62 H246" marker-end="url(#ah)"/>
  <path class="arrow" d="M440 62 H486" marker-end="url(#ah)"/>
  <path class="arrow" d="M680 62 H706" marker-end="url(#ah)"/>
  <path class="arrow" d="M800 94 V156" marker-end="url(#ah)"/>
  <path class="arrow" d="M710 192 H684" marker-end="url(#ah)"/>
  <path class="arrow" d="M490 192 H444" marker-end="url(#ah)"/>
  <path class="arrow" stroke-dasharray="4 4" d="M105 94 V156" marker-end="url(#ah)"/>
  <path class="arrow" d="M800 224 V256" marker-end="url(#ah)"/>
</svg>
<figcaption>The trip from the engine to the pixels. Files and lines are from Dograh commit <code>5dfa84c</code>.</figcaption>
</figure>

In the browser, `RenderWorkflow.tsx` does two things:

```tsx
const displayNodes = useMemo(() =>
    nodes.map((node) => node.id === activeRuntimeNodeId
        ? { ...node, data: { ...node.data, runtime_active: true } }
        : node),
    [activeRuntimeNodeId, nodes]);
```

and, on a transition, `setActiveRuntimeNodeId(nodeId)` followed by `instance.fitView({nodes:[{id:nodeId}], duration:350, padding:0.45, maxZoom:0.9})`. The highlight is a *derived* property: the stored node never changes, only the copy handed to the renderer. That also keeps `runtime_active` from being saved, and the server strips it anyway.

## The message shape

```json
{"type": "rtf-node-transition",
 "payload": {"node_id": "b", "node_name": "Book",
             "previous_node_id": "s", "previous_node_name": "Greeting",
             "allow_interrupt": true}}
```

The other event types (from the fork's `RealtimeFeedbackType` enum) are `rtf-user-transcription`, `rtf-bot-text`, `rtf-function-call-start`, `rtf-function-call-end`, `rtf-ttfb-metric`, `rtf-latency-measured`, `rtf-pipeline-error`, `rtf-bot-started-speaking`, `rtf-bot-stopped-speaking`, `rtf-user-mute-started` and `rtf-user-mute-stopped`. The UI also handles an `rtf-interrupt-warning`.

## Two producers

**The observer** (`RealtimeFeedbackObserver`, 451 lines, a Pipecat `BaseObserver`) maps frames to events:

| Frame | Event |
|---|---|
| `Interim/TranscriptionFrame` | `rtf-user-transcription` |
| `TTSTextFrame`, `TTSSpeakFrame` | `rtf-bot-text` |
| `FunctionCallInProgressFrame`, `FunctionCallResultFrame` (downstream only) | `rtf-function-call-start`, `-end` |
| `MetricsFrame` (TTFB only) | `rtf-ttfb-metric` |
| `BotStarted/StoppedSpeakingFrame` | `rtf-bot-started-speaking`, `rtf-bot-stopped-speaking` |
| `UserMuteStarted/StoppedFrame` | `rtf-user-mute-*` |
| `ErrorFrame` | `rtf-pipeline-error` |

One observer instance is shared with every agent worker, with frame-id de-duplication. That is the pattern from [lesson 7](lesson:pipecat/observers-metrics-and-tracing).

**The engine** sends node transitions. They are not frames. The observer's own docstring says so. The engine knows when the node changes, so it calls a callback directly. A frame-based approach would have to guess.

## The transport is the signaling WebSocket

There is no WebRTC data channel. Events ride the same WebSocket used to set up the call. The registry `ws_sender_registry.py` is a module-level dict from run id to a sending coroutine. It works because the signaling handler and the pipeline run in the **same process**. Phone calls register no sender, so a phone call shows no live view. It still records events (next section). That in-process dict is a scaling limit we list in [lesson 17](lesson:pipecat/what-to-steal).

## What the browser does with each event

`fromRealtimeFeedback.ts` (336 lines) turns the event list into timeline items. Some choices show care:

- Only the **LLM's** TTFB is shown, as a "reasoning delay". The comment says STT and TTS TTFB can arrive in the middle of a reply, and any message between two bot-text chunks would split the bot's speech bubble.
- If the caller speaks while muted on a no-interrupt node, a one-time notice says: "Interruption is disabled for this step. The bot will finish speaking before processing your input."
- A node transition becomes a small pill with a branch icon and the node name between two lines.

## Replay after the call

Events are also appended to an in-memory log buffer (`in_memory_buffers.py`) and persisted into the run's `logs.realtime_feedback_events`. The run detail page (`run/[runId]/page.tsx`, 1,046 lines) loads them and renders the same component in `historical` mode in a right-hand rail, next to:

- the recording, with split user and bot tracks and a shared timeline,
- "Run Metrics": duration, user turns, bot turns, tool calls, nodes visited,
- "Initial Context" and "Gathered Context" (the variables the call extracted),
- QA results, and a "View Trace" link to the Langfuse trace.

We looked for a graph overlay of the call path on the run page and did not find one. The path is the list of transition markers and the `nodes_visited` list. That is a visible gap, and a possible contribution.

:::note We found no audio visualizer
You might expect a waveform. We searched the UI for waveform, analyser and canvas components and found none. The tester shows connection status, a device picker and an `<audio>` element. The "visualization" people notice is the graph following the call.
:::

:::try
In `useWebSocketRTC.tsx`, find the `switch` that handles `rtf-` messages. List which cases change the transcript and which change only refs. Why would a mute event not add a message?
:::

:::check Why does Dograh send node transitions from the engine and not derive them from a frame in an observer?
The engine is the only code that knows when `set_node` runs. Guessing it from frames would be indirect and could drift when the engine changes.
:::

:::check Why does a phone call have no live node highlight but still have a replayable transcript?
The live view needs a registered WebSocket sender, which only the browser test call registers. The log buffer is written for every call, so the stored events exist for replay.
:::
