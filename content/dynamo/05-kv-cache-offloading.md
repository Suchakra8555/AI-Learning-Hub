---
title: KV cache offloading
summary: What happens when the KV cache outgrows GPU memory. The memory tiers, who manages them, what the docs say about their status, and why reuse beats recompute.
time: 20 min
---

The KV cache from [the first lesson](lesson:inference/what-happens-when-you-press-enter) grows with every token of every chat. A 4,096-token request on a 7B model took 2.0 GiB in our own `kv_cache.py` numbers. Sixteen such requests take 32 GiB. When the GPU is full, the server throws old blocks away. A user comes back after a coffee, and their whole prompt is read again from scratch.

**KV cache offloading** moves those blocks to bigger, slower memory instead of throwing them away. A hit there costs a copy. A miss costs a full prefill.

We read the Dynamo [KVBM configuration page](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/reference/components/kvbm-configuration.mdx), the [offloading support matrix](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/developer-guide/knowledge-base/modular-components/router/offloading-support-matrix.md), the [Kubernetes offloading guide](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/kubernetes/kv-cache-offloading/overview.mdx) and the [deprecations list](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/reference/general/releases/deprecations.mdx) on 2026-11-12. We did not run any of it.

## The tiers

Dynamo's KV block manager docs name four tiers ([engine notes](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/lib/kvbm-engine/docs/architecture.md)):

<figure>
<svg viewBox="0 0 640 360" role="img" aria-labelledby="t-dyn-tiers d-dyn-tiers">
  <title id="t-dyn-tiers">KV cache memory tiers</title>
  <desc id="d-dyn-tiers">Four steps going down, each wider than the last. G1 GPU memory is smallest and about nanoseconds away. G2 pinned CPU memory is medium and about microseconds. G3 local SSD is large and about milliseconds. G4 object storage is the largest and about 100 milliseconds. Blocks move down when evicted from a faster tier and come back up when a request needs them.</desc>
  <defs><marker id="ah-dyn-tiers" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect class="box hot" x="10" y="20" width="200" height="56" rx="8"/>
  <text x="110.0" y="44.0" font-size="13" text-anchor="middle" font-weight="700">G1  GPU memory</text>
  <text x="110.0" y="61.0" font-size="12" text-anchor="middle" class="small">smallest</text>
  <text x="224" y="53" font-size="13" text-anchor="start">about ns</text>
  <rect class="box" x="10" y="92" width="270" height="56" rx="8"/>
  <text x="145.0" y="116.0" font-size="13" text-anchor="middle" font-weight="700">G2  CPU memory (pinned)</text>
  <text x="145.0" y="133.0" font-size="12" text-anchor="middle" class="small">medium</text>
  <text x="294" y="125" font-size="13" text-anchor="start">about us</text>
  <rect class="box" x="10" y="164" width="340" height="56" rx="8"/>
  <text x="180.0" y="188.0" font-size="13" text-anchor="middle" font-weight="700">G3  local SSD</text>
  <text x="180.0" y="205.0" font-size="12" text-anchor="middle" class="small">large</text>
  <text x="364" y="197" font-size="13" text-anchor="start">about ms</text>
  <rect class="box" x="10" y="236" width="410" height="56" rx="8"/>
  <text x="215.0" y="260.0" font-size="13" text-anchor="middle" font-weight="700">G4  object storage (S3-style)</text>
  <text x="215.0" y="277.0" font-size="12" text-anchor="middle" class="small">largest</text>
  <text x="434" y="269" font-size="13" text-anchor="start">about 100 ms</text>
  <path class="arrow" d="M560 40 V300" marker-end="url(#ah-dyn-tiers)"/>
  <text x="572" y="150" font-size="12" text-anchor="start" class="small">evict down</text>
  <text x="572" y="168" font-size="12" text-anchor="start" class="small">when full</text>
  <path class="arrow" d="M610 300 V40" marker-end="url(#ah-dyn-tiers)"/>
  <text x="10" y="322" font-size="12" text-anchor="start" class="small">Hit in a lower tier: copy the block up, skip the prefill for it.</text>
  <text x="10" y="342" font-size="12" text-anchor="start" class="small">Miss everywhere: compute it again.</text>
