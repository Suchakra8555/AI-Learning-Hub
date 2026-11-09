---
title: Testing what you can't call
summary: You can't dial a real phone in CI. How our platform tested the parts it could, faked the parts it couldn't, and which bugs still only showed up on a real call.
time: 20 min
---

Your CI has no phone line, no carrier account, no LiveKit server, and no budget for STT, LLM and TTS calls on every push. Yet the bugs that hurt most on a voice platform happen across exactly those edges. So what do you test, and how much can tests catch before a real call does?

## The test pyramid for voice

A **test pyramid** is the idea that you want many cheap, fast tests at the bottom and a few slow, expensive ones at the top. For voice it looks like this, from the bottom up:

| Layer | What it covers | Speed | How the platform did it |
|---|---|---|---|
| Pure functions | Turn-taking rules, µ-law tables, frame chunking, latency maths | ms | pytest, no mocks needed |
| Fakes | Code that talks to Redis or HTTP | ms | A hand-written FakeRedis, `httpx.MockTransport` |
| Protocol parsers | Carrier wire messages in and out | ms | Frames in the carrier's JSON shape, parsed and asserted |
| Contract checks | Two services or a library agreeing on names and arguments | seconds | A provider parity script |
| Real calls | Everything above, plus the network, the SDK, the carrier | minutes, costs money | A person dialing in |

The rest of this lesson walks up the pyramid.

