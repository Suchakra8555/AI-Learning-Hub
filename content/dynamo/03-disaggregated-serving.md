---
title: Disaggregated serving
summary: Run prefill and decode on different GPUs and ship the KV cache between them. When that helps, when it hurts, and a toy model that shows both.
time: 25 min
---

A user pastes a 30-page document into a chat. On the GPU that takes the job, every other user's reply stops for a moment while the prompt is read. Nothing is broken. Prefill and decode are sharing one GPU, and prefill won.

**Disaggregated serving** means giving each phase its own GPUs. "Disaggregated" just means taken apart. The word you will also see is **aggregated** (or colocated): one worker does both. We covered the two phases in [the first engines lesson](lesson:inference/what-happens-when-you-press-enter). Prefill reads the whole prompt in one big pass. Decode then writes one token at a time.

Picture a restaurant. One kitchen can both prep ingredients and serve plates, but a huge prep job blocks the serving line. A restaurant with a prep line and a serving line avoids that. The price is that prepped food must be carried across the room.

We read Dynamo's [disaggregated serving page](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/developer-guide/knowledge-base/concepts/system-architecture/disaggregated-serving.md) and the [Kubernetes guide](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/kubernetes/disaggregated-serving/overview.md) on 2026-11-12. We did not run it.

## What Dynamo says

The docs give two reasons. The phases have different needs, so each can use different settings: their example is a larger tensor parallel size (the number of GPUs a model is split across) for memory-bound decode and a smaller one for compute-bound prefill. And long prompts stop blocking tokens that are already being generated.

A split request has three steps: the prefill worker builds the KV cache, it hands the cache to a decode worker, and the decode worker generates the tokens. The notation **xPyD** means x prefill workers and y decode workers. The docs say Dynamo supports changing x and y while running: a new worker registers and the router finds it, and a removed worker drains its requests first.

<figure>
<svg viewBox="0 0 640 330" role="img" aria-labelledby="t-dyn-disagg d-dyn-disagg">
  <title id="t-dyn-disagg">Colocated versus disaggregated GPUs</title>
  <desc id="d-dyn-disagg">Two panels. On the left, colocated: one GPU runs a long prefill block, and the decode tokens of other users wait during it, then decode continues. On the right, disaggregated: a prefill GPU runs the long prefill block, an arrow carries the KV cache to a decode GPU, and the decode GPU keeps producing tokens without a gap.</desc>
  <defs><marker id="ah-dyn-disagg" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="10" y="22" font-size="14" text-anchor="start" font-weight="700">Colocated: one GPU does both</text>
  <text x="10" y="56" font-size="12" text-anchor="start" class="small">GPU A</text>
  <rect class="box" x="56" y="40" width="40" height="30" rx="5"/>
  <text x="76.0" y="59.5" font-size="13" text-anchor="middle">d</text>
  <rect class="box" x="100" y="40" width="40" height="30" rx="5"/>
  <text x="120.0" y="59.5" font-size="13" text-anchor="middle">d</text>
  <rect class="box hot" x="144" y="40" width="120" height="30" rx="5"/>
  <text x="204.0" y="59.5" font-size="13" text-anchor="middle">long prefill</text>
  <rect class="box" x="268" y="40" width="40" height="30" rx="5"/>
  <text x="288.0" y="59.5" font-size="13" text-anchor="middle">d</text>
  <text x="10" y="100" font-size="12" text-anchor="start" class="small">Other users' tokens (d) stop while the</text>
  <text x="10" y="117" font-size="12" text-anchor="start" class="small">long prompt is read. The wait is the gap.</text>
  <path class="arrow" stroke-dasharray="5 4" d="M144 80 V86"/>
  <text x="10" y="150" font-size="14" text-anchor="start" font-weight="700">Disaggregated: two kinds of GPU</text>
  <text x="10" y="184" font-size="12" text-anchor="start" class="small">Prefill</text>
  <rect class="box hot" x="70" y="168" width="120" height="30" rx="5"/>
  <text x="130.0" y="187.5" font-size="13" text-anchor="middle">long prefill</text>
  <path class="arrow" d="M130 198 V232" marker-end="url(#ah-dyn-disagg)"/>
  <text x="140" y="222" font-size="12" text-anchor="start" class="small">KV cache</text>
  <text x="10" y="254" font-size="12" text-anchor="start" class="small">Decode</text>
  <rect class="box" x="70" y="238" width="36" height="30" rx="5"/>
  <text x="88.0" y="257.5" font-size="13" text-anchor="middle">d</text>
  <rect class="box" x="110" y="238" width="36" height="30" rx="5"/>
  <text x="128.0" y="257.5" font-size="13" text-anchor="middle">d</text>
  <rect class="box" x="150" y="238" width="36" height="30" rx="5"/>
  <text x="168.0" y="257.5" font-size="13" text-anchor="middle">d</text>
  <rect class="box" x="190" y="238" width="36" height="30" rx="5"/>
  <text x="208.0" y="257.5" font-size="13" text-anchor="middle">d</text>
  <rect class="box" x="230" y="238" width="36" height="30" rx="5"/>
  <text x="248.0" y="257.5" font-size="13" text-anchor="middle">d</text>
  <rect class="box" x="270" y="238" width="36" height="30" rx="5"/>
  <text x="288.0" y="257.5" font-size="13" text-anchor="middle">d</text>
  <text x="10" y="296" font-size="12" text-anchor="start" class="small">The decode GPU never waits. The cost: the KV cache has to travel.</text>
  <rect class="box" x="352" y="36" width="276" height="88" rx="8"/>
  <text x="490.0" y="67.5" font-size="13" text-anchor="middle" font-weight="700">Helps decode smoothness</text>
  <text x="490.0" y="84.5" font-size="12" text-anchor="middle" class="small">no long prefill in the same GPU</text>
  <text x="490.0" y="101.5" font-size="12" text-anchor="middle" class="small">each pool can be sized on its own</text>
  <rect class="box" x="352" y="160" width="276" height="126" rx="8"/>
  <text x="490.0" y="202.0" font-size="13" text-anchor="middle" font-weight="700">Costs</text>
  <text x="490.0" y="219.0" font-size="12" text-anchor="middle" class="small">a KV transfer for every request</text>
  <text x="490.0" y="236.0" font-size="12" text-anchor="middle" class="small">GPUs set aside for prefill</text>
  <text x="490.0" y="253.0" font-size="12" text-anchor="middle" class="small">two pools to keep balanced</text>
