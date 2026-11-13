---
title: Batching and GPU memory
summary: Why servers batch requests, why waiting for the slowest one wastes the GPU, and why memory is the real limit.
time: 20 min
---

One GPU can serve many people at once. The question is how to share it. Two choices decide most of your speed: how requests are grouped, and how the memory is handed out.

## Why batch at all

Decode reads the model's weights from memory for every token. If you serve one person, you pay that read for one token. If you serve eight people in one pass, the same read produces eight tokens. A group of requests handled together is a **batch**.

## Static batching: wait for the slowest

In **static batching** you take a group of requests, run them together, and start the next group only when every request in the first group is done.

The trouble is that answers have different lengths. A 2-token reply finishes in 2 steps. A 60-token reply needs 60. The short one's place in the batch sits empty for the rest of the time.

## Continuous batching: refill as you go

In **continuous batching**, the server decides again at every decode step. When one request finishes, its place goes to a waiting request right away. TensorRT-LLM's docs call the same idea in-flight batching, "also known as continuous batching or iteration-level batching" ([docs](https://github.com/NVIDIA/TensorRT-LLM/blob/main/docs/source/features/paged-attention-ifb-scheduler.md)).

<figure>
<svg viewBox="0 0 620 450" role="img" aria-labelledby="t-lanes d-lanes">
  <title id="t-lanes">Static versus continuous batching</title>
  <desc id="d-lanes">Two charts with four slots each. In static batching, requests E to H wait until the longest of A to D finishes at step 8, and everything ends at step 12. In continuous batching, E to H take freed slots as soon as B, C and D finish, and everything ends at step 9.</desc>
  <defs><marker id="ah-lanes" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="8" y="20" font-size="15" text-anchor="start" font-weight="700">Static batching</text>
  <text x="8" y="54" font-size="13" text-anchor="start" class="small">slot 1</text>
  <text x="8" y="92" font-size="13" text-anchor="start" class="small">slot 2</text>
  <text x="8" y="130" font-size="13" text-anchor="start" class="small">slot 3</text>
  <text x="8" y="168" font-size="13" text-anchor="start" class="small">slot 4</text>
  <rect class="box" x="70" y="34" width="333" height="30" rx="5"/><text x="236.5" y="53.55" font-size="13" text-anchor="middle">A</text>
  <rect class="box" x="70" y="72" width="123" height="30" rx="5"/><text x="131.5" y="91.55" font-size="13" text-anchor="middle">B</text>
  <rect class="box" x="70" y="110" width="207" height="30" rx="5"/><text x="173.5" y="129.55" font-size="13" text-anchor="middle">C</text>
  <rect class="box" x="70" y="148" width="81" height="30" rx="5"/><text x="110.5" y="167.55" font-size="13" text-anchor="middle">D</text>
  <rect class="box hot" x="406" y="34" width="165" height="30" rx="5"/><text x="488.5" y="53.55" font-size="13" text-anchor="middle">E</text>
  <rect class="box hot" x="406" y="72" width="165" height="30" rx="5"/><text x="488.5" y="91.55" font-size="13" text-anchor="middle">F</text>
  <rect class="box hot" x="406" y="110" width="123" height="30" rx="5"/><text x="467.5" y="129.55" font-size="13" text-anchor="middle">G</text>
  <rect class="box hot" x="406" y="148" width="81" height="30" rx="5"/><text x="446.5" y="167.55" font-size="13" text-anchor="middle">H</text>
  <path class="arrow" stroke-dasharray="3 5" d="M574 28 V186"/>
  <text x="594" y="202" font-size="13" text-anchor="end" class="small">all done at step 12</text>
  <text x="204.4" y="92" font-size="12" text-anchor="start" class="small">idle, waiting for A</text>
  <text x="8" y="250" font-size="15" text-anchor="start" font-weight="700">Continuous batching</text>
  <text x="8" y="284" font-size="13" text-anchor="start" class="small">slot 1</text>
  <text x="8" y="322" font-size="13" text-anchor="start" class="small">slot 2</text>
  <text x="8" y="360" font-size="13" text-anchor="start" class="small">slot 3</text>
  <text x="8" y="398" font-size="13" text-anchor="start" class="small">slot 4</text>
  <rect class="box" x="70" y="264" width="333" height="30" rx="5"/><text x="236.5" y="283.55" font-size="13" text-anchor="middle">A</text>
  <rect class="box" x="70" y="302" width="123" height="30" rx="5"/><text x="131.5" y="321.55" font-size="13" text-anchor="middle">B</text>
  <rect class="box" x="70" y="340" width="207" height="30" rx="5"/><text x="173.5" y="359.55" font-size="13" text-anchor="middle">C</text>
  <rect class="box" x="70" y="378" width="81" height="30" rx="5"/><text x="110.5" y="397.55" font-size="13" text-anchor="middle">D</text>
  <rect class="box hot" x="196" y="302" width="165" height="30" rx="5"/><text x="278.5" y="321.55" font-size="13" text-anchor="middle">E</text>
  <rect class="box hot" x="280" y="340" width="165" height="30" rx="5"/><text x="362.5" y="359.55" font-size="13" text-anchor="middle">F</text>
  <rect class="box hot" x="154" y="378" width="123" height="30" rx="5"/><text x="215.5" y="397.55" font-size="13" text-anchor="middle">G</text>
  <rect class="box hot" x="280" y="378" width="81" height="30" rx="5"/><text x="320.5" y="397.55" font-size="13" text-anchor="middle">H</text>
  <path class="arrow" stroke-dasharray="3 5" d="M448 258 V416"/>
  <text x="468" y="432" font-size="13" text-anchor="end" class="small">all done at step 9</text>
