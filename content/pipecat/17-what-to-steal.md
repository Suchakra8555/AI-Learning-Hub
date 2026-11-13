---
title: What a voice engineer should steal from Dograh
summary: Ten patterns worth copying, six weak spots to avoid, and the questions to ask of any voice platform you read.
time: 20 min
---

This lesson answers "what should I learn from them?". Each pattern has evidence in the code and a way to use it in your own project, LiveKit or Pipecat.

## Ten patterns to copy

**1. Make the graph the product, the model the judge.** Nodes narrow what the model sees. Edges become tools. You get readable logs and editable flows ([lesson 11](lesson:pipecat/graph-as-llm-tools)). Works in LiveKit too: hand-offs between agents are the same idea.

**2. Let the backend declare node types.** One generic renderer plus a spec catalog means a new node type needs no frontend code. Two implementations of one rule (display options) are locked by one shared fixture ([lesson 12](lesson:pipecat/the-visual-builder)).

**3. Registry-driven carriers.** A provider is a folder, one `ProviderSpec`, and two lines elsewhere. The call path never names a carrier ([lesson 14](lesson:pipecat/telephony-registry-and-campaigns)).

**4. Split the call from the agent.** Keep the connection, recording and history in one worker. Put model, voice and prompt in a child worker you can replace ([lesson 10](lesson:pipecat/a-call-becomes-a-pipeline)). In LiveKit you would get the same result with a session that survives agent changes.

**5. Pin the definition a call started with.** Editing an agent never changes a live call.

**6. One shutdown path.** A `TerminationFunnelProcessor` right behind the input transport sends every cancel and end request to a single `end_call`. Status ("what happened") is observed. Disposition ("how did it go") is extracted later and mapped per organization. Keeping the two separate stops an LLM from rewriting facts.

**7. Defer the action until the bot has finished speaking.** A tool that moves the call forward waits for `BotStoppedSpeakingFrame`, and is dropped if the caller interrupts. This fixed real bugs (a transition firing mid-sentence).

**8. Clean what the model says before it is spoken or stored.** A buffering filter removes tool-call syntax, thinking tags and code fences, even when a tag is split across streamed chunks.

**9. Ship test doubles with the framework.** Mock LLM, mock transport and mock TTS let Dograh run scripted conversations through the real engine in CI, with no provider and no phone. Dograh's API tests import the mock transport 23 times.

**10. Write the incident into the code.** The ARQ retry comment names the day all workers died and why. The telephony token `TODO(security)` says the token is replayable. Comments like these are how a team remembers.

## Operations ideas that are easy to miss

- **Balance long WebSockets across processes.** One uvicorn worker per process behind nginx `least_conn`.
- **Drain accounting.** The call is registered as active *before* async setup, and `/health/active-calls` feeds autoscaling, so a scale-down does not kill live calls.
- **Per-organization trace routing.** Credentials sync over Redis pub/sub, so one deployment serves many customers' Langfuse projects.
- **A fallback model list.** A fallback LLM policy wraps the primary in a processor with routes.
- **Overlap the pre-call fetch with setup**, then build the first agent's models after it settles.

## Six weak spots to avoid

Evidence from the code, not a verdict on the team:

1. **Giant factories.** `service_factory.py` is 2,029 lines of provider branches. `pipecat_engine.py` is 2,593. Adding a provider means touching a central file in several places.
2. **No cycle rule.** Graph cycles are allowed and unchecked (`workflow_graph.py:334`).
3. **Private overrides of Pipecat** that break silently on upgrade ([lesson 16](lesson:pipecat/living-with-a-fork)).
4. **A replayable media socket token,** with enforcement off by default.
5. **An in-process WebSocket registry** for live events. It works only when signaling and the pipeline share a process, and phone calls get no live view.
6. **Singletons in the API container,** with manual toggles for scale-out, and migrations on every container start.

Also: UI tests exist (72 files) and CI never runs them (we grepped `.github/workflows`). The Node version differs across `.nvmrc` (24), CI (22) and the Vercel deploy (20).

## Questions to ask of any voice platform

Use these on the next codebase you read:

1. What is the one function every call passes through?
2. Where is "who is talking" decided, and can the app veto it?
3. What happens to queued speech, tool calls and recordings on an interruption?
4. Which shutdown paths exist, and do they converge?
5. What does a carrier need to implement, and how many files does it touch?
6. How do you test a conversation without calling anyone?
7. What would break first if the framework underneath changed?

:::try
Pick one of the ten patterns and sketch it in your LiveKit project. Which LiveKit class plays the role of the registry, the child worker or the termination funnel?
:::

:::check Which pattern makes live calls immune to someone editing the agent?
Pinning the workflow definition. The run loads the definition stored with it when it started, not the current one.
:::

:::check Why does separating call status from call disposition matter?
Status is observed by the system and cannot be wrong. Disposition comes from model judgement and may change after review. Mixing them lets a model overwrite facts.
:::
