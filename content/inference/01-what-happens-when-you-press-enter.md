---
title: What happens when you press enter
summary: Prefill, decode, the KV cache and batching. The four ideas behind every model server.
time: 20 min
---

You send a prompt. A server with a GPU answers. What is it doing for those seconds? Two phases.

## Prefill, then decode

1. **Prefill.** The server reads your whole prompt at once. This is one large, parallel job and keeps the GPU busy.
2. **Decode.** The server writes the answer one token at a time. Each token needs the model's weights to move through memory again. This phase is **memory-bound**: its speed depends on how fast data moves, more than on raw math speed.

That is why the first word takes a while, and the rest come at a steady pace ([NVIDIA's inference guide](https://developer.nvidia.com/blog/mastering-llm-techniques-inference-optimization/)).

<figure>
<svg viewBox="0 0 620 214" role="img" aria-labelledby="t-pd d-pd">
  <title id="t-pd">Prefill and decode on a timeline</title>
  <desc id="d-pd">One wide block labelled prefill reads the whole prompt at once. After it, five narrow blocks each write one token, one after the other.</desc>
  <defs><marker id="ah-pd" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="10" y="24" font-size="13" text-anchor="start" class="small">Time goes left to right</text>
  <rect class="box hot" x="10" y="50" width="230" height="64" rx="8"/><text x="125.0" y="79.0" font-size="16" text-anchor="middle" font-weight="700">Prefill</text><text x="125.0" y="98.0" font-size="14" class="small" text-anchor="middle">whole prompt in one pass</text>
  <rect class="box" x="252" y="50" width="62" height="64" rx="8"/><text x="283.0" y="79.0" font-size="14" text-anchor="middle">tok 1</text><text x="283.0" y="96.0" font-size="12" class="small" text-anchor="middle">decode</text>
  <rect class="box" x="320" y="50" width="62" height="64" rx="8"/><text x="351.0" y="79.0" font-size="14" text-anchor="middle">tok 2</text><text x="351.0" y="96.0" font-size="12" class="small" text-anchor="middle">decode</text>
  <rect class="box" x="388" y="50" width="62" height="64" rx="8"/><text x="419.0" y="79.0" font-size="14" text-anchor="middle">tok 3</text><text x="419.0" y="96.0" font-size="12" class="small" text-anchor="middle">decode</text>
  <rect class="box" x="456" y="50" width="62" height="64" rx="8"/><text x="487.0" y="79.0" font-size="14" text-anchor="middle">tok 4</text><text x="487.0" y="96.0" font-size="12" class="small" text-anchor="middle">decode</text>
  <rect class="box" x="524" y="50" width="62" height="64" rx="8"/><text x="555.0" y="79.0" font-size="14" text-anchor="middle">tok 5</text><text x="555.0" y="96.0" font-size="12" class="small" text-anchor="middle">decode</text>
  <text x="10" y="140" font-size="13" text-anchor="start" class="small">The first token appears when prefill ends.</text>
  <text x="10" y="176" font-size="14" text-anchor="start">Prefill: many tokens at once. The GPU does a lot of math.</text>
  <text x="10" y="200" font-size="14" text-anchor="start">Decode: one token per pass. Each pass re-reads the weights from memory.</text>
</svg>
<figcaption>Prefill is one big step. Decode is many small steps, one token each.</figcaption>
</figure>

## The KV cache

To write token 500, the model looks back at tokens 1 to 499. Recomputing them each time would be wasteful, so the server keeps a **key** and a **value** for every earlier token, for every layer. This store is the **KV cache**. It grows with the length of the text and with the number of requests served together.

<figure>
<svg viewBox="0 0 620 262" role="img" aria-labelledby="t-kv d-kv">
  <title id="t-kv">The KV cache grows by one entry per token</title>
  <desc id="d-kv">Four rows. After prefill the cache holds three token entries. After each of the next three decode steps one more entry is added, ending at six.</desc>
  <defs><marker id="ah-kv" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="8" y="38" font-size="14" text-anchor="start">After prefill</text>
  <rect class="box" x="140" y="14" width="46" height="34" rx="6"/><text x="163.0" y="35.9" font-size="14" text-anchor="middle">T1</text>
  <rect class="box" x="192" y="14" width="46" height="34" rx="6"/><text x="215.0" y="35.9" font-size="14" text-anchor="middle">T2</text>
  <rect class="box" x="244" y="14" width="46" height="34" rx="6"/><text x="267.0" y="35.9" font-size="14" text-anchor="middle">T3</text>
  <text x="464" y="37" font-size="13" text-anchor="start" class="small">3 entries</text>
  <text x="8" y="88" font-size="14" text-anchor="start">After token 1</text>
  <rect class="box" x="140" y="64" width="46" height="34" rx="6"/><text x="163.0" y="85.9" font-size="14" text-anchor="middle">T1</text>
  <rect class="box" x="192" y="64" width="46" height="34" rx="6"/><text x="215.0" y="85.9" font-size="14" text-anchor="middle">T2</text>
  <rect class="box" x="244" y="64" width="46" height="34" rx="6"/><text x="267.0" y="85.9" font-size="14" text-anchor="middle">T3</text>
  <rect class="box hot" x="296" y="64" width="46" height="34" rx="6"/><text x="319.0" y="85.9" font-size="14" text-anchor="middle">T4</text>
  <text x="464" y="87" font-size="13" text-anchor="start" class="small">4 entries</text>
  <text x="8" y="138" font-size="14" text-anchor="start">After token 2</text>
  <rect class="box" x="140" y="114" width="46" height="34" rx="6"/><text x="163.0" y="135.9" font-size="14" text-anchor="middle">T1</text>
  <rect class="box" x="192" y="114" width="46" height="34" rx="6"/><text x="215.0" y="135.9" font-size="14" text-anchor="middle">T2</text>
  <rect class="box" x="244" y="114" width="46" height="34" rx="6"/><text x="267.0" y="135.9" font-size="14" text-anchor="middle">T3</text>
  <rect class="box" x="296" y="114" width="46" height="34" rx="6"/><text x="319.0" y="135.9" font-size="14" text-anchor="middle">T4</text>
  <rect class="box hot" x="348" y="114" width="46" height="34" rx="6"/><text x="371.0" y="135.9" font-size="14" text-anchor="middle">T5</text>
  <text x="464" y="137" font-size="13" text-anchor="start" class="small">5 entries</text>
  <text x="8" y="188" font-size="14" text-anchor="start">After token 3</text>
  <rect class="box" x="140" y="164" width="46" height="34" rx="6"/><text x="163.0" y="185.9" font-size="14" text-anchor="middle">T1</text>
  <rect class="box" x="192" y="164" width="46" height="34" rx="6"/><text x="215.0" y="185.9" font-size="14" text-anchor="middle">T2</text>
  <rect class="box" x="244" y="164" width="46" height="34" rx="6"/><text x="267.0" y="185.9" font-size="14" text-anchor="middle">T3</text>
  <rect class="box" x="296" y="164" width="46" height="34" rx="6"/><text x="319.0" y="185.9" font-size="14" text-anchor="middle">T4</text>
  <rect class="box" x="348" y="164" width="46" height="34" rx="6"/><text x="371.0" y="185.9" font-size="14" text-anchor="middle">T5</text>
  <rect class="box hot" x="400" y="164" width="46" height="34" rx="6"/><text x="423.0" y="185.9" font-size="14" text-anchor="middle">T6</text>
  <text x="464" y="187" font-size="13" text-anchor="start" class="small">6 entries</text>
  <text x="8" y="228" font-size="13" text-anchor="start" class="small">T = one token. Each cell holds that token&#x27;s key and value for every layer.</text>
  <text x="8" y="248" font-size="13" text-anchor="start" class="small">Highlighted cell: the one added by the latest decode step. Old cells are never recomputed.</text>
</svg>
<figcaption>The cache starts with one entry per prompt token and gains one entry for every token written.</figcaption>
</figure>

Run `code/inference/kv_cache.py`:

```text
1 request,  4096 tokens: 2.0 GiB
16 requests, 4096 tokens: 32.0 GiB
```

The formula is in the file: 2 (key and value) × layers × heads × head size × bytes per number × tokens × requests. For a Llama 2 7B shape in 16-bit numbers, one 4,096-token request needs about 2 GiB. NVIDIA's guide gives about 2 GB for the same case, and the script checks that match. The weights alone are about 14 GB.

Sixteen requests at once need 32 GiB for the cache. Memory runs out long before math does. That is the problem serving software exists to solve.

## Batching

Serving many requests together lets one load of the weights serve all of them. **In-flight batching** (also called continuous batching) lets a finished request leave and a new one join without waiting for the whole batch. The [next lesson](lesson:inference/batching-and-gpu-memory) shows both kinds side by side.

| Word | One line |
|---|---|
| Prefill | Read the prompt, all at once |
| Decode | Write tokens, one at a time |
| KV cache | Saved keys and values of earlier tokens |
| Batching | Serve many requests in one pass |

:::check Why does a long prompt use more GPU memory even before the model answers?
The KV cache stores keys and values for every prompt token, and it grows with the prompt length.
:::
