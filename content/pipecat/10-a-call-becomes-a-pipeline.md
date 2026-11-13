---
title: How a call becomes a pipeline
summary: Trace a browser test call and a phone call to the one function that builds the Pipecat pipeline. See the real processor order, why the LLM and TTS live in a child worker, and the turn defaults.
time: 30 min
---

Every Dograh call, whatever the door, ends up in one function. This lesson walks both doors, then the pipeline.

## Door 1: the browser test call

1. The UI opens a WebSocket to `/api/v1/ws/signaling/{workflow_id}/{workflow_run_id}` (`api/routes/webrtc_signaling.py:836`).
2. The browser sends an `offer` with its session description. There is no data channel and no HTTP signalling. ICE candidates **trickle over the same WebSocket**. The module docstring says why: it must work across several uvicorn processes.
3. The server checks the run, takes a concurrency slot, builds `SmallWebRTCConnection(ice_servers=..., connection_timeout_secs=60)` and answers.
4. It registers a function that sends JSON to this WebSocket, then starts the pipeline as a background task.

```python
async def ws_sender(message: dict):
    if ws.application_state == WebSocketState.CONNECTED:
        await ws.send_json(message)
register_ws_sender(workflow_run_id, ws_sender)
...
pipeline_task = asyncio.create_task(run_pipeline_smallwebrtc(pc, workflow_id, workflow_run_id, ...))
```

That `ws_sender` is how live events reach the screen. Remember it for [lesson 13](lesson:pipecat/live-events-and-replay).

## Door 2: a phone call

For an outbound call, `routes/telephony.py:92 initiate_call` creates a `WorkflowRun` named like `WR-TEL-OUT-xxxxxxxx`, checks quota, and asks the carrier to dial. The carrier calls back a webhook and Dograh answers with markup that tells it to open a media stream. For Twilio that is:

```xml
<Response><Connect><Stream url="{ws_url}"></Stream></Connect><Pause length="40"/></Response>
```

The carrier opens a WebSocket to `/ws/{workflow_id}/{organization_id}/{workflow_run_id}`. The handler checks an optional signed token, finds the run, requires it to be in state `INITIALIZED`, and hands the socket to the provider class. It marks the run `running` only after the carrier's `start` message arrives, because some carriers open the socket while the phone is still ringing.

For **inbound** calls one route, `/inbound/run`, serves every carrier. It asks each registered provider "can you handle this webhook?", normalizes the data, and one SQL query joins the telephony config and phone number tables to find the workflow. The number row's `inbound_workflow_id` decides which agent answers.

Both doors reach `_run_pipeline_impl` (`run_pipeline.py:639`). In order, it:

1. loads the run and workflow, scoped by organization,
2. uses the **pinned definition** from when the run started (lines 707 to 710), so editing the agent mid-call changes nothing,
3. validates it into a `WorkflowGraph`,
4. starts the **pre-call fetch** (an HTTP call for caller data) in the background while services are built,
5. builds STT, or a realtime model,
6. builds the `PipecatEngine` (the call logic, [next lesson](lesson:pipecat/graph-as-llm-tools)),
7. builds the pipeline and a worker, attaches observers, and runs.

## The processor order

From `pipeline_builder.py`:

```python
processors = [transport.input(), termination_funnel, stt]
if answer_supervisor is not None: processors.append(answer_supervisor)
if opening_input is not None:     processors.append(opening_input)
processors.append(user_context_aggregator)
if answer_supervisor is not None: processors.append(answer_supervisor.llm_gate())
processors.extend([call_monitor_processor, *generation_stage,
    transport.output(), audio_buffer, assistant_context_aggregator,
    pipeline_metrics_aggregator])
return Pipeline([p for p in processors if p is not None])
```

Compare it with the textbook chain in [lesson 1](lesson:pipecat/what-pipecat-is). The same skeleton, with Dograh's pieces:

- `termination_funnel` is second, so every shutdown request, even an upstream cancel, is redirected to the engine's single `end_call` path.
- `answer_supervisor` and its LLM gate handle voicemail detection before the agent speaks.
- `call_monitor_processor` owns idle timeout, maximum call length and a response watchdog.
- `generation_stage` is **one processor** that stands in for the LLM and TTS. See below.
- `audio_buffer` records the call. It sits after the output transport and uses the unmixed bot track so recordings have no ambient noise.
- `pipeline_metrics_aggregator` is last.