:::tip LiveKit has a test layer for agents
livekit-agents ships a pytest framework: `session.run` drives one turn in text, `expect` asserts what the agent said and which tools it called, and `mock_tools` swaps tool bodies for fakes. Console mode lets you talk to the agent in a terminal with no room ([unit tests](https://docs.livekit.io/testing/unit-tests)). [Testing and observability](lesson:livekit/testing-and-observability) runs these tests offline with a scripted fake LLM, so no key and no server are needed.
:::

## Pure modules first

A **pure function** returns the same output for the same input and touches nothing outside itself: no clock, no network, no globals. It is the cheapest thing to test. That is why the platform pulled turn-taking out into a module of pure functions (see [tuning turns as pure functions](lesson:voice-prod/tuning-turns-as-pure-functions)) and why the latency timer takes its clock as an argument.

A fresh example. Interruption sensitivity from 0 to 1 maps to how long the caller must talk before the agent stops, using the platform's formula `1.0 - 0.8 * s`:

```python
def min_interrupt_duration(sensitivity: float) -> float:
    s = min(max(sensitivity, 0.0), 1.0)
    return round(1.0 - 0.8 * s, 3)

def test_ends_of_the_dial():
    assert min_interrupt_duration(0.0) == 1.0
    assert min_interrupt_duration(1.0) == 0.2

def test_out_of_range_is_clamped():
    assert min_interrupt_duration(-3) == 1.0
    assert min_interrupt_duration(7) == 0.2

def test_more_sensitive_means_shorter():
    assert min_interrupt_duration(0.75) < min_interrupt_duration(0.25)
```

```text
...                                                                      [100%]
3 passed in 0.00s
```

No setup and no mocks, and it runs in a millisecond. Push as much logic as you can into code shaped like this.

## Fakes for what you own the interface to

A **fake** is a small working stand-in for a real dependency. A **mock** only records calls. The media bridge's tests use a hand-written FakeRedis that implements only the three commands the stream-ticket code uses: `set`, `get`, and `getdel`. It keeps real expiry times on a monotonic clock. A test can check that a ticket works once, fails the second time, and fails after its TTL, all without a Redis server.

The API gateway's tests do the same for HTTP. httpx lets you swap the network layer for a function that returns canned responses ([httpx: mock transports](https://www.python-httpx.org/advanced/transports/#mock-transports)). The gateway tests use that to check routing, that the internal-key header is stripped, that paths with an `internal` segment get a 404 without being proxied, and that an upstream timeout becomes a 504.

## Parsers with real-shaped frames

Each carrier adapter turns wire messages into events like "stream started", "caller audio", "DTMF digit", "stopped". The tests feed it JSON frames in the carrier's exact shape: a `start` with the ticket in its custom parameters, a `media` frame with 160 bytes of base64 µ-law, a `dtmf`, a `mark`, a `stop`. Then they assert the parsed result. Frames captured from a real call are better still, because docs and reality drift. Vobiz never sends `stop`, for example, and a test built only from a generic spec would expect one.

## Contract checks

A **contract check** tests that two sides agree, without running either for real. The platform's parity script checks three things. Every provider in the assistant config catalog has a builder in the agent's registry, and the other way round. Every keyword argument the registry passes to a LiveKit plugin is accepted by that plugin's installed constructor, with the plugin classes stubbed so nothing touches the network. And the catalog's turn-taking capabilities match the registry's. Plugins rename arguments between releases, and the builders are imported lazily, so without this check a rename only fails when a real caller dials in.

## The bugs only real calls found

:::warn Gotcha from the platform
Three bugs passed every test and broke on the first real calls.

1. **Consumers crash-looping.** The Redis docs say a blocking `XREADGROUP` returns nil when its BLOCK time runs out ([XREADGROUP](https://redis.io/docs/latest/commands/xreadgroup/)). With the platform's client setup, redis-py raised `TimeoutError` instead, so every event consumer crashed and restarted about every 5 s. The unit tests used fakes and never blocked on a real socket.
2. **Silent outbound calls.** livekit-agents waits for the user to speak first by default. On inbound calls the caller says "hello", so nobody noticed. On outbound calls the callee waited for the agent, the agent waited for the callee, and the silence timeout hung up. The tests checked the platform's code, not the SDK's defaults. The fix was to speak the first message explicitly.
3. **No Call row, ever.** Without the `webhook:` block in LiveKit's config file, LiveKit never told call orchestration that a room started. The agent joined, looked up the call, and exited with "no call row for room". That is server config, and no Python test reads it.

Two races are still open. The agent can start before the webhook has inserted the Call row. And the worker registers with no agent name, so LiveKit dispatches it to every room. Both depend on timing between separate processes, which unit tests do not have.
:::

Each bug lived at an edge the tests replaced with something friendlier: a fake socket, a caller who speaks first, a config file nobody loads. Four of the nine services have no tests at all, including the credential service and the webhook dispatcher.

## A first real call smoke checklist

Run this by hand after any deploy that touches media, config, or the SDK version.

- [ ] Inbound call: the agent greets you within 2 s of pickup.
- [ ] Outbound call: the agent speaks first, and the callee does not wait in silence.
- [ ] Talk over the agent: it stops within half a second, and you hear no leftover audio.
- [ ] Stay silent: the idle prompt plays, then the call ends at the silence timeout.
- [ ] Hang up: the Call row is marked ended and the `call.ended` webhook arrives.
- [ ] Check the logs: no consumer restarts, no "no call row" errors.
- [ ] Check the latency report for the call: e2e p50 is near your usual baseline.
- [ ] If recording is on, the file exists. If it is off, it does not.

:::try
Add a test to the snippet above that passes `0.5` and checks the result is `0.6`. Then change `round(..., 3)` to no rounding at all and run it again. Predict which assertions fail and why. (Hint: floating point.)
:::

:::note What we did not test
We read the media bridge tests, the gateway tests, and the parity script, and counted test files per service. We did not run the platform's test suites or its parity script. We ran only our own snippet here. The three bugs are from the platform's notes. We did not reproduce them.
:::

:::say
Test pure code exhaustively, fake what you own, check contracts against what you don't, and keep a short script for the first real call, because the edges are where voice breaks.
:::

:::check Why did the FakeRedis tests not catch the `TimeoutError` crash loop?
The fake has no socket and no blocking read. The bug came from how the real client handled a socket timeout during a blocking call, and that code path never ran in tests.
:::

:::check What does the parity script catch that unit tests of each service would miss?
A disagreement between two sides: a provider in the catalog with no builder, or a keyword argument a newer plugin no longer accepts. Each side passes its own tests. They only fail together.
:::
