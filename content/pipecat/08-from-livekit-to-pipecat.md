---
title: From LiveKit Agents to Pipecat: a translation table
summary: You know LiveKit. This lesson maps each LiveKit idea to its Pipecat class, and names six differences in how the two frameworks think.
time: 15 min
---

The Pipecat column below is checked against source. The LiveKit column is from general knowledge of LiveKit Agents and we did not re-verify it for this lesson. For LiveKit facts we did check, see the [LiveKit track](lesson:livekit/agents-mental-model).

## The translation

| LiveKit Agents | Pipecat | Where |
|---|---|---|
| `AgentSession` | No single class. A `Pipeline([...])`, a `PipelineWorker`, a `WorkerRunner`. | `pipeline/worker.py`, `workers/runner.py` |
| `Agent` (instructions, tools) | An `LLMService` with `Settings(system_instruction=...)` and an `LLMContext(tools=[...])`. For multi-step behavior: `pipecat.flows` (`FlowManager`, `NodeConfig`). | `flows/manager.py` |
| Worker and job dispatch | **None built in.** You start one bot per connection. `pipecat.runner.run.main()` helps locally. Pipecat Cloud hosts it. | `runner/` |
| Room and participant events | Transport events: `on_client_connected`, `on_first_participant_joined`, `on_participant_left` | transport classes |
| `stt_node`, `llm_node`, `tts_node` | The processors in the list. A custom node is a `FrameProcessor` subclass. | `processors/` |
| Plugins `livekit-plugins-*` | `pipecat.services.<provider>` with install extras | `services/` |
| Silero VAD plugin | `SileroVADAnalyzer` in `LLMUserAggregatorParams(vad_analyzer=...)` | `audio/vad/` |
| Turn detector model | `TurnAnalyzerUserTurnStopStrategy(LocalSmartTurnAnalyzerV3())`, the default | `turns/user_stop/` |
| Endpointing delay, interruption options | `VADParams`, strategy settings, `MinWordsUserTurnStartStrategy`, `should_interrupt` | `turns/` |
| `@function_tool` | An async function with `params: FunctionCallParams`, passed in `LLMContext(tools=[...])` | `services/llm_service.py` |
| Handoffs (return a new agent) | Flows node transitions, `LLMSwitcher`, or multi-worker activation | `flows/`, `workers/` |
| `session.say(...)` | `worker.queue_frames([TTSSpeakFrame("...")])` | |
| `session.generate_reply()` | Add a message, then `LLMRunFrame()` | |
| Chat context | `LLMContext`, written by `LLMContextAggregatorPair` | `processors/aggregators/` |
| Metrics events | `MetricsFrame`, `UserBotLatencyObserver` | `observers/` |
| Realtime models | `OpenAIRealtimeLLMService`, Gemini Live, Grok, Ultravox and more | `services/` |
| SIP trunks | Carrier serializers over a websocket, or Daily SIP. You run the carrier side yourself. | `serializers/` |
| Noise cancellation | `audio_in_filter=` with Krisp, RNNoise or AIC filters | `audio/filters/` |
| Preemptive generation | `EagerUserTurnStopStrategy` and speculative `LLMContextFrame` | `turns/` |

## Six differences that matter

1. **Visible wiring.** LiveKit hides the chain inside the session. Pipecat shows the chain as a list you edit. You gain control and lose a shortcut.
2. **Three frame families decide priority.** What is dropped on interruption is a property of the frame, not a setting on the session.
3. **Interruption is a frame.** You can intercept it, log it or react to it in any processor.
4. **The history records what was played.** The assistant aggregator sits after the output transport.
5. **VAD and turns live in the user aggregator,** not the transport and not the model plugin.
6. **No dispatcher.** LiveKit's worker pool, job dispatch and rooms are a platform feature. In Pipecat, "one process per call" or "one asyncio task per call" is your design. Dograh runs one task per call inside a pool of API processes behind nginx. [Lesson 9](lesson:pipecat/dograh-tour) shows how.

:::note A newer Pipecat feature that sounds like dispatch
Pipecat 1.3 and later have a `workers` package with a message bus and `request_job`, `activate_worker` and Redis or PGMQ backends. That is for several agents cooperating inside one conversation. It is **not** LiveKit-style job dispatch. Dograh uses it in one place: a call worker plus a child agent worker per node visit ([lesson 10](lesson:pipecat/a-call-becomes-a-pipeline)).
:::

## Which one should you pick?

For your own project, a fair summary from what we read: LiveKit gives you rooms, dispatch, SIP and scaling as a platform, and the agent code stays short. Pipecat gives you a smaller kernel and more openness, and you bring the hosting. Dograh's choice tells you something. A product that needed eight carriers, its own turn rules and live graph events picked the framework where the middle of the pipeline is open to change.

:::try
Take a LiveKit agent you wrote. Draw its flow as a Pipecat list: transport, STT, user aggregator, LLM, TTS, output, assistant aggregator. Mark where each of your tools, hooks and settings would go.
:::

:::check In LiveKit you set an endpointing delay on the session. Name two Pipecat settings that play a similar role.
`VADParams.stop_secs` for how long silence must last, and `SpeechTimeoutUserTurnStopStrategy(user_speech_timeout=...)` or the Smart Turn model as the stop strategy for deciding the turn is over.
:::

:::check Pipecat has a workers package with a message bus. Does it replace LiveKit's job dispatch?
No. It coordinates several workers inside one conversation. Starting one bot per incoming call is still your job, or Pipecat Cloud's.
:::