</svg>
<figcaption>Faster tiers are smaller. The latency labels are the rough orders of magnitude in the Dynamo KVBM engine notes, not measurements we made.</figcaption>
</figure>

The time labels are the notes' own rough orders of magnitude, from a developer page, not measurements. Capacity rises as speed falls. That is why you keep the hottest blocks on the GPU and let the rest sink.

## What the docs say about who does it

This part needs care, because the docs do not line up.

The README says **KVBM** (KV Block Manager) offloads KV cache down the tiers from GPU to CPU to SSD to remote storage. The [configuration page](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/reference/components/kvbm-configuration.mdx) describes the same four tiers, with sizes set by `DYN_KVBM_CPU_CACHE_GB` and `DYN_KVBM_DISK_CACHE_GB`. It warns that a CPU cache smaller than the GPU cache makes KVBM churn, offloading blocks after every forward pass, and performance can get worse.

But the deprecations list says KVBM "is deprecated in v1.5.0 and removal is targeted for v1.7.0". It tells you to use the engine's own offloading instead. The main branch we read is at 1.7.0 and still has the KVBM code and docs. The same configuration page says the TensorRT-LLM KVBM connector was removed, while another page still claims "full KVBM integration" for TensorRT-LLM. We cannot tell you the final status. Check the release notes for your version before building on KVBM.

What the docs steer you to instead are engine-side connectors, and they say to pick one because the connectors "are alternatives, not layers":

| Engine | Offloading option named in the docs |
|---|---|
| vLLM | `OffloadingConnector` (native CPU), LMCache, FlexKV |
| SGLang | HiCache, with an optional shared pool through Mooncake |
| TensorRT-LLM | native host cache |

From the support matrix: CPU memory offload is the well-supported path for vLLM. Disk is marked "available but not fully validated" for vLLM. Shared pools across workers are still planned for vLLM.

## What gets evicted

When a tier is full, something has to leave. The library behind KVBM describes blocks held by running requests as protected from eviction. Blocks no request holds sit in an inactive pool, kept for reuse until room is needed. Its README example builds the pool with an LRU rule (drop the **least recently used** block first) and a TinyLFU frequency counter ([kvbm-logical README](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/lib/kvbm-logical/README.md)). That is an example in a library README. We did not confirm what a deployment uses by default. There is also a knob to set a minimum priority before a block is offloaded to host memory.

## The router sees the tiers

Offloading ties back to [routing](lesson:dynamo/kv-aware-routing). For engines that report which tier holds a block, the router gives partial credit. The matrix says the defaults are 0.75 of a GPU hit for a block in host memory and 0.25 for one on disk, set by `--router-host-cache-hit-weight` and `--router-disk-cache-hit-weight`. TensorRT-LLM reports a merged GPU plus host view, so those weights do not apply to it.

Those weights say something useful: a CPU-memory hit is worth a lot, a disk hit much less. They are defaults, not measured truths for your hardware.

## Why reuse usually beats recompute

Computing a prefix means running the model over every token of it. Copying a cached prefix means moving bytes. For a long prefix the copy is typically cheaper than the math, and it also frees the GPU for other work. That is our reasoning, not a number from the docs, and the word is "typically": a slow tier, a tiny hit, or a copy that fights for the same bus can reverse it. That is why the docs warn about churn and why they ask you to compare on your own workload. The project also points out that the engines' own offloading is the recommended route for host and disk tiers.

:::check A chat user returns after an hour and their blocks were pushed to CPU memory. Is that a miss?
No. It is a hit in a lower tier. The block is copied back up and that part of the prefill is skipped.
:::

:::check Why can a CPU cache that is smaller than the GPU cache make things worse?
The docs say KVBM then churns: it offloads blocks after every forward pass and few of them are reused, so the copying costs more than it saves.
:::
