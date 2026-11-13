---
title: Services, tool calls and the 66 providers
summary: STT, LLM and TTS are base classes with one method to fill in. You learn how a tool call becomes frames, how TTS keeps word timing, and what a provider folder looks like.
time: 20 min
---

Pipecat has 66 provider folders under `src/pipecat/services/` in the Dograh fork (we counted with `ls -d services/*/`). Behind them are only a few base classes. Learn those and every provider looks the same.

## The base classes

All services extend `AIService`, which is a `FrameProcessor` that also handles settings and `StartFrame`/`EndFrame`/`CancelFrame` hooks.

| Base | One method you fill in | What it does |
|---|---|---|
| `STTService` | `run_stt(audio: bytes)` yields frames | Turns audio chunks into `TranscriptionFrame` and `InterimTranscriptionFrame`. Handles keepalive and reconnect. |
| `LLMService` | one streaming method per provider | Turns an `LLMContextFrame` into `LLMTextFrame`s between a start and an end frame. Runs tool calls. |
| `TTSService` | `run_tts(text, context_id)` yields frames | Turns text into `TTSAudioRawFrame`s. Tracks word timing. |

Variants exist for the common wire styles: `WebsocketSTTService`, `SegmentedSTTService` (a VAD cuts the audio first), `WebsocketTTSService`, `InterruptibleTTSService`, and `AudioContextTTSService`.

**Settings** go in a nested object in current versions: `OpenAILLMService.Settings(system_instruction=...)`. You can change them mid-call by sending an `LLMUpdateSettingsFrame`. Dograh uses this to swap the system prompt when the call moves to a new node. See [the graph lesson](lesson:pipecat/graph-as-llm-tools).

## A provider is a thin file

Dograh's fork adds `services/huggingface/` and `services/speaches/`. The Speaches TTS is a subclass of an OpenAI-compatible service with one override: it passes the voice string through unchanged, because the upstream OpenAI service rejects voices that are not on its list and raised a `KeyError` for custom voices. That is the whole change. It is what "adding a provider" often looks like.

## TTS and word timing

A TTS service does more than make audio. Providers that return word timestamps call `add_word_timestamps(word_times, context_id=...)`. The words are queued with the audio so that playback and text stay in order. The output transport later releases each word when playback reaches it. That is how the assistant aggregator in [lesson 3](lesson:pipecat/interruptions-and-queues) knows what was spoken.

Each TTS request is an **audio context** with an id. Contexts play in order. An interruption discards the interruptible ones and keeps the rest.

Dograh's fork changed a related rule: text is held back until audio exists for it. If a TTS call returns no audio, its text is dropped with a warning, so the model's history is never polluted by words nobody heard ([`tts_service.py`, `_should_hold_frame`](https://github.com/dograh-hq/pipecat/blob/9ac08e90be4bb83e506f3d10deaa8e6d31588547/src/pipecat/services/tts_service.py)). This is the newest commit in the fork, and it matches an upstream fix (PR #6234) that Dograh took early.

## Tool calls, step by step

In the `getting-started/07-function-calling.py` example a tool is a plain async function with a docstring:

```python
async def get_current_weather(params: FunctionCallParams, location: str, format: str):
    """Get the current weather.
    Args:
        location: The city and state, e.g. "San Francisco, CA".
        format: The temperature unit. Must be "celsius" or "fahrenheit".
    """
    await params.result_callback({"conditions": "nice", "temperature": "75"})

context = LLMContext(tools=[get_current_weather])
```

Pipecat builds the JSON schema from the signature and docstring, and registers the function. The flow when the model calls it:

1. The LLM service broadcasts `FunctionCallsStartedFrame` (a system frame) and `FunctionCallInProgressFrame` (up and down, so the assistant aggregator records it).
2. Your handler runs. It may take a while, so the bot can say "let me check" meanwhile (`on_function_calls_started` event, then `tts.queue_frame(TTSSpeakFrame(...))`).
3. Your handler calls `result_callback(result)`. A `FunctionCallResultFrame` goes out. It is uninterruptible.
4. The assistant aggregator writes the tool call and result into the context. `run_llm` (default true) makes the model speak again. For several parallel calls, the model runs once, using a `group_id`.

You can pass `FunctionCallResultProperties(on_context_updated=...)` to run code after the result has landed in the history. Dograh's end-of-call logic is built on exactly that hook: say the closing line, then hang up.

:::note
`register_function(...)` has a flag `cancel_on_interruption` and a `timeout_secs`. By default a tool is not cancelled when the caller interrupts. Check your tools: a slow tool plus a caller who keeps talking can finish after the conversation moved on.
:::

## Switchers

`LLMSwitcher` and `ServiceSwitcher` put several services in a `ParallelPipeline` behind gates. You switch by frame, or let a failover strategy switch when a service reports an unusable error. Dograh does not use these. It wrote its own `FallbackLLMProcessor` (`api/services/pipecat/fallback_llm.py`), which we saw named but did not read.

## Realtime models

Services such as `OpenAIRealtimeLLMService` and `GeminiLive` take audio in and give audio out, with no separate STT or TTS. In Dograh they get a different pipeline with no STT and no TTS, a separate text model for out-of-band jobs, and per-provider turn settings. They also cannot transfer calls, because transfers need the split pipeline from [lesson 10](lesson:pipecat/a-call-becomes-a-pipeline).

:::try
List the folders in `src/pipecat/services/` of any Pipecat checkout. Pick one TTS provider and one LLM provider. Find the `run_tts` or streaming method in each. How many lines of the file are the actual provider call?
:::

:::check Why does a tool result frame survive an interruption?
It is uninterruptible. If it were dropped, the model would never see that the tool ran, and might call it again on the next turn.
:::

:::check What is an audio context in a TTS service?
One synthesis request with its own id. Contexts play in order. On interruption the interruptible ones are discarded and uninterruptible ones are kept, which lets Pipecat keep a must-say line while clearing the rest.
:::