</svg>
<figcaption>The same eight requests. One bar is one request, and its length is how many decode steps it needs. Static waits for the slowest. Continuous refills a slot the moment it frees up.</figcaption>
</figure>

## Run it

`code/inference/batching_sim.py` is a toy. It has 4 slots and 20 fake requests that arrive one every 2 steps and ask for 4 to 60 tokens. One step is one decode step, and prefill is free. It is our own script, not a model of any real server.

```text
static      total steps 152  slot use 42.4%  avg wait  60.4  avg finish  73.3
continuous  total steps  72  slot use 89.6%  avg wait   9.3  avg finish  22.2
```

**Slot use** is the share of slot-steps that held a request. Static batching left more than half the slots empty. Continuous batching finished the same work in under half the steps. Real gains depend on your traffic, so treat the shape of this result as the lesson, not the numbers.

## Where GPU memory goes

Three things share the GPU's memory: the weights, the KV cache from [the first lesson](lesson:inference/what-happens-when-you-press-enter), and some working space. The weights are fixed. The KV cache grows with every token of every request.

Take our 7B example: the weights are about 14 GB in 16-bit numbers, and one 4,096-token request needs about 2 GB of cache. On a 24 GB card, that leaves room for only a few requests.

<figure>
<svg viewBox="0 0 590 292" role="img" aria-labelledby="t-mem d-mem">
  <title id="t-mem">Where GPU memory goes</title>
  <desc id="d-mem">A 24 GB bar split into 14 GB of weights, 8 GB of KV cache for four requests, and 2 GB free. Below it, four reserved slabs of memory, each only partly filled, with the empty part wasted.</desc>
  <defs><marker id="ah-mem" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="8" y="20" font-size="14" text-anchor="start" font-weight="700">Example: one 24 GB GPU, a 7B model in 16-bit numbers</text>
  <rect class="box" x="10" y="36" width="324.66666666666663" height="52" rx="6"/><text x="172.33333333333331" y="59.0" font-size="13" text-anchor="middle">Weights</text><text x="172.33333333333331" y="75.0" font-size="11" class="small" text-anchor="middle">14 GB</text>
  <rect class="box hot" x="336.66666666666663" y="36" width="184.66666666666666" height="52" rx="6"/><text x="428.99999999999994" y="59.0" font-size="13" text-anchor="middle">KV cache</text><text x="428.99999999999994" y="75.0" font-size="11" class="small" text-anchor="middle">8 GB, 4 requests</text>
  <rect class="box" x="523.3333333333333" y="36" width="44.666666666666664" height="52" rx="6"/><text x="545.6666666666666" y="66.55" font-size="13" text-anchor="middle">free</text>
  <text x="10" y="112" font-size="13" text-anchor="start" class="small">Weights are fixed. The KV cache grows. One more 4,096-token request needs 2 GB.</text>
  <text x="8" y="150" font-size="14" text-anchor="start" font-weight="700">Fragmentation: each request reserves room for the longest text it might reach</text>
  <rect class="box" x="10" y="166" width="132" height="44" rx="6"/>
  <rect class="box hot" x="10" y="166" width="99" height="44" rx="6"/>
  <text x="76" y="233" font-size="12" text-anchor="middle" class="small">request 1: 75% used</text>
  <rect class="box" x="150" y="166" width="132" height="44" rx="6"/>
  <rect class="box hot" x="150" y="166" width="40" height="44" rx="6"/>
  <text x="216" y="233" font-size="12" text-anchor="middle" class="small">request 2: 30% used</text>
  <rect class="box" x="290" y="166" width="132" height="44" rx="6"/>
  <rect class="box hot" x="290" y="166" width="66" height="44" rx="6"/>
  <text x="356" y="233" font-size="12" text-anchor="middle" class="small">request 3: 50% used</text>
  <rect class="box" x="430" y="166" width="132" height="44" rx="6"/>
  <rect class="box hot" x="430" y="166" width="20" height="44" rx="6"/>
  <text x="496" y="233" font-size="12" text-anchor="middle" class="small">request 4: 15% used</text>
  <text x="10" y="258" font-size="13" text-anchor="start" class="small">Highlighted: tokens that exist now. Empty: reserved but unused.</text>
  <text x="10" y="276" font-size="13" text-anchor="start" class="small">Nobody else can take the empty part.</text>
