---
title: Never block the audio loop
summary: One ordinary blocking call inside async code stalls every frame of audio on that process. See it happen in a 40-line script, then learn the patterns the platform uses, and the one it still gets wrong.
time: 20 min
---

The caller's audio arrives every 20 ms. The agent's audio has to leave every 20 ms. Now add one line in an event handler that writes to Redis and waits 50 ms for the reply. Nothing crashes and no error is logged, but the audio stutters, and only while the caller is talking, because that is when the handler runs.

## One thread, many jobs

Both the media bridge and the agent worker run on an **event loop**: one thread that switches between many tasks. Python's asyncio loop is cooperative. A task gives up control only at an `await`. A normal function call that waits on the network, without `await`, holds the thread until it returns. Every other task on that loop waits with it.

Python's docs put it plainly: blocking code "should not be called directly", because if it runs for 1 second, "all concurrent asyncio Tasks and IO operations would be delayed by 1 second" ([asyncio dev guide](https://docs.python.org/3/library/asyncio-dev.html#running-blocking-code)). Debug mode logs any callback that takes longer than 100 ms. For audio, 100 ms is already far too late.

<figure>
<svg viewBox="0 0 760 330" role="img" aria-labelledby="t-loop d-loop">
  <title id="t-loop">A 50 ms block stalls a 20 ms frame clock</title>
  <desc id="d-loop">Three timelines from 0 to 200 ms. Top: frames every 20 ms. Middle: a blocking 50 ms publish starts at 80 ms, just as the next frame is due, so that frame runs at 130 ms, 70 ms after the one before it. Bottom: the same publish runs in a worker thread and every frame stays on time.</desc>
  <defs><marker id="ah-loop" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" font-weight="700">
    <text x="50" y="30">Nothing blocking: a frame every 20 ms</text>
    <text x="50" y="110">Sync publish of 50 ms, starting at 80 ms</text>
    <text x="50" y="200">Same publish with asyncio.to_thread</text>
  </g>
  <g>
    <rect class="box" x="45" y="42" width="10" height="26"/><rect class="box" x="109" y="42" width="10" height="26"/><rect class="box" x="173" y="42" width="10" height="26"/><rect class="box" x="237" y="42" width="10" height="26"/><rect class="box" x="301" y="42" width="10" height="26"/><rect class="box" x="365" y="42" width="10" height="26"/><rect class="box" x="429" y="42" width="10" height="26"/><rect class="box" x="493" y="42" width="10" height="26"/><rect class="box" x="557" y="42" width="10" height="26"/><rect class="box" x="621" y="42" width="10" height="26"/><rect class="box" x="685" y="42" width="10" height="26"/>
  </g>
  <g>
    <rect class="box" x="45" y="122" width="10" height="26"/><rect class="box" x="109" y="122" width="10" height="26"/><rect class="box" x="173" y="122" width="10" height="26"/><rect class="box" x="237" y="122" width="10" height="26"/>
    <rect class="box hot" x="306" y="122" width="154" height="26" rx="4"/>
    <rect class="box hot" x="461" y="122" width="10" height="26"/><rect class="box" x="525" y="122" width="10" height="26"/><rect class="box" x="589" y="122" width="10" height="26"/><rect class="box" x="653" y="122" width="10" height="26"/>
  </g>
  <text x="383" y="140" font-size="13" text-anchor="middle">publish() 50 ms</text>
  <path class="arrow" d="M242 164 H466" marker-start="url(#ah-loop)" marker-end="url(#ah-loop)"/>
  <text x="354" y="182" font-size="13" class="small" text-anchor="middle">gap of 70 ms: the frame due at 80 ms ran at 130 ms</text>
  <g>
    <rect class="box" x="45" y="212" width="10" height="26"/><rect class="box" x="109" y="212" width="10" height="26"/><rect class="box" x="173" y="212" width="10" height="26"/><rect class="box" x="237" y="212" width="10" height="26"/><rect class="box" x="301" y="212" width="10" height="26"/><rect class="box" x="365" y="212" width="10" height="26"/><rect class="box" x="429" y="212" width="10" height="26"/><rect class="box" x="493" y="212" width="10" height="26"/><rect class="box" x="557" y="212" width="10" height="26"/><rect class="box" x="621" y="212" width="10" height="26"/><rect class="box" x="685" y="212" width="10" height="26"/>
  </g>
  <rect class="box" x="306" y="248" width="160" height="26" rx="4"/>
  <text x="386" y="266" font-size="13" text-anchor="middle">worker thread: 50 ms</text>
  <path class="arrow" d="M50 300 H690"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="50" y="318">0 ms</text><text x="370" y="318">100 ms</text><text x="690" y="318">200 ms</text>
  </g>
