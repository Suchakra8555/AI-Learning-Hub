---
title: Events that don't lie
summary: Call events drive customer webhooks, recordings and transcripts. Learn how Redis Streams consumer groups deliver them, why at-least-once means every handler must be idempotent, and the four gaps the platform still has.
time: 20 min
---

A customer says their `call.ended` webhook fired twice. Another says it never fired. You deploy a new service with its own consumer group, and the first thing it does is work through every call event from the past month. Each of these is normal behavior for the same event bus when you haven't planned for it.

## Redis Streams in a few commands

A **Redis Stream** is an append-only log. Each entry gets an id that grows over time. The commands you need ([Redis streams intro](https://redis.io/docs/latest/develop/data-types/streams/)):

- **XADD** appends an entry. With `MAXLEN ~ 1000` it also trims old entries. The `~` asks for "approximate trimming", which is "more efficient" and may leave a few extra entries ([XADD](https://redis.io/docs/latest/commands/xadd/)).
- A **consumer group** is a named reader with its own position in the stream. Every group sees every entry. Inside a group, each entry goes to one consumer.
- **XREADGROUP** with the id `>` returns entries never delivered to anyone in the group. Each delivered entry goes on the group's **pending entries list (PEL)**: "a list of message IDs delivered but not yet acknowledged" ([XREADGROUP](https://redis.io/docs/latest/commands/xreadgroup/)).
- **XACK** removes an entry from the PEL once it's handled.
- **XAUTOCLAIM** hands entries that have sat pending longer than a set idle time to another consumer, and increments their delivery count ([XAUTOCLAIM](https://redis.io/docs/latest/commands/xautoclaim/)).

A consumer can crash after doing the work but before XACK. The entry stays pending and gets delivered again. That is **at-least-once delivery**: nothing is lost, but anything can arrive twice. So every handler must be **idempotent**, meaning that running it twice on the same event has the same effect as running it once. The usual way is to store each event's id when you handle it and skip ids you've seen.

<figure>
<svg viewBox="0 0 760 360" role="img" aria-labelledby="t-stream d-stream">
  <title id="t-stream">One stream, two consumer groups, one dead-letter stream</title>
  <desc id="d-stream">A producer appends entries 1 to 6 to the call events stream. The webhook dispatcher group has delivered up to entry 4 and has entry 3 pending because it failed. The recording group has delivered up to entry 6 with nothing pending. After too many failed tries, entry 3 moves to a dead-letter stream.</desc>
  <defs><marker id="ah-stream" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="16" y="34" width="120" height="44" rx="10"/><text x="76" y="61">XADD</text>
    <rect class="box" x="160" y="34" width="70" height="44" rx="6"/><text x="195" y="61">1</text>
    <rect class="box" x="240" y="34" width="70" height="44" rx="6"/><text x="275" y="61">2</text>
    <rect class="box hot" x="320" y="34" width="70" height="44" rx="6"/><text x="355" y="61">3</text>
    <rect class="box" x="400" y="34" width="70" height="44" rx="6"/><text x="435" y="61">4</text>
    <rect class="box" x="480" y="34" width="70" height="44" rx="6"/><text x="515" y="61">5</text>
    <rect class="box" x="560" y="34" width="70" height="44" rx="6"/><text x="595" y="61">6</text>
  </g>
  <text x="160" y="24" font-size="13" class="small">Call events stream (oldest on the left)</text>
  <text x="645" y="54" font-size="12" class="small">MAXLEN trims</text>
  <text x="645" y="70" font-size="12" class="small">from the left</text>
  <path class="arrow" d="M136 56 H156" marker-end="url(#ah-stream)"/>
  <rect class="box" x="16" y="140" width="340" height="104" rx="10"/>
  <rect class="box" x="400" y="140" width="340" height="104" rx="10"/>
  <g font-size="14">
    <text x="32" y="166" font-weight="700">Webhook dispatcher group</text>
    <text x="32" y="192">last delivered: 4</text>
    <text x="32" y="218">pending (PEL): 3, failed, not acked</text>
    <text x="416" y="166" font-weight="700">Recording group</text>
    <text x="416" y="192">last delivered: 6</text>
    <text x="416" y="218">pending (PEL): none</text>
  </g>
  <path class="arrow" stroke-dasharray="5 5" d="M435 80 C435 110 260 110 240 136" marker-end="url(#ah-stream)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M595 80 V136" marker-end="url(#ah-stream)"/>
  <rect class="box hot" x="16" y="290" width="340" height="50" rx="10"/>
  <text x="186" y="320" font-size="14" text-anchor="middle">Dead-letter stream: entry 3 after 3 tries</text>
  <path class="arrow" d="M186 244 V286" marker-end="url(#ah-stream)"/>
  <text x="200" y="272" font-size="12" class="small">XAUTOCLAIM retries, then gives up</text>
  <text x="400" y="310" font-size="13" class="small">Each group keeps its own position and PEL.</text>
  <text x="400" y="330" font-size="13" class="small">A slow group never holds back a fast one.</text>
</svg>
<figcaption>Groups read the same stream independently. A dead-letter stream is where a message goes when retrying it stops making sense. The platform doesn't have one yet.</figcaption>
</figure>

## How the platform uses it

There is one stream for call events. Each entry is a small envelope: an event id, the event type, org, assistant and call ids, a JSON payload, and a timestamp. Call orchestration and the agent worker publish. The webhook dispatcher and the recording service each own a consumer group. Each runs its consumer loop in a daemon thread inside its web process, with a sync Redis client and a 5 s blocking read. It acks after the handler returns. If the handler raises, the entry stays pending.

:::warn Gotcha from the platform
Redis's docs say a blocking XREADGROUP that times out returns a nil reply. In the platform's setup, the Python client raised `TimeoutError` instead, right around when the 5 s block ran out with no new events. The loop treated that as a crash. Every consumer restarted about every 5 s, re-ran the group setup and logged an error, even with zero traffic. Only a real run showed it. The fix: treat a timed-out read the same as an empty one.
:::

## The four gaps

| Gap | What happens | The fix |
|---|---|---|
| No XAUTOCLAIM | After a failure the loop goes back to reading `>`, which only returns new entries. A failed entry sits in the PEL forever. | Periodically XAUTOCLAIM entries idle for, say, a minute. |
| No dead-letter queue | A **poison message** (one that fails every time) has nowhere to go. | After N tries, copy it to a **dead-letter queue**, a separate stream a human checks, and XACK the original. |
| Groups start at id 0 | XGROUP CREATE takes "`$` for the last message currently in the stream, or `0` to read from the start" ([XGROUP CREATE](https://redis.io/docs/latest/commands/xgroup-create/)). A new group at `0` replays all history. | Create new groups at `$`, unless replay is the goal. |
| XADD has no MAXLEN | The stream grows until Redis runs out of memory. | `MAXLEN ~` sized to a few days of events. |

The daemon threads are a smaller risk. Python's docs say daemon threads "are abruptly stopped at shutdown" ([threading](https://docs.python.org/3/library/threading.html#thread-objects)). A deploy can kill a handler mid-event. That's survivable only because the entry stays pending, and only if something reclaims it.

## The script

`code/voice-prod/consumer_group.py` models a stream in plain Python, then adds the three fixes: reclaim, dead-letter, and an idempotency check. The `done` set stands in for a database table that both groups share.

```python
def handle(event):
    if event["id"] in done:                           # idempotency key: safe to see twice
        return "skipped (already done)"
    if event.get("bad"):
        raise ValueError("bad payload")
    done.add(event["id"])
    return "sent customer webhook"
```

```text
new group from '$' reads only new messages:
  msg 4 call.ended   -> sent customer webhook
  msg 5 call.started -> sent customer webhook
a new group from '0' would replay 5 old messages
group from '0', one bad message:
  msg 1 call.started -> sent customer webhook
  msg 2 call.ended   -> skipped (already done)
  msg 3 call.ended   -> FAILED: bad payload (stays pending)
  msg 4 call.ended   -> skipped (already done)
  msg 5 call.started -> skipped (already done)
  msg 3 call.ended   -> FAILED: bad payload (stays pending)
  msg 3 call.ended   -> FAILED: bad payload (stays pending)
pending: []  dead-letter: [3]
```

Message 4 is a duplicate delivery of event `evt-1`. The first group sent it once. The second group, reading from `0`, skips it because the event id is already in `done`. Without that check the customer would get the webhook twice. Message 3 fails three times, then moves to the dead-letter list.

:::try
Change `MAX_TRIES` from 3 to 5. The script still calls `reclaim()` three times. Predict how many `FAILED` lines you'll see and what the last line prints.
:::

:::note What we did not test
The script models streams in Python. It doesn't talk to Redis. We read the platform's consumer code and its note about the `TimeoutError`. We did not reproduce that error ourselves or confirm its root cause.
:::

## The rule

Assume every event arrives at least once, maybe twice. Make handlers idempotent by event id. Reclaim stuck entries, give up after a few tries into a dead-letter queue, cap the stream with MAXLEN, and create new groups at `$`.

:::say
A stream keeps your event until someone acks it, which means it can deliver the same event twice, so your handler has to notice.
:::

:::check Why do handlers need to be idempotent even though a consumer group gives each entry to one consumer?
A consumer can finish the work and crash before XACK. The entry stays pending and is delivered again, by XAUTOCLAIM or by a restart.
:::

:::check You add an analytics service with a new group created at `0`. What happens on its first start?
It reads every entry still in the stream, from the oldest. With no MAXLEN that can be the full history, so it processes months of old calls as if they were new.
:::

Next: [Timeouts, retries, and saying goodbye](lesson:voice-prod/timeouts-retries-and-goodbyes)