</svg>
<figcaption>Top: the fixed weights leave room for a few requests. Bottom: reserving the maximum for each request strands memory inside every slab.</figcaption>
</figure>

So the number of requests you can run at once is set by memory, not math.

## Fragmentation: reserved but empty

A server does not know how long an answer will be. The simple move is to **reserve** room for the longest text a request is allowed to reach. If most requests stop far short of that, most of the reserved memory sits empty, and no other request can use it. Scattered empty gaps like this are called **fragmentation**.

`code/inference/paged_kv.py` measures it on a toy. The pool is 24 GiB of cache at 0.5 MiB per token. Requests are cut off at 4,096 tokens, and most are much shorter. It compares reserving 4,096 tokens per request against handing out small fixed-size blocks of 16 tokens as text grows. Each request is given its final length up front, which a real server cannot know.

```text
contiguous (reserve max length)  requests  12  reserved  24.0 GiB  used   4.4 GiB  wasted  19.6 GiB (82%)
paged (16-token blocks)          requests  56  reserved  23.9 GiB  used  23.6 GiB  wasted   0.2 GiB (1%)
```

The same memory holds 12 requests one way and 56 the other. The numbers come from a made-up length mix with an average of about 780 tokens. Your mix will differ. The next lesson shows how vLLM hands out memory in blocks.

:::check Why can a server with free GPU math still refuse a new request?
Memory can run out first. Each request needs KV cache that grows with its length, and reserving the maximum for every request leaves much of it unused.
:::

:::check In static batching, why does one long answer slow down the short ones in its group?
The group only ends when its longest request ends. Short requests finish early, but their slots stay empty and new requests cannot start until the next group.
:::