<figure>
<svg viewBox="0 0 900 330" role="img" aria-labelledby="t10 d10">
  <title id="t10">Dograh's split pipeline</title>
  <desc>The call worker holds transport input, termination funnel, STT, user aggregator, call monitor, an agent bridge, transport output, audio buffer and assistant aggregator. A child agent worker holds the LLM and TTS. The agent bridge connects the two over Pipecat's worker bus. Each time the call moves to a new agent, a new child worker replaces the old.</desc>
  <defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect x="10" y="20" width="880" height="110" rx="14" class="frame"/>
  <text x="24" y="42" font-size="14" font-weight="700">Call worker (lives for the whole call)</text>
  <g font-size="12" text-anchor="middle">
    <rect class="box" x="24" y="60" width="86" height="50" rx="8"/><text x="67" y="82">transport</text><text x="67" y="98">input</text>
    <rect class="box" x="122" y="60" width="86" height="50" rx="8"/><text x="165" y="82">termination</text><text x="165" y="98">funnel</text>
    <rect class="box" x="220" y="60" width="70" height="50" rx="8"/><text x="255" y="90">STT</text>
    <rect class="box" x="302" y="60" width="86" height="50" rx="8"/><text x="345" y="82">user</text><text x="345" y="98">aggregator</text>
    <rect class="box" x="400" y="60" width="86" height="50" rx="8"/><text x="443" y="82">call</text><text x="443" y="98">monitor</text>
    <rect class="box hot" x="498" y="60" width="96" height="50" rx="8"/><text x="546" y="82">agent</text><text x="546" y="98">bridge</text>
    <rect class="box" x="606" y="60" width="86" height="50" rx="8"/><text x="649" y="82">transport</text><text x="649" y="98">output</text>
    <rect class="box" x="704" y="60" width="70" height="50" rx="8"/><text x="739" y="82">audio</text><text x="739" y="98">buffer</text>
    <rect class="box" x="786" y="60" width="92" height="50" rx="8"/><text x="832" y="82">assistant</text><text x="832" y="98">aggregator</text>
  </g>
  <path class="arrow" stroke-dasharray="5 5" d="M546 112 V196" marker-end="url(#ah)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M590 196 V112" marker-end="url(#ah)"/>
  <text x="640" y="160" font-size="12" class="small">worker bus</text>
  <rect x="330" y="200" width="340" height="100" rx="14" class="frame hot"/>
  <text x="344" y="222" font-size="14" font-weight="700">Agent worker (one per node visit)</text>
  <g font-size="13" text-anchor="middle">
    <rect class="box hot" x="350" y="236" width="80" height="48" rx="8"/><text x="390" y="266">LLM</text>
    <rect class="box" x="440" y="236" width="100" height="48" rx="8"/><text x="490" y="258">spoken-text</text><text x="490" y="273">filter</text>
    <rect class="box hot" x="550" y="236" width="100" height="48" rx="8"/><text x="600" y="266">TTS</text>
  </g>
  <text x="720" y="262" font-size="13" class="small">Transfer to a new agent</text>
  <text x="720" y="280" font-size="13" class="small">swaps this box only.</text>
</svg>
<figcaption>From <code>pipeline_builder.py</code> lines 36 to 203. The child worker is created with <code>active=False</code>, no heartbeats, no idle timeout, and no RTVI of its own.</figcaption>
</figure>

**Why split?** A call has things that must survive an agent change: the audio connection, the recording, the transcript, the chat history. It also has things that change per agent: the model, the voice, the prompt. Putting the LLM and TTS in a child worker, joined over Pipecat's worker bus, means "transfer to another agent" replaces one worker and never touches the transport. This uses the Pipecat 1.x multi-worker features from the note in [lesson 8](lesson:pipecat/from-livekit-to-pipecat). It also explains why realtime-model calls cannot transfer: they have no split.

## The worker and its parameters

```python
PipelineParams(enable_metrics=True, enable_usage_metrics=True,
    send_initial_empty_metrics=False, enable_heartbeats=True,
    start_metadata={"workflow_run_id": workflow_run_id})
DograhPipelineWorker(pipeline, ..., processor_unusable_policy=ProcessorUnusablePolicy.CANCEL,
    enable_tracing=True, enable_rtvi=False, conversation_id=f"{workflow_run_id}")
```

`ProcessorUnusablePolicy.CANCEL` keeps the old behavior of ending the call when a service reports a permanent failure. The subclass `DograhPipelineWorker` overrides **private** methods of Pipecat's worker to make setup cancellable. Its docstring says to keep the lifecycle tests when upgrading. That is a debt marker, and [lesson 16](lesson:pipecat/living-with-a-fork) comes back to it.

## Turn settings, with the numbers

From `api/schemas/workflow_configurations.py` and `run_pipeline.py`:

| Setting | Default |
|---|---|
| Maximum call duration | 300 s |
| Maximum user idle | 10 s |
| Smart turn stop | 2.0 s |
| Start strategy | `min_words`, 2 words |
| Stop strategy | `transcription` |
| VAD | `SileroVADAnalyzer(VADParams(stop_secs=0.2))` always |
| User turn stop timeout | 5.0 s (30 s when the STT owns turns) |

Start strategies by setting: `min_words` gives `MinWordsUserTurnStartStrategy(min_words=2)`. External-turn STT such as Deepgram Flux gives `ExternalUserTurnStartStrategy`. Stop strategies: Flux gives `ExternalUserTurnStopStrategy`, a turn analyzer gives `LocalSmartTurnAnalyzerV3`, and anything else gives `SpeechTimeoutUserTurnStopStrategy`. For realtime models there is a table of per-provider rules in `run_pipeline.py` lines 265 to 329.

These are exactly the knobs from [lesson 4](lesson:pipecat/turns-vad-and-context), set from a form in the UI.

## Choosing services

`service_factory.py` (2,029 lines) reads the effective model configuration for the run (organization settings plus per-workflow overrides) and returns the right service by a long `if`/`elif` on a provider id. About 37 provider ids exist. Two details are worth stealing:

- Every STT service is created with `should_interrupt=False`, with the comment "Let UserAggregator take care of sending InterruptionFrame". One place decides interruptions.
- Every OpenAI-compatible LLM is subclassed with a **spoken tool call mixin**. Some models write a tool call as text ("`<function=...>`") instead of a real call. The mixin recovers it, and the fork's `SpokenTextProcessor` keeps such text out of the speech.

:::check Why does Dograh pin the workflow definition a run started with?
A call can last many minutes, and people edit agents in the builder at any time. Using the definition that was current when the run was created means an edit cannot change a call that is already in progress.
:::

:::check What does the agent bridge let Dograh do that one flat pipeline would not?
Replace the LLM and TTS (a new agent, voice or model) in the middle of a call without touching the audio connection, recording or transcript.
:::
