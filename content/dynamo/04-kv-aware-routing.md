---
title: KV-aware routing
summary: Score each worker by how much of the prompt it has already cached, minus how busy it is, and send the request to the best one. Plus a script that compares three policies.
time: 20 min
---

You run three workers behind a round-robin balancer. A chat user sends their fifth message. It repeats the system prompt and the first four turns, and only the last line is new. Worker 2 has all of that cached. The balancer sends the request to worker 3, which computes it all again.

That is the problem **KV-aware routing** solves. The router knows what each worker has cached, and it prefers the worker that can skip the most prefill. The [vLLM](lesson:inference/vllm-in-depth) and [SGLang](lesson:inference/sglang-in-depth) lessons covered prefix caching inside one engine. This is the same idea across a fleet.

We read the Dynamo [KV-aware routing page](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/developer-guide/knowledge-base/concepts/system-architecture/kv-aware-routing.md), [routing concepts](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/developer-guide/knowledge-base/modular-components/router/routing-concepts.md) and [router design](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/developer-guide/knowledge-base/modular-components/router/router-design.md) on 2026-11-12. We did not run Dynamo.

## How the router knows what is cached

Workers report. When a worker adds or drops KV blocks, it publishes an event. The [event guide](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/developer-guide/advanced-customizations/writing-custom-backends/publish-kv-events.md) lists three: `BlockStored`, `BlockRemoved` and `AllBlocksCleared`. The router keeps a prefix tree of all blocks reported by all workers (the docs call it the KVIndexer), so it can ask "how many blocks at the start of this prompt does each worker hold?" That number is the **overlap**.

Events travel on the event plane. ZMQ is the default and NATS is the alternative. If your setup cannot publish events, the docs name two fallbacks: pass `--no-router-kv-events` and the router predicts cache state from its own routing choices, or accept that `kv` mode then scores by load only.

## Cache and load together

Always picking the most cached worker would pile everyone onto one machine. So the router scores load too. From the docs, with their defaults:

```text
cost = prefill_load_scale * (uncached prompt blocks) + blocks already in flight on that worker
```

The lowest cost wins. (The full formula also credits blocks held in CPU memory or on disk, and has an optional per-request term. See [lesson 5](lesson:dynamo/kv-cache-offloading).) The docs' worked example has a request of 10 blocks:

<figure>
<svg viewBox="0 0 640 390" role="img" aria-labelledby="t-dyn-route d-dyn-route">
  <title id="t-dyn-route">The router scores three workers for one request</title>
  <desc id="d-dyn-route">A request with 10 prompt blocks goes to a router. Worker 1 has 2 blocks cached and 10 blocks in flight, so its cost is 8 plus 10, which is 18. Worker 2 has 5 cached and 5 in flight, cost 5 plus 5, which is 10, and it is chosen. Worker 3 has 8 cached but 9 in flight, cost 2 plus 9, which is 11. Lowest cost wins.</desc>
  <defs><marker id="ah-dyn-route" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="10" y="20" font-size="13" text-anchor="start" font-weight="700">Request: 10 prompt blocks</text>
  <rect class="box" x="10" y="30" width="22" height="22" rx="3"/>
  <rect class="box" x="35" y="30" width="22" height="22" rx="3"/>
  <rect class="box" x="60" y="30" width="22" height="22" rx="3"/>
  <rect class="box" x="85" y="30" width="22" height="22" rx="3"/>
  <rect class="box" x="110" y="30" width="22" height="22" rx="3"/>
  <rect class="box" x="135" y="30" width="22" height="22" rx="3"/>
  <rect class="box" x="160" y="30" width="22" height="22" rx="3"/>
  <rect class="box" x="185" y="30" width="22" height="22" rx="3"/>
  <rect class="box" x="210" y="30" width="22" height="22" rx="3"/>
  <rect class="box" x="235" y="30" width="22" height="22" rx="3"/>
  <rect class="box" x="330" y="22" width="300" height="50" rx="8"/>
  <text x="480.0" y="43.0" font-size="13" text-anchor="middle" font-weight="700">Router</text>
  <text x="480.0" y="60.0" font-size="12" text-anchor="middle" class="small">cost = uncached + in flight</text>
  <rect class="box" x="10" y="100" width="620" height="74" rx="8"/>
  <text x="24" y="124" font-size="13" text-anchor="start" font-weight="700">Worker 1</text>
  <text x="24" y="144" font-size="12" text-anchor="start" class="small">2 of 10 blocks cached</text>
  <text x="24" y="162" font-size="12" text-anchor="start" class="small">10 blocks in flight</text>
  <rect class="box hot" x="150" y="126" width="22" height="22" rx="3"/>
  <rect class="box hot" x="175" y="126" width="22" height="22" rx="3"/>
  <rect class="box" x="200" y="126" width="22" height="22" rx="3"/>
  <rect class="box" x="225" y="126" width="22" height="22" rx="3"/>
  <rect class="box" x="250" y="126" width="22" height="22" rx="3"/>
  <rect class="box" x="275" y="126" width="22" height="22" rx="3"/>
  <rect class="box" x="300" y="126" width="22" height="22" rx="3"/>
  <rect class="box" x="325" y="126" width="22" height="22" rx="3"/>
  <rect class="box" x="350" y="126" width="22" height="22" rx="3"/>
  <rect class="box" x="375" y="126" width="22" height="22" rx="3"/>
  <text x="430" y="134" font-size="14" text-anchor="start">8 + 10 = 18</text>
  <rect class="box hot" x="10" y="184" width="620" height="74" rx="8"/>
  <text x="24" y="208" font-size="13" text-anchor="start" font-weight="700">Worker 2</text>
  <text x="24" y="228" font-size="12" text-anchor="start" class="small">5 of 10 blocks cached</text>
  <text x="24" y="246" font-size="12" text-anchor="start" class="small">5 blocks in flight</text>
  <rect class="box hot" x="150" y="210" width="22" height="22" rx="3"/>
  <rect class="box hot" x="175" y="210" width="22" height="22" rx="3"/>
  <rect class="box hot" x="200" y="210" width="22" height="22" rx="3"/>
  <rect class="box hot" x="225" y="210" width="22" height="22" rx="3"/>
  <rect class="box hot" x="250" y="210" width="22" height="22" rx="3"/>
  <rect class="box" x="275" y="210" width="22" height="22" rx="3"/>
  <rect class="box" x="300" y="210" width="22" height="22" rx="3"/>
  <rect class="box" x="325" y="210" width="22" height="22" rx="3"/>
  <rect class="box" x="350" y="210" width="22" height="22" rx="3"/>
  <rect class="box" x="375" y="210" width="22" height="22" rx="3"/>
  <text x="430" y="218" font-size="14" text-anchor="start" font-weight="700">5 + 5 = 10</text>
  <text x="430" y="240" font-size="12" text-anchor="start" class="small">lowest cost, chosen</text>
  <rect class="box" x="10" y="268" width="620" height="74" rx="8"/>
  <text x="24" y="292" font-size="13" text-anchor="start" font-weight="700">Worker 3</text>
  <text x="24" y="312" font-size="12" text-anchor="start" class="small">8 of 10 blocks cached</text>
  <text x="24" y="330" font-size="12" text-anchor="start" class="small">9 blocks in flight</text>
  <rect class="box hot" x="150" y="294" width="22" height="22" rx="3"/>
  <rect class="box hot" x="175" y="294" width="22" height="22" rx="3"/>
  <rect class="box hot" x="200" y="294" width="22" height="22" rx="3"/>
  <rect class="box hot" x="225" y="294" width="22" height="22" rx="3"/>
  <rect class="box hot" x="250" y="294" width="22" height="22" rx="3"/>
  <rect class="box hot" x="275" y="294" width="22" height="22" rx="3"/>
  <rect class="box hot" x="300" y="294" width="22" height="22" rx="3"/>
  <rect class="box hot" x="325" y="294" width="22" height="22" rx="3"/>
  <rect class="box" x="350" y="294" width="22" height="22" rx="3"/>
  <rect class="box" x="375" y="294" width="22" height="22" rx="3"/>
  <text x="430" y="302" font-size="14" text-anchor="start">2 + 9 = 11</text>
  <path class="arrow" d="M480 72 V96" marker-end="url(#ah-dyn-route)"/>
  <text x="10" y="372" font-size="12" text-anchor="start" class="small">Filled squares are cached. Cost = blocks still to compute + blocks in flight.</text>
