---
title: Observers, metrics and tracing
summary: Observers watch every frame without changing it. This lesson shows how to turn frames into UI events (we ran it), what Pipecat measures by itself, and how traces reach Langfuse.
time: 20 min
---

If processors are the workers, **observers** are the cameras. They see every frame pushed anywhere in the pipeline, they cannot change anything, and they run in their own queue so a slow one cannot delay audio.

## The interface

```python
class BaseObserver(BaseObject):
    async def on_process_frame(self, data: FrameProcessed)
    async def on_push_frame(self, data: FramePushed)   # source, destination, frame, direction, timestamp
    async def on_processor_setup(self, data: ProcessorSetUp)
    async def on_pipeline_started(self)
```

You pass them to the worker: `PipelineWorker(pipeline, observers=[MyObserver()])`. Every processor boundary reports the same frame again, so a useful observer remembers frame ids it has already handled. (A frame that crosses six processors is "pushed" six times.)

## Frames to browser events: a real run

`code/pipecat/frames_to_events.py` is a small sketch of what Dograh's `RealtimeFeedbackObserver` does. It watches for four kinds of frame and appends a JSON event for each. We ran it with a scripted conversation:

```json
{"type": "rtf-user-transcription", "payload": {"text": "I want to book a table"}}
{"type": "rtf-bot-started-speaking", "payload": {}}
{"type": "rtf-bot-text", "payload": {"text": "Sure."}}
{"type": "rtf-bot-text", "payload": {"text": "For how many people?"}}
{"type": "rtf-bot-stopped-speaking", "payload": {}}
```

The `rtf-` prefix and the event names are Dograh's. In production the events go over a WebSocket to the browser and into a log buffer for replay. [Lesson 13](lesson:pipecat/live-events-and-replay) follows them to the screen.

:::warn
Our demo feeds frames in by hand. A real `TTSTextFrame` comes from a TTS service with timing, and `TranscriptionFrame` from STT. The demo proves the observer pattern, not Dograh's mapping rules.
:::

## What Pipecat measures for you

Turn on `PipelineParams(enable_metrics=True, enable_usage_metrics=True)`. Services then push `MetricsFrame`s containing:

- **TTFB** (time to first byte) for the STT, LLM and TTS stages,
- **processing time**,
- **LLM token usage**, including cache reads and audio tokens,
- **STT audio seconds** and **TTS character counts**,
- **turn metrics** such as the Smart Turn probability.

Observers that build on them:

| Observer | Gives you |
|---|---|
| `TurnTrackingObserver` | `on_turn_started`, `on_turn_ended(was_interrupted)`: a numbered list of turns |
| `UserBotLatencyObserver` | A `LatencyBreakdown`: from the end of user speech to the first bot audio, split by stage |
| `MetricsLogObserver`, `LLMLogObserver`, `DebugLogObserver` | Log lines |
| `FunctionCallObserver`, `ErrorObserver` | Tool and error hooks |

`PipelineWorker` adds the turn tracker automatically. With tracing on, it adds the latency and trace observers too.

:::note
The latency number a caller feels is **user stops talking** to **bot audio starts**. It includes the end-of-turn wait, which no single service reports. That is why `UserBotLatencyObserver` exists. See [where the milliseconds go](lesson:voice/where-the-milliseconds-go).
:::

## Tracing

`setup_tracing(service_name=..., exporter=...)` plus `PipelineWorker(enable_tracing=True, conversation_id=...)` makes OpenTelemetry spans: one per conversation, one per turn, and one per STT, LLM and TTS call, with token counts. You supply the exporter. Dograh's exporter sends to **Langfuse**, and routes each organization's traces to that organization's own credentials (`api/services/pipecat/tracing_config.py`).

The fork changed this layer more than most: ChatML conversion so Langfuse shows Gemini and OpenAI messages the same way, span names like `llm-<node name>`, a trace URL helper so the run page can link to the trace, and traces that are **private** unless `LANGFUSE_TRACES_PUBLIC` is set. The old behavior published every trace publicly by default.

## RTVI

RTVI is Pipecat's own client protocol: `bot-ready`, `user-transcription`, `bot-tts-text`, `llm-function-call-*`, `error`. `PipelineWorker` adds an `RTVIProcessor` and an `RTVIObserver` unless you say otherwise. If you use Pipecat's JavaScript client, you get a live transcript for free. Dograh turns RTVI off (`enable_rtvi=False`) and sends its own events, because it needs node transitions and tool cards that RTVI does not carry.

:::try
Add a `BotStartedSpeakingFrame` handler to `frames_to_events.py` that also records a timestamp. Subtract the time of the transcript event from the time of the bot event and print "latency". What does that number miss compared with a real call?
:::

:::check Why does an observer need to remember frame ids?
A frame is reported at every hop between processors. Without a seen-set, one transcript crossing six processors produces six identical events.
:::

:::check What does UserBotLatencyObserver measure that a TTS service's TTFB does not?
The whole gap the caller feels: end of speech, the turn decision wait, the model, the TTS and the audio start. A single service only knows its own slice.
:::
