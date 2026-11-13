---
title: Your path from LiveKit to Dograh contributor
summary: An eight-stage study plan that ends with a merged pull request. Each stage has lessons to read, code to run, one thing to build and a check you can run on yourself.
time: 20 min
---

You said you know LiveKit and nothing about Pipecat, and that you want to reach contributor level. Here is the plan. It is ordered by what each step needs from the one before it. The time estimates are our guess for a working engineer, not measurements.

<figure>
<svg viewBox="0 0 900 270" role="img" aria-labelledby="t19 d19">
  <title id="t19">Eight stages to a first contribution</title>
  <desc>A staircase of eight stages: 1 Pipecat basics, 2 turns and services, 3 transports and observers, 4 Dograh backend, 5 graph engine, 6 builder UI, 7 fork and tests, 8 first pull request.</desc>
  <g font-size="12" text-anchor="middle">
    <rect class="box" x="10" y="200" width="100" height="56" rx="8"/><text x="60" y="224">1 Pipecat</text><text x="60" y="242">basics</text>
    <rect class="box" x="120" y="178" width="100" height="78" rx="8"/><text x="170" y="206">2 Turns,</text><text x="170" y="224">services,</text><text x="170" y="242">tools</text>
    <rect class="box" x="230" y="156" width="100" height="100" rx="8"/><text x="280" y="190">3 Transports,</text><text x="280" y="208">observers</text>
    <rect class="box" x="340" y="134" width="100" height="122" rx="8"/><text x="390" y="176">4 Dograh</text><text x="390" y="194">backend</text>
    <rect class="box hot" x="450" y="112" width="100" height="144" rx="8"/><text x="500" y="170">5 Graph</text><text x="500" y="188">engine</text>
    <rect class="box hot" x="560" y="90" width="100" height="166" rx="8"/><text x="610" y="168">6 Builder</text><text x="610" y="186">UI</text>
    <rect class="box" x="670" y="68" width="100" height="188" rx="8"/><text x="720" y="160">7 Fork,</text><text x="720" y="178">tests, CI</text>
    <rect class="box hot" x="780" y="46" width="110" height="210" rx="8"/><text x="835" y="150">8 First</text><text x="835" y="168">pull</text><text x="835" y="186">request</text>
  </g>
</svg>
<figcaption>Each stage builds on the one before. Stages 5 and 6 are the Dograh heart.</figcaption>
</figure>

## Stage 1: Pipecat basics (about 3 hours)

- **Read:** [what Pipecat is](lesson:pipecat/what-pipecat-is), [frames and processors](lesson:pipecat/frames-and-processors), [interruptions](lesson:pipecat/interruptions-and-queues).
- **Run:** `frames_hello.py` and `interruption_demo.py` in `code/pipecat/`.
- **Build:** a processor that counts words in `TextFrame`s and pushes a summary text frame before `EndFrame`. Test it with `queue_frames`, as in the demos.
- **You are ready when** you can explain, without notes, why `InterruptionFrame` jumps the queue and what the queue does with `EndFrame`.

## Stage 2: Turns, services, tools (about 5 hours)

- **Read:** [turns and VAD](lesson:pipecat/turns-vad-and-context), [services and tool calls](lesson:pipecat/services-and-tool-calls), [the LiveKit translation table](lesson:pipecat/from-livekit-to-pipecat).
- **Run:** clone `pipecat-ai/pipecat` and run the `getting-started/06-voice-agent.py` and `07-function-calling.py` examples with your own keys. We did not run these, because they need provider accounts.
- **Build:** port one small LiveKit agent you wrote to Pipecat. Keep a table of what was easy and what was not.
- **You are ready when** you can change a bot from "interrupt on any speech" to "needs three words" using a start strategy, and say what that does to a cough.

## Stage 3: Transports and observers (about 4 hours)

- **Read:** [transports and serializers](lesson:pipecat/transports-and-phone-audio), [observers and metrics](lesson:pipecat/observers-metrics-and-tracing), then the earlier [phone audio](lesson:voice-prod/phone-audio-is-different) lesson.
- **Run:** `frames_to_events.py`.
- **Build:** an observer that writes one JSON line per turn with `TurnTrackingObserver`, including whether it was interrupted.
- **You are ready when** you can say where VAD, noise filtering and resampling each happen.

