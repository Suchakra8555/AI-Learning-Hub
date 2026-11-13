---
title: What Dograh changed in Pipecat
summary: Against upstream Pipecat 1.15.0, Dograh's fork differs in 167 files, +14,441 and -595 lines, and almost half of it is tests. This lesson groups the changes and says which are general and which are Dograh-only.
time: 30 min
---

You asked what Dograh changed in Pipecat. This is the answer, from `git diff` against the real upstream tag.

:::warn What we measured
We cloned `dograh-hq/pipecat` at the commit Dograh pins (`9ac08e90b`) and added `pipecat-ai/pipecat` as `upstream`. We read the diffs and commit messages. "Why" statements are marked as our inference. We did not run the fork's tests. Numbers are exact for that commit and will move.
:::

## The right base to compare with

The obvious `git merge-base` gives upstream v1.12.0, and a diff from there is 1,299 files and +118,076 lines. Almost all of that is **upstream's own work** between 1.12 and 1.15, because the fork has already absorbed v1.15.0. Commit `334261dc1` is titled "Merge upstream Pipecat v1.15.0 and preserve Dograh integrations (#82)". That sync was a squash-style pull request with one parent, so Git still reports the old merge base.

Against the v1.15.0 tag the delta is the real one:

| | Files | Added | Removed |
|---|---|---|---|
| All changes | 167 | 14,441 | 595 |
| `src/` | | 7,854 | 504 |
| `tests/` | | 6,553 | 88 |

64 files are new (33 source, 24 test, 7 changelog notes), 103 are modified, none deleted. The fork is also **behind**: upstream tagged v1.16.0 on 11 November 2026 and the fork does not have it.

## Who and how

