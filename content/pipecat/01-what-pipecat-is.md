---
title: What Pipecat is, and why Dograh built on it
summary: Pipecat is a Python framework that moves small typed messages through a chain of processors. This lesson shows the chain, the smallest working bot, and what that design gives a product like Dograh.
time: 15 min
---

You know LiveKit Agents. You give it a room, a model and some tools, and the framework runs the conversation. This track opens **Pipecat**, a different framework for the same job, and then opens **Dograh**, a voice platform built on a modified copy of it.

:::warn What we read, and what we ran
We read Dograh at commit `5dfa84c` (12 November 2026) and its Pipecat fork at commit [`9ac08e9`](https://github.com/dograh-hq/pipecat). We ran the small demos in `code/pipecat/` on `pipecat-ai` 1.16.0. We did **not** run Dograh itself, place a phone call through it, or time anything. When a lesson says "Dograh does X", that comes from reading its source with a file path. Where we guess, we say "we infer".
:::

## The problem Pipecat solves

A voice agent is a loop that never stops. Audio comes in, text comes out of a speech model, a language model writes a reply, a voice model turns it into audio, and the audio goes back out. All of that has to happen while the caller can talk over the bot at any moment.

You can write that loop with callbacks and flags. It works for a demo. It breaks when the caller interrupts, because every piece needs to know to stop, and each one stops in a different way.

Pipecat's answer is to make everything a **frame**: a small typed message. A **processor** receives a frame, does one job, and passes frames on. You line processors up in a **pipeline**. An interruption is not a flag. It is one more frame, and every processor knows what to do when it sees one.

<figure>
<svg viewBox="0 0 900 330" role="img" aria-labelledby="t1 d1">
  <title id="t1">A Pipecat voice pipeline</title>
  <desc>Seven processors in a row: transport input, speech to text, user aggregator, language model, text to speech, transport output, assistant aggregator. Frames flow downstream to the right. Some frames, like interruptions and errors, also flow upstream to the left.</desc>
  <defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="10" y="90" width="108" height="60" rx="10"/><text x="64" y="116">transport</text><text x="64" y="134">.input()</text>
    <rect class="box" x="138" y="90" width="108" height="60" rx="10"/><text x="192" y="126">STT</text>
    <rect class="box hot" x="266" y="90" width="108" height="60" rx="10"/><text x="320" y="116">user</text><text x="320" y="134">aggregator</text>
    <rect class="box" x="394" y="90" width="108" height="60" rx="10"/><text x="448" y="126">LLM</text>
    <rect class="box" x="522" y="90" width="108" height="60" rx="10"/><text x="576" y="126">TTS</text>
    <rect class="box" x="650" y="90" width="108" height="60" rx="10"/><text x="704" y="116">transport</text><text x="704" y="134">.output()</text>
    <rect class="box hot" x="778" y="90" width="108" height="60" rx="10"/><text x="832" y="116">assistant</text><text x="832" y="134">aggregator</text>
  </g>
  <path class="arrow" d="M118 120 H134" marker-end="url(#ah)"/>
  <path class="arrow" d="M246 120 H262" marker-end="url(#ah)"/>
  <path class="arrow" d="M374 120 H390" marker-end="url(#ah)"/>
  <path class="arrow" d="M502 120 H518" marker-end="url(#ah)"/>
  <path class="arrow" d="M630 120 H646" marker-end="url(#ah)"/>
  <path class="arrow" d="M758 120 H774" marker-end="url(#ah)"/>
  <text x="450" y="66" font-size="14" font-weight="700" text-anchor="middle">Downstream: audio, text, LLM output, speech audio</text>
  <path class="arrow" stroke-dasharray="5 5" d="M700 168 H70" marker-end="url(#ah)"/>
  <text x="450" y="192" font-size="14" font-weight="700" text-anchor="middle">Upstream: interruptions, errors, "bot started speaking"</text>
  <text x="450" y="236" font-size="13" class="small" text-anchor="middle">The assistant aggregator sits after the output transport, so it sees what was actually played.</text>
  <text x="450" y="262" font-size="13" class="small" text-anchor="middle">Voice activity detection (VAD) and turn rules live inside the user aggregator, not the transport.</text>
</svg>
<figcaption>The standard Pipecat chain. This is the order in Pipecat's own getting-started example, <code>examples/getting-started/06-voice-agent.py</code>.</figcaption>
</figure>

## The smallest real bot

This is the heart of Pipecat's own example, trimmed (the full file has imports and transport settings above it):

```python
stt = DeepgramSTTService(api_key=os.environ["DEEPGRAM_API_KEY"])
tts = CartesiaTTSService(api_key=os.environ["CARTESIA_API_KEY"], settings=...)
llm = OpenAILLMService(api_key=os.environ["OPENAI_API_KEY"], settings=...)

context = LLMContext()
user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
    context,
    user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
)

pipeline = Pipeline([
    transport.input(), stt, user_aggregator, llm, tts,
    transport.output(), assistant_aggregator,
])
worker = PipelineWorker(pipeline, params=PipelineParams(enable_metrics=True))
runner = WorkerRunner()
await runner.add_workers(worker)
await runner.run()
```

Read it top to bottom and you have read the whole bot. There is no hidden session object. The order of the list is the order of the work.

:::note Names changed in version 1.3
Older blog posts use `PipelineTask` and `PipelineRunner`. In 1.16 they still import, but they print a deprecation warning. The current names are `PipelineWorker` and `WorkerRunner`. Our demos use the old names for one reason: they run in fewer lines. Dograh uses the new ones.
:::

## What the design gives a product

Dograh is a platform with a drag-and-drop builder, phone carriers, campaigns and billing. It did not write the real-time core. It uses Pipecat for these reasons (the first four are what we see in the code; the last is our inference):

1. **Services are swappable.** Pipecat has 66 provider folders under `src/pipecat/services/` in the fork. Dograh's service factory picks one by name from a user's settings.
2. **Transports are separate from the brain.** The same pipeline runs over a browser (WebRTC) or a phone carrier (WebSocket). Dograh swaps only the transport.
3. **Serializers handle carrier formats.** A phone carrier's JSON-and-base64 audio becomes frames in one small class.
4. **Observers watch without touching.** Dograh's live transcript and node highlight come from an observer, not from changes inside the pipeline. See [live events](lesson:pipecat/live-events-and-replay).
5. **A pipeline is plain Python, so it can be forked.** Dograh changed Pipecat itself in 167 files. That would be hard with a closed framework. [Lesson 15](lesson:pipecat/what-dograh-changed) lists the changes.

## Run it

```bash
cd code/pipecat
pip install -r requirements.txt
python frames_hello.py
```

No keys needed. The next lesson walks through the output.

:::check In the standard chain, why is the assistant aggregator placed after the output transport and not right after the LLM?
Because it records what the caller actually heard. Words reach it only when they are played. If the caller interrupts, the unplayed words never arrive, so the conversation history keeps only what was spoken. [Lesson 3](lesson:pipecat/interruptions-and-queues) shows how.
:::

:::check What is the difference between a frame and a processor?
A frame is a small typed message, such as a chunk of audio or a piece of text. A processor is an object that receives frames, does one job, and pushes frames on to its neighbors.
:::
