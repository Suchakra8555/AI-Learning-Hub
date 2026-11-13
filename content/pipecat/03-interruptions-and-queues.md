---
title: Interruptions: what really happens when the caller talks over the bot
summary: An interruption is one frame that cancels the work in flight and empties the queues. You run it, read the timeline, and see why the chat history keeps only what was spoken.
time: 20 min
---

A caller says "wait, no" while the bot is halfway through a sentence. What must happen? The bot must stop talking. The text still waiting to be spoken must be thrown away. The language model call that was streaming must be cancelled. And the chat history must not claim the bot said words it never said.

In many stacks each of those is its own piece of code. In Pipecat it is one frame, `InterruptionFrame`, and a rule every processor follows.

## An experiment

`code/pipecat/interruption_demo.py` builds a processor that "speaks" five words at 0.3 seconds each. At 0.75 seconds the script pushes an `InterruptionFrame`, as if the caller had spoken. Here is the real output:

```text
 0.00s  system  StartFrame#0
 0.30s  data    TextFrame#0(pts: None, text: [word0])
 0.60s  data    TextFrame#1(pts: None, text: [word1])
 0.75s  system  OutputTransportMessageUrgentFrame#0(message: {'label': 'rtvi-ai', 'type': 'bot-interrupted'})
 0.75s  system  InterruptionFrame#0
 1.25s  data    TextFrame#5(pts: None, text: [after])
 1.25s  control EndFrame#0(reason: None)
```

Read it line by line:

- `word0` and `word1` came out at 0.30 and 0.60 seconds. Normal.
- `word2` was being "spoken" when the interruption hit at 0.75 seconds. It never appears. Its work was **cancelled** in flight.
- `word3` and `word4` were waiting in the queue. They never appear either. The queue was **emptied**.
- The `InterruptionFrame` itself arrived at 0.75 seconds exactly, with no wait. It is a system frame, so it skipped the line.
- `after`, sent later, flows normally. The pipeline is healthy again, only 0.5 seconds after the cut.
- Pipecat also announced the interruption to a browser client (`bot-interrupted`). That is the auto-added RTVI processor from the last lesson.

<figure>
<svg viewBox="0 0 880 300" role="img" aria-labelledby="t3 d3">
  <title id="t3">Timeline of the interruption experiment</title>
  <desc>A time axis from 0 to 1.25 seconds. Words 0 and 1 complete at 0.3 and 0.6 seconds. Word 2 is in progress when the interruption arrives at 0.75 seconds and is cancelled. Words 3 and 4 are dropped from the queue. The word after arrives at 1.25 seconds.</desc>
  <g font-size="13" text-anchor="middle">
    <path class="arrow" d="M40 200 H850" />
    <text x="40" y="226">0.0 s</text><text x="300" y="226">0.5 s</text><text x="560" y="226">1.0 s</text><text x="810" y="226">1.25 s</text>
    <rect class="box" x="40" y="120" width="104" height="44" rx="8"/><text x="92" y="147">word0</text>
    <rect class="box" x="148" y="120" width="104" height="44" rx="8"/><text x="200" y="147">word1</text>
    <rect class="box hot" x="256" y="120" width="86" height="44" rx="8"/><text x="299" y="147">word2 cut</text>
    <rect class="box" x="400" y="120" width="104" height="44" rx="8" stroke-dasharray="5 5"/><text x="452" y="147">word3 dropped</text>
    <rect class="box" x="508" y="120" width="104" height="44" rx="8" stroke-dasharray="5 5"/><text x="560" y="147">word4 dropped</text>
    <rect class="box hot" x="740" y="120" width="104" height="44" rx="8"/><text x="792" y="147">after</text>
  </g>
  <path class="arrow" d="M342 60 V196" stroke-dasharray="3 4"/>
  <text x="342" y="48" font-size="14" font-weight="700" text-anchor="middle">0.75 s: InterruptionFrame</text>
  <text x="440" y="270" font-size="13" class="small" text-anchor="middle">Positions are schematic. The times in the log are real.</text>
</svg>
<figcaption>What the log shows: one frame, three effects. Work in flight is cancelled, queued work is dropped, the pipeline recovers at once.</figcaption>
</figure>

## How a processor does it

The code is in [`FrameProcessor._start_interruption`](https://github.com/dograh-hq/pipecat/blob/9ac08e90be4bb83e506f3d10deaa8e6d31588547/src/pipecat/processors/frame_processor.py), simplified here from the version we read:

```python
current = self.__process_current_frame
current_is_uninterruptible = current is not None and not current.interruptible
if current_is_uninterruptible:
    self.__reset_process_queue()          # drop queued interruptible frames, keep the in-flight one
else:
    await self.__cancel_process_task()    # cancel the coroutine that is mid-work
    self.__create_process_task()          # start a fresh worker for the next frame
```

`FrameQueue.reset()` empties the queue but puts back any frame with `interruptible = False`. That is why `EndFrame` and `FunctionCallResultFrame` survive. A tool result must reach the chat history even if the caller barged in, or the model would later call the tool again.

Cancelling the task is plain asyncio cancellation. An LLM stream or a TTS request that is being awaited gets a `CancelledError` and stops.

## The output transport has its own rule

Audio is cut into small chunks before it leaves. At 24 kHz mono with 16-bit samples, a 10 ms slice is 480 bytes, and Pipecat sends four of them at once: 1,920 bytes, 40 ms ([`base_output.py`, lines 134 to 151](https://github.com/dograh-hq/pipecat/blob/9ac08e90be4bb83e506f3d10deaa8e6d31588547/src/pipecat/transports/base_output.py)). Smaller chunks mean less audio is already "out the door" when the cut arrives.

On an interruption the output transport empties its audio queue, drops half-filled buffers, stops the playback clock, and announces `BotStoppedSpeakingFrame(interrupted=True)`. The audio task keeps running so a background-noise mixer does not click.

## Why the history stays honest

The assistant aggregator sits **after** the output transport. Words reach it only when playback reaches them: the transport holds timed text frames until their presentation time. When the interruption arrives, the aggregator runs `_trigger_assistant_turn_stopped(interrupted=True)` and commits only what it has seen so far.

So after "I can book you for Tues-" is cut off, the history holds "I can book you for Tues", not the whole planned sentence. The model's next turn knows what the caller actually heard. We read this from the aggregator and transport code and from comments in `tts_service.py`; we did not trace a live call to confirm it end to end.

Dograh depends on this. Its fork added `BotStoppedSpeakingFrame.interrupted` and `interruption_id`, and a rule that drops a deferred tool call if an interruption comes before the bot finishes speaking. [Lesson 15](lesson:pipecat/what-dograh-changed) covers it.

## Compared with LiveKit

LiveKit Agents also handles interruptions, but as session behavior you configure (and, from general knowledge, override with node hooks). Pipecat makes the mechanism visible: the frame is in your pipeline, you can log it, and you can write a processor that reacts to it. The price is that you own more wiring.

:::try
Change `asyncio.sleep(0.75)` in `interruption_demo.py` to `0.1`, then to `2.0`. At what point does `word0` stop appearing? At what point does the interruption change nothing?
:::

:::check Why is InterruptionFrame a system frame and not a data frame?
Data frames wait in line behind the work they are meant to cancel. A system frame is handled at once, so the cancel arrives while the work is still in flight.
:::

:::check The caller interrupts while a tool call is running. Why does FunctionCallResultFrame stay in the queue?
It is marked uninterruptible. The tool's answer must reach the chat history, or the model will not know the tool ran and may run it again.
:::