- 135 commits since the old merge base: 124 normal, 11 merges. Three people wrote 116 of the 124 (two of the names look like one person with two Git identities).
- A few outside contributors landed fixes (Speaches voices, Sarvam language codes, Whisper null text, Langfuse privacy).
- The history starts with `b09dfc9ab` "feat: cherry pick dograh custom changes" (30 March 2026), on a fresh upstream commit. We infer the fork was rebuilt then by replaying Dograh's changes onto upstream, and then merged forward by tag.
- Syncs: tag merges on short-lived branches (`merge-v1.12.0` and similar) for 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8.1, 1.10, 1.12 and 1.15. The fork skips 1.6, 1.9, 1.11, 1.13 and 1.14. The lag behind an upstream tag is one to five days.
- After each merge a follow-up commit adapts Dograh code to changed contracts ("Fix Dograh services for Pipecat 1.5 contracts", "Adapt dograh strategies and services to Pipecat 1.7 contracts", "adapt Dograh services to Pipecat 1.8 contracts").
- Two commits are upstream fixes taken early: `9ac08e90b` (TTS text held until audio exists, upstream PR #6234) and `77e137d09` (websocket abort, PR #6490). Their subjects do not match upstream's, so a text search finds no copy. Matching had to be by content.

The fork's only prose record of its own fixes is a `changelog/` folder of seven short notes. There is no `DOGRAH.md`, and the README and CI files are byte-identical to upstream.

## The changes, in groups

### 1. Telephony serializers (new: Asterisk, Vobiz, Cloudonix, call strategies)

Covered in [lesson 6](lesson:pipecat/transports-and-phone-audio). Summary: three new serializers, a `TransferStrategy`/`HangupStrategy` pair, a new `EndTaskReason` enum, and a breaking change to the Vonage constructor (it now requires `call_uuid` and hangs up with a signed REST call). Telnyx lost its built-in hang-up.

### 2. A hosted AI gateway ("Dograh services")

`services/dograh/` adds `DograhLLMService`, `DograhSTTService`, `DograhFluxSTTService` and `DograhTTSService`, all pointing at `services.dograh.com`. The LLM subclasses `OpenAILLMService`, sets `supports_developer_role = False` (the gateway routes to several providers), and adds metadata for correlation and a billing version. A `403 quota_exceeded` becomes a permanent error and an empty stream. The TTS is a websocket service with word timestamps and treats `voice_not_found` as permanent. We infer this is how a user with "no API keys" gets a working call: one key covers all vendors. This is Dograh-specific and unlikely to be upstreamed.

### 3. More providers

MiniMax (LLM, plus a new websocket TTS with retries), HuggingFace (LLM and STT), Speaches (self-hosted). Plus fixes: Sarvam TTS drops punctuation-only fragments that cause HTTP 400, Whisper STT accepts `"text": null`, OpenAI TTS closes its client in `cleanup()`, the Deepgram header logging bug.

### 4. Turn-taking and muting

- `CallbackUserMuteStrategy`: ask your own function whether to mute.
- `LLMUserAggregatorParams.should_interrupt`: a synchronous veto at turn start, so the engine can say "not now".
- Muted realtime transcripts still enter the context.
- A function call during a user turn forces the turn to stop.
- `ExternalUserTurnStopStrategy` ends the turn on a finalized transcript after an external stop.
- `ProposedUserStoppedSpeakingFrame` is uninterruptible, so a queued stop is not eaten by the same turn's start.
- `TurnTrackingObserver` understands mute and attributes a late bot stop to the interrupted turn.

A "provisional VAD" interruption strategy was added and then **reverted**. It is not in the code.

### 5. Tool calls that wait for speech

`is_node_transition` on `register_function`, deferral until `BotStoppedSpeakingFrame`, `NodeTransitionStartedFrame`, and an `on_function_calls_prepared` hook. See [lesson 11](lesson:pipecat/graph-as-llm-tools).

### 6. Spoken-text cleanup (about 760 lines)

`SpokenTextSanitizer`, `SpokenTextProcessor` and `SpokenTextFilter` strip model control syntax from speech and from the history: `<function=...>`, `<think...>`, `<|...|>`, code fences, JSON fragments. They buffer a half-streamed tag across chunks. `XMLFunctionTagFilter` is now an alias for the new filter. We infer the reason: models sometimes say their tool calls out loud.

### 7. Realtime-model changes

Gemini Live: queue tool results during a reconnect and replay them, route connect errors to `push_error`, seed an empty history so the model can greet first, a settings hook to reconnect on a changed system prompt. OpenAI Realtime: explicit 24 kHz PCM defaults. xAI: default transcription model `grok-transcribe` (the docstring says "Dograh needs the user transcripts") and provisional snapshots no longer become final turns. AWS Nova Sonic: audio token counts.

### 8. Recording

`AudioBufferProcessor(use_unmixed_audio_for_bot_track=True)` and `OutputAudioRawFrame.unmixed_audio`: record the bot track from before the ambient mixer, so recordings have no background noise. Both resamplers reset on the same gap so the two tracks stay aligned.

### 9. Transport robustness

A write-failure watchdog (10 failed audio writes cancels the worker), the `bot_vad_stop_secs` parameter, no close frame if the app already closed the socket, a `_transfer_in_progress` flag so a deliberate transfer is not reported as a hang-up, and a no-op `SilenceAudioMixer` whose presence makes the transport stream continuous audio.

### 10. Tracing

`langfuse_helpers.py` (new), ChatML normalization, `llm-<node>` span names, a trace URL helper, `conversation_parent_context` so several stateless text-chat pipelines share one trace, and contextvars for run id and organization id. Traces became **private by default**. One stale comment still says "make trace public".

### 11. Test fixtures shipped inside the package

`pipecat/tests/mock_llm_service.py`, `mock_transport.py` and `mock_tts_service.py`. Dograh's API tests import `mock_transport` 23 times. They let a test run a scripted conversation through the real engine with no provider and no phone. [Lesson 17](lesson:pipecat/what-to-steal) lists this as one to copy.

## What was NOT changed

We searched for the things you might expect and did not find them:

- no ambient-noise mixer in the fork (Dograh's backend builds its own in `api/services/pipecat/audio_mixer.py`; we did not read how),
- no VAD changes (`audio/vad` is identical to upstream),
- no voicemail-detector changes (restored to upstream in `52a758f1b`),
- no `PipecatEngine` and no "stasis" string in the fork: the engine lives in Dograh's main repo,
- no changes to `pyproject.toml`, `README.md` or `.github/` relative to upstream.

## General or Dograh-only?

Our judgement from reading, not a maintainer's view:

| Probably good for upstream | Dograh-only |
|---|---|
| Whisper null-text guard, OpenAI TTS cleanup, Sarvam text filter, Deepgram header fix | `services/dograh/*` and billing metadata |
| `LLMSpecificMessage.is_metadata` for Gemini thought signatures | `EndTaskReason`, `RealtimeFeedbackType`, `run_context` |
| `CallbackUserMuteStrategy`, `should_interrupt`, muted-transcript fix | Langfuse public-trace policy and trace URLs |
| `unmixed_audio` recording option | Strategy injection that removes Telnyx's hang-up |
| MiniMax websocket TTS, HuggingFace, Speaches | Breaking Vonage constructor |
| Asterisk, Vobiz and Cloudonix serializers | `persist_to_logs` and other "engine-side" flags |
| `SpokenTextSanitizer` (would need discussion, it replaces an upstream class) | xAI `grok-transcribe` default |

:::try
Clone `dograh-hq/pipecat`, add upstream as a remote, and run `git diff --stat v1.15.0 HEAD -- src | sort -t'|' -k2 -n -r | head`. Open the top three files. For each, decide: could this have been a subclass in Dograh's own repo instead of a fork edit?
:::

:::check Why is the diff from the merge base misleading?
The fork merged upstream v1.15.0 in one single-parent commit, so Git still reports v1.12.0 as the merge base. A diff from there includes three releases of upstream's own work. Diff against the v1.15.0 tag to see Dograh's changes.
:::

:::check Name two reasons Dograh keeps a fork instead of subclassing Pipecat classes in its own repo.
Some behavior lives in places a subclass cannot reach cleanly: queue and frame rules (`is_node_transition` deferral, uninterruptible frames), core frame classes, the user aggregator. Also, shipping test mocks and new serializers inside the package keeps them next to the code they test.
:::