</svg>
<figcaption>The blocked loop still runs every frame, just late, and on a phone call late audio sounds like a stutter.</figcaption>
</figure>

## The script

`code/voice-prod/blocking_loop.py` runs an audio pump that wants a frame every 20 ms. Next to it, a transcript handler publishes 10 events, each taking 50 ms. First the publish blocks, then it runs in a thread:

```python
async def on_transcript(mode, n=10):
    for _ in range(n):         # one event per partial transcript
        await asyncio.sleep(0.08)
        if mode == "blocking":
            slow_publish()                       # blocks the loop
        else:
            await asyncio.to_thread(slow_publish)  # loop keeps running
```

```text
blocking  worst gap  70.7 ms, frames later than 30 ms: 10/50
to_thread worst gap  25.5 ms, frames later than 30 ms: 0/50
```

Ten publishes, ten late frames. The worst gap is about 70 ms: the 20 ms the pump was already waiting, plus the 50 ms block. With `to_thread` the worst gap was 25 to 28 ms across several runs, and no frame crossed 30 ms. On a busy machine you may see one stray late frame in the `to_thread` run. That is ordinary scheduling noise, not the publish.

**`asyncio.to_thread`** runs a normal function "in a separate thread" and gives back something you can `await` ([asyncio docs](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)). The loop stays free while the thread waits.

:::try
Change `time.sleep(0.05)` in `slow_publish` to `time.sleep(0.2)`. Predict two numbers before running: the worst gap, and how many frames are late. Hint: does a longer block make more publishes happen?
:::

## What the platform does right

The agent worker fetches its STT, LLM and TTS secrets with `asyncio.gather` over three `to_thread` calls, so three slow lookups cost one wait. The bridge has three patterns worth copying.

- **Race, then cancel.** A call ends either when the carrier socket closes or when the room closes. The bridge starts both waits as tasks and uses `asyncio.wait(..., return_when=FIRST_COMPLETED)`, which returns "when any future finishes or is cancelled". Then it cancels the other one.
- **One writer at a time.** Agent audio frames, the barge-in clear command and the hang-up message all go out on the same socket. A **send lock** (an `asyncio.Lock`) lets one write finish before the next starts, and nothing gets sent after the socket closes.
- **Keep task references.** The docs warn that the loop "only keeps weak references to tasks", so a task nobody references "may get garbage collected at any time, even before it's done" ([create_task](https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task)). The bridge puts fire-and-forget tasks in a set and removes each one when it finishes.

:::warn Gotcha from the platform
The event bus uses a sync Redis client. The agent's transcript handler calls it directly on the event loop, for every partial transcript, not only the final ones. Each publish is a network round trip that holds the loop running the call's STT, LLM and TTS. On a nearby Redis that's usually short. When Redis is slow, every live call on that worker stalls with it. This is still open. The fix is to move the publish off the loop (an async client, `to_thread`, or a queue drained by one publisher task) and to stop publishing every partial.
:::

## Backpressure, and why there is almost none

**Backpressure** is how a fast producer gets slowed down, or has its excess dropped, when the consumer can't keep up. Without it, data piles up in buffers and arrives later and later.

The platform has essentially none. Caller audio goes from the socket straight into the LiveKit audio source, frame by frame. Agent audio is forwarded as it arrives. If the loop stalls, frames queue in socket buffers and play back late. For live audio, old frames are worth less than new ones, so a bounded queue that drops the oldest is the usual shape. A fresh sketch:

```python
q = asyncio.Queue(maxsize=10)        # 10 frames = 200 ms of audio

def offer(frame):
    if q.full():
        q.get_nowait()               # drop the oldest; late audio is useless
    q.put_nowait(frame)
```

:::note What we did not test
We did not measure how long the platform's Redis publish takes in production, or how much it stalls a real call. The script uses `time.sleep` as a stand-in for a slow network call. The backpressure sketch is our own, written to show the shape.
:::

## The rule

On an audio loop, every call that can wait on the network needs an `await`. If the library has no async version, wrap it in `to_thread`. Keep a reference to every task you start, and give every queue a limit.

:::say
A sync call inside async code makes every other call on that loop wait until it returns.
:::

:::check Why was the worst gap about 70 ms when the block was only 50 ms?
The pump had already started a 20 ms sleep. The block took 50 ms of the loop's time, so the pump woke 20 + 50 = 70 ms after its last frame.
:::

:::check In the try exercise, why did the late-frame count stay at 10 when the block grew to 200 ms?
There are still only 10 publishes, and each one causes one long gap. A longer block makes each gap longer. It doesn't add publishes.
:::

Next: [Tuning turns as pure functions](lesson:voice-prod/tuning-turns-as-pure-functions)