</svg>
<figcaption>Time goes left to right. Same long prompt on both sides. On the left it freezes other users' tokens. On the right the decode GPU never stops.</figcaption>
</figure>

## The hand-off

The router's PrefillRouter runs the show. The prefill worker returns `disaggregated_params`, a note with backend-specific transfer details. The router passes it to the decode worker, which pulls the blocks through **NIXL**, directly from prefill GPU memory to decode GPU memory. The docs say the transfer is non-blocking, so GPUs keep working on other requests while it runs.

How the hand-off works differs by engine. SGLang uses a bootstrap connection, and prefill can run in the background so decode starts at once. For vLLM and TensorRT-LLM the docs say prefill is synchronous and decode waits for it.

<figure>
<svg viewBox="0 0 640 330" role="img" aria-labelledby="t-dyn-kvxfer d-dyn-kvxfer">
  <title id="t-dyn-kvxfer">KV hand-off between prefill and decode workers</title>
  <desc id="d-dyn-kvxfer">Three columns: prefill worker, router, decode worker. Arrow 1: the prefill worker returns transfer metadata to the router. Arrow 2: the router sends the decode request with that metadata to the decode worker. Arrow 3: the decode worker uses the metadata to pull the KV blocks straight from the prefill GPU memory over NIXL. A bottom bar shows the transports NIXL can use: NVLink on one node, InfiniBand or RoCE across nodes, with TCP as a slow fallback.</desc>
  <defs><marker id="ah-dyn-kvxfer" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect class="box" x="10" y="10" width="170" height="44" rx="8"/>
  <text x="95.0" y="36.5" font-size="13" text-anchor="middle" font-weight="700">Prefill worker</text>
  <rect class="box" x="235" y="10" width="170" height="44" rx="8"/>
  <text x="320.0" y="36.5" font-size="13" text-anchor="middle" font-weight="700">Router</text>
  <rect class="box" x="460" y="10" width="170" height="44" rx="8"/>
  <text x="545.0" y="36.5" font-size="13" text-anchor="middle" font-weight="700">Decode worker</text>
  <path class="arrow" stroke-dasharray="5 4" d="M95 54 V200"/>
  <path class="arrow" stroke-dasharray="5 4" d="M320 54 V200"/>
  <path class="arrow" stroke-dasharray="5 4" d="M545 54 V200"/>
  <path class="arrow" d="M95 84 H316" marker-end="url(#ah-dyn-kvxfer)"/>
  <circle class="box hot" cx="205" cy="72" r="11"/>
  <text x="205" y="76.5" font-size="13" text-anchor="middle" font-weight="700">1</text>
  <text x="205" y="106" font-size="12" text-anchor="middle" class="small">transfer note</text>
  <path class="arrow" d="M320 134 H541" marker-end="url(#ah-dyn-kvxfer)"/>
  <circle class="box hot" cx="430" cy="122" r="11"/>
  <text x="430" y="126.5" font-size="13" text-anchor="middle" font-weight="700">2</text>
  <text x="430" y="156" font-size="12" text-anchor="middle" class="small">request + note</text>
  <path class="arrow" d="M541 182 H99" marker-end="url(#ah-dyn-kvxfer)"/>
  <circle class="box hot" cx="215" cy="170" r="11"/>
  <text x="215" y="174.5" font-size="13" text-anchor="middle" font-weight="700">3</text>
  <text x="320" y="200" font-size="12" text-anchor="middle" class="small">pull KV blocks over NIXL</text>
  <rect class="box hot" x="10" y="226" width="620" height="90" rx="8"/>
  <text x="320" y="248" font-size="13" text-anchor="middle" font-weight="700">NIXL picks a path from what both ends have</text>
  <rect class="box" x="26" y="262" width="180" height="38" rx="8"/>
  <text x="116.0" y="277.0" font-size="13" text-anchor="middle">NVLink</text>
  <text x="116.0" y="294.0" font-size="12" text-anchor="middle" class="small">inside one node</text>
  <rect class="box" x="230" y="262" width="180" height="38" rx="8"/>
  <text x="320.0" y="277.0" font-size="13" text-anchor="middle">InfiniBand / RoCE</text>
  <text x="320.0" y="294.0" font-size="12" text-anchor="middle" class="small">RDMA, across nodes</text>
  <rect class="box" x="434" y="262" width="180" height="38" rx="8"/>
  <text x="524.0" y="277.0" font-size="13" text-anchor="middle">TCP</text>
  <text x="524.0" y="294.0" font-size="12" text-anchor="middle" class="small">slow fallback</text>
