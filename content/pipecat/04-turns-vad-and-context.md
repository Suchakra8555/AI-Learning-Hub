---
title: Turns, voice detection and the chat context
summary: In Pipecat the user aggregator decides when the caller starts and stops a turn, then builds the model's input. You learn the defaults, the strategy objects, and how mute rules work.
time: 25 min
---

Turn-taking is the part of voice AI that feels most like magic and breaks most often. In Pipecat it lives in one object: the **user aggregator**. Not the transport, not the model.

:::warn Version check
Older Pipecat guides put voice activity detection on the transport (`vad_analyzer=` in `TransportParams`) and talk about `allow_interruptions`. In the 1.15 code we read, neither exists. We searched `transports/base_*.py` and `PipelineParams`. If a tutorial tells you otherwise, it is for an older version.
:::

## Two jobs, two pieces

| Job | Question | Where it lives |
|---|---|---|
| **VAD** (voice activity detection) | Is there speech in this 32 ms of audio? | `SileroVADAnalyzer`, inside the user aggregator |
| **Turn strategies** | Did the caller just start a turn? Did they finish? | `turns/user_start/` and `turns/user_stop/` |

VAD defaults, read from [`vad_analyzer.py`](https://github.com/dograh-hq/pipecat/blob/9ac08e90be4bb83e506f3d10deaa8e6d31588547/src/pipecat/audio/vad/vad_analyzer.py) and confirmed by printing `VADParams()` in 1.16.0:

```text
confidence=0.7 start_secs=0.2 stop_secs=0.2 min_volume=0.6
```

So speech must be detected for 0.2 seconds before it counts, and silence must last 0.2 seconds before it counts as a pause. A 0.2 second pause is far too short to mean "I'm done". That is why VAD alone is not a turn decision.

Silero supports only 8,000 and 16,000 Hz audio. It needs windows of 512 samples at 16 kHz and 256 at 8 kHz. Phone audio at 8 kHz works as is.

## Start and stop strategies

Defaults from [`turns/user_turn_strategies.py`, lines 403 to 427](https://github.com/dograh-hq/pipecat/blob/9ac08e90be4bb83e506f3d10deaa8e6d31588547/src/pipecat/turns/user_turn_strategies.py):

- **Start:** a turn starts when VAD hears speech, **or** when a transcript arrives (`VADUserTurnStartStrategy`, `TranscriptionUserTurnStartStrategy`).
- **Stop:** the turn ends when a model says it is finished: `TurnAnalyzerUserTurnStopStrategy` with `LocalSmartTurnAnalyzerV3`. That is a small ONNX model that listens to the audio and judges whether the sentence is complete.

Other pieces you can swap in:

| Strategy | What it does |
|---|---|
| `MinWordsUserTurnStartStrategy(min_words=3)` | Ignore "uh-huh". Only a 3-word utterance starts a turn. |
| `SpeechTimeoutUserTurnStopStrategy(user_speech_timeout=0.6)` | Plain silence timer. Cheap, no model. |
| `ExternalUserTurnStartStrategy` and `ExternalUserTurnStopStrategy` | Trust the STT service's own turn signal, such as Deepgram Flux. |
| `ClassifierUserTurnStopStrategy` | New in 1.15. A classifier decides if the turn is complete. |
| `LLMTurnCompletionUserTurnStopStrategy` | A language model decides. |

The strategies are objects, not flags. That is why Dograh could build its own: `CallbackUserMuteStrategy` is in its fork, and its backend picks start and stop strategies per call.

:::say
Pipecat splits "is someone making sound" (VAD) from "is this person done" (turn strategy), and both live in the user aggregator.
:::

## From a turn to a model call

When the stop strategy fires, the user aggregator:

1. joins the transcripts of the turn into one string,
2. appends `{"role": "user", "content": ...}` to the `LLMContext`,
3. pushes an `LLMContextFrame` downstream.

The `LLMService` gets that frame and starts streaming a reply. `LLMContext` is a plain object holding OpenAI-style message dicts, tools and a tool choice. Each provider has an **adapter** that converts it to that provider's format (there are 16 adapters, including Anthropic, Gemini and several realtime ones).

Pipecat can also start the model **early**. With `EagerUserTurnStopStrategy`, a "speculative" `LLMContextFrame(speculation=True)` goes out before the turn is confirmed. If the caller keeps talking, a `UserTurnResponseCancelFrame` discards it. It trades extra model calls for lower delay.

## Muting the caller

Sometimes the bot must not be interrupted: a legal sentence, a tool running, the first greeting. Pipecat's tool for this is a list of **user mute strategies** passed to the user aggregator:

- `AlwaysUserMuteStrategy`
- `FirstSpeechUserMuteStrategy`
- `MuteUntilFirstBotCompleteUserMuteStrategy`
- `FunctionCallUserMuteStrategy`: mute while a tool runs
- `CallbackUserMuteStrategy` (**Dograh's**): ask your own async function

Dograh's pipeline passes two of these: `FunctionCallUserMuteStrategy()` and `CallbackUserMuteStrategy(engine.should_mute_user)`. The callback mutes the caller when the current workflow node has `allow_interrupt = False` and the bot is speaking. That one checkbox in the builder becomes a mute strategy at run time.

## Idle callers and empty turns

`LLMUserAggregatorParams(user_idle_timeout=...)` (default 0, off) fires an `on_user_turn_idle` event when nobody speaks for too long. The old `UserIdleProcessor` and `STTMuteFilter` classes are gone from this version. Dograh sets the aggregator's idle timeout to 0 and runs its own call monitor instead.

## How LiveKit differs

LiveKit Agents ships a turn-detector model and endpointing delays on the session (from general knowledge, which we did not check against LiveKit's current docs). Pipecat ships the same kind of model, Smart Turn v3, but expresses the policy as strategy objects you assemble. If you tuned `min_endpointing_delay` in LiveKit, the closest Pipecat knobs are `VADParams.stop_secs`, `SpeechTimeoutUserTurnStopStrategy.user_speech_timeout` and the choice of stop strategy.

:::try
In Pipecat's repo, open `examples/turn-management/turn-management-interruption-config.py`. Find where `MinWordsUserTurnStartStrategy` is used. Write one sentence about what a caller sees that is different from the default.
:::

:::check VAD's default stop_secs is 0.2. Why is that not the moment the turn ends?
Because people pause mid-sentence for more than 0.2 seconds. VAD only says "there is silence now". The stop strategy, by default the Smart Turn model, decides whether the sentence is actually finished.
:::

:::check What turns a workflow node's "allow interruption" checkbox into runtime behavior in Dograh?
A `CallbackUserMuteStrategy` whose callback is `engine.should_mute_user`. While the bot speaks on a node with interruptions off, the callback says "mute", so the user aggregator ignores the caller's speech for turn decisions.
:::