</svg>
<figcaption>The example numbers come from Dynamo's router design page. Worker 3 caches the most, but it is busy, so worker 2 wins.</figcaption>
</figure>

Worker 3 holds the most, 8 of 10 blocks. It still loses, because it is already busy with 9 blocks. A cache-hot worker can lose to a colder, quieter one. That is the design: "a placement decision, not an unconditional affinity rule."

To turn it on you start the frontend with `--router-mode kv`. The docs suggest comparing against `--router-mode random` or `round-robin` on your own workload. Setting `router_temperature` above zero adds some randomness to the pick.

## Try it: three policies

`code/dynamo/kv_router.py` is our toy, not Dynamo's code. It has 3 workers with a small LRU cache each, and 200 requests from 4 families of chats. Each request is one turn of a chat, repeating the shared system prompt and the chat so far. It compares round-robin, picking the longest overlap only, and overlap minus load. The last is the same choice as the lowest cost above, because every worker faces the same prompt length.

```text
200 requests, 3 workers, 4 chat families, cache 220 blocks each
peak in flight = most blocks being worked on at once by the busiest worker
policy          cache hit  recomputed tokens peak in flight  requests per worker
round-robin           29%            184,608           1266  [67, 67, 66]
overlap only          32%            173,568           3276  [200, 0, 0]
overlap - load        43%            152,160           1230  [71, 67, 62]
```

- **Round-robin** spreads the load evenly and hits the cache 29% of the time, by luck of where each chat's earlier turns went.
- **Overlap only** sends all 200 requests to worker 0. The first request goes there by our tie-break, and from then on that worker always has the most cached. Its peak in-flight work is more than twice that of the other policies. This extreme is partly an artifact of the toy, but it is the failure the load term exists to prevent. Its hit rate is also capped by one worker's small cache.
- **Overlap minus load** reaches 43% hits and 152,160 recomputed tokens against 184,608 for round-robin, with the busiest worker no busier than round-robin's.

The toy is a handful of numbers we picked. Real gains depend on how much of your traffic shares prefixes. If every prompt is unique, there is nothing to match.

## Limits to know

The cache view is only as good as the events. The docs' offloading matrix notes that some engines do not report which tier holds a block. Routing also assumes the cache stays put: a worker that evicts a block tells the router only if its events work. Both are good reasons to measure hit rates, not assume them.

:::check Worker A caches 9 of your 10 prompt blocks but is swamped. Worker B caches 2 and is idle. Which does the router pick?
It depends on the numbers, because it compares cost. A swamped worker's high in-flight load can outweigh its cache advantage, as worker 3 in the example lost to worker 2.
:::

:::check How does the router learn what each worker has cached?
Workers publish KV events (blocks stored, blocks removed, cache cleared). The router builds a prefix tree from them.
:::