## Stage 4: Dograh backend (about 6 hours)

- **Read:** [tour](lesson:pipecat/dograh-tour), [a call becomes a pipeline](lesson:pipecat/a-call-becomes-a-pipeline), [telephony](lesson:pipecat/telephony-registry-and-campaigns).
- **Do:** run Dograh locally (the setup steps are in [lesson 18](lesson:pipecat/contribute-to-dograh)). Make a test call from the browser. Open `run_pipeline.py` next to the lesson and find each step.
- **Build:** add a log line at the point where the pipeline's processor list is built and confirm the order matches the lesson.
- **You are ready when** you can draw the call path from a Twilio webhook to `_run_pipeline_impl` from memory.

## Stage 5: The graph engine (about 6 hours)

- **Read:** [graph as tools](lesson:pipecat/graph-as-llm-tools).
- **Run:** `mini_workflow.py`, then extend it as the lesson's exercise suggests.
- **Do:** in the Dograh repo, read `workflow_graph.py`, `pipecat_engine_context_composer.py` and `_create_transition_func`. Run `api/tests/test_pipecat_engine_tool_calls.py` and read what it asserts.
- **Build:** a failing test for a graph with a duplicate tool name through the API validation route, then check it passes.
- **You are ready when** you can explain why `set_node` runs before `result_callback`.

## Stage 6: The builder UI (about 8 hours)

- **Read:** [the builder](lesson:pipecat/the-visual-builder), [live events](lesson:pipecat/live-events-and-replay).
- **Do:** run the UI. Add a node, connect it, break validation on purpose, undo twice. Watch the network tab during a test call and find the `rtf-` messages. Read `RenderWorkflow.tsx` around the `<ReactFlow>` element and `GenericNode.tsx`.
- **Build:** a vitest test for `CustomEdge` or `AddNodePanel` (idea 4 in [lesson 18](lesson:pipecat/contribute-to-dograh)). You will need basic TypeScript and React. If you have none, spend a weekend on it first.
- **You are ready when** you can explain where `runtime_active` is set and why it never reaches the database.

## Stage 7: The fork, tests and CI (about 5 hours)

- **Read:** [what changed](lesson:pipecat/what-dograh-changed), [living with a fork](lesson:pipecat/living-with-a-fork), [what to steal](lesson:pipecat/what-to-steal).
- **Do:** clone the fork, add upstream, reproduce the `v1.15.0..HEAD` numbers, read `mock_transport.py` and one test that uses it.
- **Build:** a scripted-conversation test with the mock transport and mock LLM.
- **You are ready when** you can classify any patched file as keep, take theirs or rework.

## Stage 8: Your first pull request (about a weekend)

- Pick idea 1, 2 or 7 from [lesson 18](lesson:pipecat/contribute-to-dograh). Open an issue or ask in Slack first.
- Use a conventional title, link the issue, run format, lint and tests locally.
- Keep it small. A merged small change teaches you more than a closed large one.
- Then pick something from stage 5 or 6, and after that a provider.

## A realistic sequence of contributions

1. Docs or CI fix (stage 8).
2. UI tests for one canvas component.
3. A bug fix from the issue list, with a reproduction.
4. A feature in an area you have studied (the path overlay is a UI-and-API task that uses everything from stages 5 and 6).
5. A provider integration, with the evidence checklist.
6. A change to the Pipecat fork, discussed first.

## Beyond this course

- Read upstream Pipecat's `CHANGELOG.md` monthly. Dograh trails it by days, so its direction follows upstream.
- Pipecat's own examples folder has `flows/`, `turn-management/`, `observability/` and `multi-worker/` directories we only mention. Work through one.
- Dograh's `.agents/skills/review-pr` shows what its maintainers check in a review. Read it before your first pull request.
- Compare with the [LiveKit track](lesson:livekit/agents-mental-model) after each stage. The contrast is where you learn the most.

:::say
Learn Pipecat's frames, then Dograh's graph, then ship one small, well-evidenced pull request.
:::

:::check What is your first pull request, and what is its check on yourself?
Ideas 1, 2 or 7 from lesson 18. You are done when CI is green, the title is conventional, and a maintainer can understand it without a call.
:::
