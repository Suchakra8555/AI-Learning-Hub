---
title: Measuring latency on real calls
summary: The average says your agent replies in under a second. Some callers wait three. How the platform records each turn as an event, why it reports percentiles, and what it still cannot see.
time: 20 min
---

Your dashboard says the agent answers in 950 ms on average. A customer sends you a recording where the caller says "hello?" twice because the agent went quiet for three seconds. Both are true. The average hid the bad turn.

[Where the milliseconds go](lesson:voice/where-the-milliseconds-go) split one turn into stages on paper. This lesson is about measuring those stages on live phone calls and reporting them in a way that shows the turns callers complain about.

## One turn, as spans

A **turn** here is one reply: from the moment the caller stops talking to the moment the first audio of the agent's answer goes out.

<figure>
<svg viewBox="0 0 920 230" role="img" aria-labelledby="t-turn d-turn">
  <title id="t-turn">One agent turn as stacked spans</title>
  <desc id="d-turn">A horizontal bar from the caller going quiet to the caller hearing audio. In order: end-of-turn wait, STT final transcript, LLM first sentence, TTS first byte, and the network and phone leg. A bracket marks the first four as the server-side e2e latency the platform measures. The phone leg is outside it.</desc>
  <defs><marker id="ah-turn" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <path class="arrow" d="M20 40 H770"/>
  <path class="arrow" d="M20 32 V48"/><path class="arrow" d="M770 32 V48"/>
  <text x="395" y="26" font-size="13" class="small" text-anchor="middle">e2e latency: measured on the server</text>
  <path class="arrow" d="M776 40 H900"/>
  <text x="838" y="26" font-size="13" class="small" text-anchor="middle">not measured</text>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="20" y="60" width="290" height="60" rx="8"/><text x="165" y="95">End-of-turn wait</text>
    <rect class="box" x="310" y="60" width="90" height="60" rx="8"/><text x="355" y="95">STT final</text>
    <rect class="box hot" x="400" y="60" width="240" height="60" rx="8"/><text x="520" y="95">LLM first sentence</text>
    <rect class="box" x="640" y="60" width="130" height="60" rx="8"/><text x="705" y="95">TTS first byte</text>
    <rect class="box" x="776" y="60" width="124" height="60" rx="8"/><text x="838" y="95">Network</text>
  </g>
  <path class="arrow" d="M20 150 H896" marker-end="url(#ah-turn)"/>
  <text x="20" y="175" font-size="13" class="small">Caller stops talking</text>
  <text x="900" y="175" font-size="13" class="small" text-anchor="end">Caller hears audio</text>
  <text x="460" y="210" font-size="13" class="small" text-anchor="middle">Widths are illustrative. STT final overlaps the end-of-turn wait in streaming setups.</text>
</svg>
<figcaption>One turn. The stages run mostly in sequence, so the slowest one sets the floor. The phone leg from the media server to the handset is not in any number the platform records.</figcaption>
</figure>

## Time to first sentence, not time to first token

**TTFT** (time to first token) is how long the LLM takes to send back its first piece of text. It is the number most LLM dashboards show. On a voice call it leaves out a wait the caller can hear.

The platform's notes say streaming TTS plugins buffer text until they have a whole sentence, so the voice sounds natural. If the model starts with "Sure, so the thing about your order is that", TTS cannot start until the period. The time from the first token to the first complete sentence is hidden between "LLM first token" and "TTS first byte". Call it **TTFS**, time to first sentence.

The platform measures it with a small timer wrapped around the LLM's text stream. It starts the clock on the first chunk of text and stops it at the first sentence boundary: sentence-ending punctuation followed by whitespace, at least about 20 characters in. That is a rough copy of the plugins' sentence rules, not the real tokenizer, and the code says so.

## Metrics as events

There is no metrics backend. Instead, after each agent reply the worker publishes one `metric.recorded` event onto the same Redis Stream that carries call events. A fresh sketch of the payload:

```python
{"metric_name": "turn_latency", "turn_tier": "streaming", "llm_requests": 2,
 "e2e_latency_ms": 912.0, "llm_node_ttft_latency_ms": 280.0,
 "llm_ttfs_latency_ms": 140.0, "tts_node_ttfb_latency_ms": 170.0}
```