</svg>
<figcaption>The router only passes a note. The KV blocks themselves go GPU to GPU. NIXL picks the path.</figcaption>
</figure>

NIXL's overview says it chooses among transports such as NVLink, InfiniBand, RoCE, GPUDirect RDMA, NVMe-oF and TCP based on what both ends have ([NIXL overview](https://github.com/ai-dynamo/nixl/blob/main/docs/nixl.md)). The network matters a lot. Dynamo's Kubernetes install guide says that without RDMA the KV transfer falls back to TCP, with "~98s TTFT vs ~200-500ms with RDMA" ([install guide](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/kubernetes/installation/install-dynamo.md)). That is the project's own statement, for an unnamed setup. It tells you the order of the risk: a slow link can erase the whole benefit.

## When it helps and when it hurts

The Kubernetes guide lists where splitting helps most: long prompts or retrieval-heavy traffic, long generations or high concurrency, wanting to scale prefill and decode separately, and large models that need different parallelism per phase.

It also says "It is not automatically better." For small models, short prompts, low concurrency, or clusters without a fast KV-transfer fabric, an aggregated setup is simpler and often faster. The architecture page adds that at low concurrency an aggregated worker often avoids transfer and pool-splitting overhead, and that GPUs set aside for prefill do not hold decode KV cache. It says the best boundary depends on model, GPU, engine and request lengths, and "should not be encoded as a universal token threshold". So we will not give you one.

For the in-between case the docs describe an experimental **conditional disaggregation**: the router sends a request to a decode worker for local prefill when that decode worker already holds much of the prompt ([page](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/developer-guide/advanced-customizations/conditional-disaggregation.md)). It needs KV events from the decode workers, and SGLang is not supported yet.

## A toy you can run

`code/dynamo/disagg_sim.py` is a toy timing model. **It is not a benchmark.** Every number in it is made up: 0.12 ms of prefill per prompt token, a decode step of 15 ms plus 0.5 ms per sequence in the batch, a 0.1 MB-per-token KV cache moved over a 25 GB/s link with 10 ms of setup. It has 8 GPUs and the same traffic for both setups, set so prefill takes a quarter of each GPU's time when colocated. For the split it tries every pool size and keeps the best TTFT. TTFT is time to first token, and ITL is inter-token latency, as in the [benchmark lesson](lesson:inference/benchmark-honestly).

```text
toy model, 8 GPUs, 200 output tokens per request. Times in ms. Not a benchmark.
 prompt |         colocated          |                  split                   | verdict
 tokens |    TTFT     ITL worst ITL | pools P+D    TTFT     ITL transfer |
    500 |      70    33.2        86 |    4+4        102    90.0       12 | stay colocated
   4000 |     560    75.8       496 |    7+1        602    25.7       26 | split wins on ITL only
  16000 |    2240   255.2      1935 |    7+1       2378    16.7       74 | split wins on ITL only
```

Read the rows in order.

- **500 tokens.** Splitting loses on both. At this size a prefill is only 60 ms, so it hardly disturbs decode. The split still costs a 12 ms transfer, and 4 prefill plus 4 decode GPUs leave each decode GPU with twice the batch, so inter-token latency goes from 33 to 90 ms.
- **4,000 tokens.** ITL falls from 75.8 to 25.7 ms, because the one decode GPU is never interrupted. TTFT rises a little, 560 to 602, which is the transfer plus a queue for prefill.
- **16,000 tokens.** The colocated GPU stalls decode for the whole 1.9 seconds of a prefill, so mean ITL is 255 ms and the worst case is 1,935 ms. The split holds ITL at 16.7 ms. TTFT is again slightly worse.

The shape matches what the docs say: the win is smooth decode for long prompts, the cost is the transfer and the dedicated GPUs, and short prompts get only the cost. The numbers prove nothing about Dynamo. Change the constants and the crossover moves.

:::check A team serves a small model with short chat prompts at low traffic. Should they split prefill and decode?
Probably not. The docs say aggregated is simpler and often faster for small models, short prompts and low concurrency, and the toy shows the transfer and the extra pool bookkeeping outweigh the gain.
:::

:::check What does the router hand to the decode worker, and what moves over NIXL?
The router hands over a small note of transfer details. The KV cache blocks themselves move over NIXL, GPU to GPU.
:::
