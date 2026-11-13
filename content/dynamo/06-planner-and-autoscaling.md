---
title: Planner and autoscaling
summary: The planner watches latency and load and changes how many prefill and decode workers run. Targets, the two loops, and the limits the docs list.
time: 20 min
---

Your morning traffic is long documents. Your afternoon traffic is short chat. With a fixed pool of 4 prefill and 4 decode workers, you are right for one of them at most. Add workers by hand and you are paged at night. Add too many and you pay for idle GPUs.

The **Dynamo planner** is the part that changes worker counts for you. We read the [planner overview](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/developer-guide/knowledge-base/modular-components/planner/overview.md) and [planner design](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/developer-guide/knowledge-base/modular-components/planner/planner-design.md) on 2026-11-12. We did not run it.

## Why not a normal autoscaler

The docs argue that tools like HPA, which scale on CPU or request rate, do not fit LLM serving:

- Cost depends on request content. One 32K-token prompt can cost far more than many short ones.
- Prefill and decode scale on different things. Prefill follows input length. Decode follows concurrency and KV memory.
- The numbers users care about are TTFT and ITL, not CPU use.
- Starting a GPU worker takes minutes, so the scaler must predict, not only react.

## Targets and two loops

An **SLA** here is a latency target, for example TTFT under 200 ms and ITL under 20 ms (the numbers in the README's example, not a recommendation). The planner has four optimization targets:

| Target | What it does |
|---|---|
| `throughput` (the default) | scales on queue depth and KV cache use |
| `latency` | scales earlier, to keep queues short |
| `load` | uses thresholds you set |
| `sla` | aims at TTFT and ITL values you give it |

Only the `sla` target lets you pick between two scaling methods:

- **Throughput-based**: predicts traffic (request count, input and output lengths) with a forecaster, then works out the worker counts that meet the targets. The default interval is 180 seconds. Forecasters offered are Constant, ARIMA, Kalman and Prophet. It sets a floor on worker counts.
- **Load-based**: reads per-engine metrics (the docs call them ForwardPassMetrics) and nudges counts up or down by one. The default interval is 5 seconds. It reacts to bursts above the floor.

<figure>
<svg viewBox="0 0 640 330" role="img" aria-labelledby="t-dyn-loop d-dyn-loop">
  <title id="t-dyn-loop">The planner feedback loop</title>
  <desc id="d-dyn-loop">Four boxes in a loop. Metrics: TTFT, ITL, queue depth and KV use. Planner: compares them with the targets and predicts traffic. Decision: change the number of prefill workers and decode workers. Apply: the connector or operator starts or stops workers. Then traffic runs on the new pool sizes and produces new metrics.</desc>
  <defs><marker id="ah-dyn-loop" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect class="box" x="20" y="30" width="250" height="64" rx="8"/>
  <text x="145.0" y="58.0" font-size="13" text-anchor="middle" font-weight="700">1  Measure</text>
  <text x="145.0" y="75.0" font-size="12" text-anchor="middle" class="small">TTFT, ITL, queue, KV use</text>
  <rect class="box hot" x="370" y="30" width="250" height="64" rx="8"/>
  <text x="495.0" y="58.0" font-size="13" text-anchor="middle" font-weight="700">2  Compare</text>
  <text x="495.0" y="75.0" font-size="12" text-anchor="middle" class="small">targets, and a traffic forecast</text>
  <rect class="box hot" x="370" y="220" width="250" height="64" rx="8"/>
  <text x="495.0" y="248.0" font-size="13" text-anchor="middle" font-weight="700">3  Decide</text>
  <text x="495.0" y="265.0" font-size="12" text-anchor="middle" class="small">change prefill and decode counts</text>
  <rect class="box" x="20" y="220" width="250" height="64" rx="8"/>
  <text x="145.0" y="248.0" font-size="13" text-anchor="middle" font-weight="700">4  Apply</text>
  <text x="145.0" y="265.0" font-size="12" text-anchor="middle" class="small">operator starts or stops workers</text>
  <path class="arrow" d="M270 62 H366" marker-end="url(#ah-dyn-loop)"/>
  <path class="arrow" d="M495 94 V216" marker-end="url(#ah-dyn-loop)"/>
  <path class="arrow" d="M370 252 H274" marker-end="url(#ah-dyn-loop)"/>
  <path class="arrow" d="M145 220 V98" marker-end="url(#ah-dyn-loop)"/>
  <text x="320" y="154" font-size="12" text-anchor="middle" class="small">new pool sizes change the next measurements</text>
  <text x="320" y="314" font-size="12" text-anchor="middle" class="small">Fast loop: seconds. Slow, predictive loop: minutes. Both can run together.</text>
</svg>
<figcaption>One loop, run again and again. The docs describe a fast version and a slower, predictive version of it.</figcaption>
</figure>

The loop is the same in both: measure, compare, decide, apply. What changes is how often and how far ahead it looks. On Kubernetes the planner patches the replica counts of the deployment resource, and the operator makes the pods match. Note that the planner changes how many workers of each kind exist. The docs describe it setting counts per role. We found nothing about moving a running worker from one pool to the other, so expect old workers to stop and new ones to start.

## Safe ways to start

The docs suggest starting with the default `throughput` target because it needs no configuration. The `sla` target can run in `advisory` mode, which calculates and logs what it would do without changing anything. Set replica floors and a `max_gpu_budget` before you turn advice off.

## Limits the docs list

- Scale-down is abrupt. A removed worker is stopped without waiting for in-flight requests, so a request in prefill on it fails, and in a split setup a decode worker waiting on its KV transfer can also be hurt. The docs' workaround is to set minimum endpoint counts.
- Load-based scaling needs per-engine metrics, and support differs by backend and version. For TensorRT-LLM, decode scaling also needs the worker to report its KV capacity.
- Workers take minutes to start, so the planner can only fix problems slowly.

The README quotes "80% fewer SLA breaches" at 5% lower cost from a conference talk. That is a claim about someone else's workload.

:::check Why does the planner use TTFT and ITL targets and not CPU use?
Those are what users feel, and the docs say CPU or request rate does not map to them, because cost depends on prompt length and phase.
:::

:::check The planner scales a prefill worker down while it is mid-request. What happens?
Per the docs, the worker is stopped without waiting, so that request fails. Setting minimum endpoint counts protects capacity.
:::