The `e2e`, LLM first-token and TTS first-byte numbers come from the turn's own metrics in livekit-agents. The TTFS number is the platform's. `turn_tier` records which end-of-turn strategy the call used (see [tuning turns as pure functions](lesson:voice-prod/tuning-turns-as-pure-functions)), so you never average a VAD-only call with a native end-of-turn call. `llm_requests` above 1 means **preemptive generation** started drafting a reply before the turn was final, and the final transcript threw that draft away. Each extra request is money spent on nothing.

A script reads these events back for a list of call ids and prints n, p50, p95 and mean per stage, per tier. It can save a run and print the change against it, so you can compare before and after a config change.

## Why percentiles

A **percentile** says "this share of turns were at or below this value". p50 is the middle turn. p95 means 1 turn in 20 was slower. p99 is 1 in 100. A 10-minute call has dozens of turns, so a 1-in-20 bad turn happens on most calls.

`code/voice-prod/latency_report.py` makes 400 fake turns. Most are fine. About 6% get a slow LLM response that adds 1.5 to 3 s. It reports with [`statistics.quantiles`](https://docs.python.org/3/library/statistics.html#statistics.quantiles):

```python
def pct(xs, p):
    return statistics.quantiles(xs, n=100)[p - 1]
```

```text
stage          mean    p50    p95    p99
eot_ms          348    345    481    497
llm_ttfs_ms     449    329    880   3068
tts_ttfb_ms     152    150    211    219
total_ms        949    855   1422   3547

turns over 1.5 s: 17/400; LLM was the biggest stage in 17 of them
```

The mean total is 949 ms, which looks fine. The p99 is 3.5 s. Look at the LLM row: the mean (449) sits well above the p50 (329) because a few huge values drag it up. That gap between mean and median is the quickest sign of a long tail. And all 17 slow turns had the LLM as their biggest stage, which tells you where to look first.

## Dropping noisy metrics

livekit-agents also emits VAD metrics. On the platform they fired about once a second for the whole call, mostly with empty fields. Publishing them would have filled the stream with noise and drowned out the one event per turn that matters. The worker drops them before publishing. Be choosy about what you send. A metric nobody reads still costs stream space and consumer time.

## What tracing would add

The events give you numbers per turn but no picture. **Tracing** records one request as a tree of timed **spans**, one per stage ([OpenTelemetry: traces](https://opentelemetry.io/docs/concepts/signals/traces/)). For voice, one trace per turn with a span for each box in the figure would let you open a single slow turn and see exactly which stage stalled, with the call id, provider, and model attached. [Tracing, dashboards, and alerts](lesson:deploy/tracing-and-dashboards) shows the setup for LLM apps. The platform has neither tracing nor dashboards. Its logs are structured JSON and its metrics are stream events read by a script.

:::tip Built into livekit-agents
Both pieces now ship with the SDK. `set_tracer_provider` exports the agent's spans to any OpenTelemetry backend ([OpenTelemetry traces](https://docs.livekit.io/testing/observability/tracing)). Each reply's `ChatMessage.metrics` carries its per-turn latency, and 1.8 deprecates the session-level `metrics_collected` event in its favor ([data hooks](https://docs.livekit.io/testing/observability/data)). [Testing and observability](lesson:livekit/testing-and-observability) sets both up on a self-hosted lab.
:::

:::warn Gotcha from the platform
Cost tracking was written and never switched on. The code that turns usage into money has 36 tests, and the pricing route has 6 more. No call path ever calls it. Its rate cards are marked "illustrative" and unverified. So the platform can tell you a turn took 3 s, but it cannot tell you what the call cost.
:::

:::try
In `latency_report.py`, change the slow-response chance from `0.06` to `0.20`. Before you run it, predict: does the p50 of `llm_ttfs_ms` move much? Does the p95? Then set it to `0.0` and see how close mean and p50 get.
:::

:::note What we did not test
We read the turn-latency module, the worker's metric handling, and the report script. We did not place real calls or run the report on real events. The numbers above come from generated data. The 20-character sentence rule is the platform's approximation. We did not compare it to each TTS plugin's tokenizer.
:::

:::say
Measure the sentence, not the token, record every turn as an event, and report p95 and p99, because callers remember the slow turns.
:::

:::check Why does the platform measure time to first sentence on top of TTFT?
Streaming TTS waits for a full sentence before it speaks. A fast first token followed by a long first sentence still leaves the caller in silence, and TTFT alone never shows that wait.
:::

:::check The mean is 949 ms and the p50 is 855 ms. What does that gap tell you?
A few very slow turns pull the mean up. The distribution has a long tail, so look at p95 and p99, and find which stage the slow turns share.
:::
