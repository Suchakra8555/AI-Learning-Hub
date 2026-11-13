---
title: Frames and processors, from a real run
summary: Pipecat has 147 frame types in three families. You build a two-processor pipeline, watch every hop, and learn the three rules every processor must follow.
time: 20 min
---

Everything in Pipecat is a frame going through a processor. If you understand those two objects, the rest of the framework is detail.

## Frames come in three families

Open `src/pipecat/frames/frames.py` and you find a base class and three families ([lines 75 to 165](https://github.com/dograh-hq/pipecat/blob/9ac08e90be4bb83e506f3d10deaa8e6d31588547/src/pipecat/frames/frames.py)). We counted them in the installed 1.16.0 package:

| Family | Count | Rule | Examples |
|---|---|---|---|
| `SystemFrame` | 60 | Jumps the queue. Handled at once. Never dropped by an interruption. | `StartFrame`, `CancelFrame`, `InterruptionFrame`, `InputAudioRawFrame`, `UserStartedSpeakingFrame`, `MetricsFrame` |
| `DataFrame` | 38 | Handled in order. Dropped when the caller interrupts. | `OutputAudioRawFrame`, `TextFrame`, `TranscriptionFrame`, `FunctionCallResultFrame` |
| `ControlFrame` | 45 | Handled in order. Dropped on interruption, with exceptions. | `EndFrame`, `LLMFullResponseStartFrame`, `TTSStartedFrame` |

The total is 147 frame classes. The other four subclass `Frame` directly (`LLMContextFrame` is one).

Why three families? Because the right behavior differs. Microphone audio must never wait behind a slow reply, so it is a system frame. A half-spoken sentence must be thrown away when the caller cuts in, so it is a data frame. A goodbye must survive, so `EndFrame` is marked `interruptible = False` even though it is a control frame.

Each frame also carries an `id`, a `name` like `TextFrame#1`, an optional presentation timestamp `pts`, and a `metadata` dict.

## What a processor does

Subclass `FrameProcessor` and write one method:

```python
class Upper(FrameProcessor):
    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)   # rule 1
        if isinstance(frame, TextFrame):
            frame = TextFrame(frame.text.upper())
        await self.push_frame(frame, direction)         # rule 2
```

Three rules, learned the hard way by everyone who writes a first processor:

1. **Always call `super().process_frame`.** It handles `StartFrame`, `CancelFrame` and interruptions for you. Skip it and the processor never wakes up.
2. **Frames are not forwarded for you.** If you do not call `push_frame`, the frame stops here. This is how a filter works, and also how you create a silent bug.
3. **Pass the `direction` through.** `DOWNSTREAM` goes from input toward output. `UPSTREAM` goes back. Errors and interruptions travel both ways.

Under the hood each processor has two asyncio tasks and two queues. System frames take a priority lane and are processed immediately. Everything else waits in order ([`frame_processor.py`, lines 140 to 160 and 1354 to 1400](https://github.com/dograh-hq/pipecat/blob/9ac08e90be4bb83e506f3d10deaa8e6d31588547/src/pipecat/processors/frame_processor.py)).

## The real run

`code/pipecat/frames_hello.py` puts `Upper` and a printing processor in a `Pipeline`, queues one `TextFrame("hello")` and an `EndFrame`, and logs every hop with an observer. We ran it. The output, shortened:

```text
PipelineTask#0::Source -> RTVIProcessor#0: StartFrame
RTVIProcessor#0 -> Pipeline#0: StartFrame
Pipeline#0::Source -> Upper#0: StartFrame
Upper#0 -> Printer#0: StartFrame
  sink got: StartFrame#0
...
Upper#0 -> Printer#0: TextFrame
  sink got: TextFrame#1(pts: None, text: [HELLO])
  sink got: EndFrame#0(reason: None)
```

Three things to notice:

- **`StartFrame` arrives first, and nothing else moves until it has passed through every processor.** That is how setup finishes before data flows.
- **A processor you did not write appears.** `RTVIProcessor#0` is added in front of your pipeline automatically by `PipelineWorker`. RTVI is Pipecat's protocol for talking to a browser client. Dograh turns it off (`enable_rtvi=False`) and uses its own messages.
- **Your pipeline is wrapped.** `Pipeline#0::Source` and `Pipeline#0::Sink` are two small processors at the ends. A `Pipeline` is itself a processor, so you can nest pipelines.

<figure>
<svg viewBox="0 0 880 250" role="img" aria-labelledby="t2 d2">
  <title id="t2">One frame's journey in the demo</title>
  <desc>A TextFrame enters at the task source, passes the RTVI processor, the pipeline source, the Upper processor, the Printer processor, the pipeline sink and the task sink. The EndFrame follows right behind it.</desc>
  <defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="13" text-anchor="middle">
    <rect class="box" x="8" y="70" width="104" height="54" rx="10"/><text x="60" y="92">Task</text><text x="60" y="110">source</text>
    <rect class="box" x="132" y="70" width="104" height="54" rx="10"/><text x="184" y="92">RTVI</text><text x="184" y="110">(auto-added)</text>
    <rect class="box" x="256" y="70" width="104" height="54" rx="10"/><text x="308" y="92">Pipeline</text><text x="308" y="110">source</text>
    <rect class="box hot" x="380" y="70" width="104" height="54" rx="10"/><text x="432" y="102">Upper</text>
    <rect class="box hot" x="504" y="70" width="104" height="54" rx="10"/><text x="556" y="102">Printer</text>
    <rect class="box" x="628" y="70" width="104" height="54" rx="10"/><text x="680" y="92">Pipeline</text><text x="680" y="110">sink</text>
    <rect class="box" x="752" y="70" width="104" height="54" rx="10"/><text x="804" y="92">Task</text><text x="804" y="110">sink</text>
  </g>
  <path class="arrow" d="M112 97 H128" marker-end="url(#ah)"/>
  <path class="arrow" d="M236 97 H252" marker-end="url(#ah)"/>
  <path class="arrow" d="M360 97 H376" marker-end="url(#ah)"/>
  <path class="arrow" d="M484 97 H500" marker-end="url(#ah)"/>
  <path class="arrow" d="M608 97 H624" marker-end="url(#ah)"/>
  <path class="arrow" d="M732 97 H748" marker-end="url(#ah)"/>
  <text x="440" y="170" font-size="14" text-anchor="middle">Order seen in the log: StartFrame, then TextFrame, then EndFrame.</text>
  <text x="440" y="196" font-size="13" class="small" text-anchor="middle">Upper rewrites "hello" to "HELLO". Printer prints it. Both frames reach the task sink.</text>
</svg>
<figcaption>One pipeline, seven stops. The two highlighted boxes are the only code we wrote.</figcaption>
</figure>

## Observers

`HopLog` in the demo is a **`BaseObserver`**. It is handed a `FramePushed` record (source, destination, frame, direction, time) every time any processor pushes a frame. It cannot change anything. Dograh's live transcript, its node highlight and its latency numbers all come from observers. Pipecat runs each observer behind its own queue, so a slow observer cannot slow the call ([`worker_observer.py`](https://github.com/dograh-hq/pipecat/blob/9ac08e90be4bb83e506f3d10deaa8e6d31588547/src/pipecat/pipeline/worker_observer.py)).

:::try
Open `code/pipecat/frames_hello.py`. Delete the line `await self.push_frame(frame, direction)` in `Printer`, and run it again. What happens to the output? Then restore the line and delete `await super().process_frame(...)` in `Upper` instead. Which break is louder?
:::

:::check You write a processor that logs every frame but forgets to call push_frame. What does the pipeline do?
Everything after your processor sees nothing. The call goes silent, and there is no error, because dropping a frame is a legal thing for a processor to do.
:::

:::check Why is EndFrame a control frame but still survives an interruption?
Control frames are normally dropped on interruption. `EndFrame` sets `interruptible = False`, so the queue keeps it. A goodbye must not vanish because the caller coughed.
:::
