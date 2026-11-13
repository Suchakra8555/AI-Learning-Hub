---
title: vLLM in depth
summary: How vLLM stores the KV cache in blocks, schedules requests step by step, reuses shared prompts, and exposes an OpenAI-style server.
time: 25 min
---

**vLLM** is an open-source library for running language models on your own hardware. Its README says it began in the Sky Computing Lab at UC Berkeley ([README](https://github.com/vllm-project/vllm/blob/main/README.md)).

We did not run vLLM for this lesson. We read its docs and source on 2026-11-12, and the toy scripts are ours. Where something could not be checked, the lesson says so.

## PagedAttention: pages for the KV cache

The last lesson showed that reserving the longest length per request wastes memory. vLLM's answer is **PagedAttention**. It cuts each request's KV cache into small fixed-size pieces called **blocks**, the way an operating system cuts memory into pages, or the way a notebook is made of pages that need not sit next to each other on a shelf.

A request's text is in order, but its blocks do not have to be. A **block table** records which physical block holds each piece. New blocks are handed out only when the text grows into them.

<figure>
<svg viewBox="0 0 600 262" role="img" aria-labelledby="t-blocks d-blocks">
  <title id="t-blocks">A block table maps a request&#x27;s text to scattered memory blocks</title>
  <desc id="d-blocks">A request&#x27;s tokens are cut into three logical blocks. A block table sends logical block 0 to physical block 6, block 1 to physical block 2, and block 2 to physical block 4. Physical blocks of other requests sit in between.</desc>
  <defs><marker id="ah-blocks" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="10" y="20" font-size="14" text-anchor="start" font-weight="700">Request 1: A B C D E F G H I</text>
  <text x="10" y="40" font-size="12" text-anchor="start" class="small">4 tokens per block (the vLLM docs example)</text>
  <rect class="box" x="10" y="64" width="96" height="44" rx="6"/><text x="58.0" y="83.0" font-size="14" text-anchor="middle">A B C D</text><text x="58.0" y="100.0" font-size="12" class="small" text-anchor="middle">logical 0</text>
  <rect class="box" x="10" y="120" width="96" height="44" rx="6"/><text x="58.0" y="139.0" font-size="14" text-anchor="middle">E F G H</text><text x="58.0" y="156.0" font-size="12" class="small" text-anchor="middle">logical 1</text>
  <rect class="box" x="10" y="176" width="96" height="44" rx="6"/><text x="58.0" y="195.0" font-size="14" text-anchor="middle">I</text><text x="58.0" y="212.0" font-size="12" class="small" text-anchor="middle">logical 2</text>
  <text x="200" y="56" font-size="14" text-anchor="middle" class="small">Block table</text>
  <rect class="box hot" x="150" y="64" width="100" height="44" rx="6"/><text x="200.0" y="90.9" font-size="14" text-anchor="middle">-&gt; block 6</text>
  <path class="arrow" d="M106 86 H150"/>
  <rect class="box hot" x="150" y="120" width="100" height="44" rx="6"/><text x="200.0" y="146.9" font-size="14" text-anchor="middle">-&gt; block 2</text>
  <path class="arrow" d="M106 142 H150"/>
  <rect class="box hot" x="150" y="176" width="100" height="44" rx="6"/><text x="200.0" y="202.9" font-size="14" text-anchor="middle">-&gt; block 4</text>
  <path class="arrow" d="M106 198 H150"/>
  <text x="450" y="56" font-size="14" text-anchor="middle" class="small">GPU memory pool</text>
  <rect class="box" x="330" y="64" width="112" height="38" rx="5"/><text x="386.0" y="87.2" font-size="12" text-anchor="middle">block 0: req 2</text>
  <rect class="box" x="450" y="64" width="112" height="38" rx="5"/><text x="506.0" y="87.2" font-size="12" text-anchor="middle">block 1: free</text>
  <rect class="box hot" x="330" y="108" width="112" height="38" rx="5"/><text x="386.0" y="131.2" font-size="12" text-anchor="middle">block 2: req 1</text>
  <rect class="box" x="450" y="108" width="112" height="38" rx="5"/><text x="506.0" y="131.2" font-size="12" text-anchor="middle">block 3: req 2</text>
  <rect class="box hot" x="330" y="152" width="112" height="38" rx="5"/><text x="386.0" y="175.2" font-size="12" text-anchor="middle">block 4: req 1</text>
  <rect class="box" x="450" y="152" width="112" height="38" rx="5"/><text x="506.0" y="175.2" font-size="12" text-anchor="middle">block 5: free</text>
  <rect class="box hot" x="330" y="196" width="112" height="38" rx="5"/><text x="386.0" y="219.2" font-size="12" text-anchor="middle">block 6: req 1</text>
  <rect class="box" x="450" y="196" width="112" height="38" rx="5"/><text x="506.0" y="219.2" font-size="12" text-anchor="middle">block 7: req 3</text>
  <path class="arrow" d="M250 86 L328 215" marker-end="url(#ah-blocks)"/>
  <path class="arrow" d="M250 142 L328 127" marker-end="url(#ah-blocks)"/>
  <path class="arrow" d="M250 198 L328 171" marker-end="url(#ah-blocks)"/>
</svg>
<figcaption>The request&#x27;s text is in order. Its memory is not. The table is the only thing that knows where each piece lives.</figcaption>
</figure>

The vLLM docs use this same shape. Their example uses 4 tokens per block, and a request with the prompt ABCDEF and output GHI ends with a block table of `[0 (ABCD), 1 (EFGH), 2 (I)]` ([prefix caching design](https://github.com/vllm-project/vllm/blob/main/docs/design/prefix_caching.md)). The block size in real use is a setting. We did not pin down its default, which varies by setup in the source we read.

Our `paged_kv.py` from the last lesson is the same idea in 30 lines: 56 requests fit instead of 12 in a toy pool.

The vLLM paper claims 2 to 4 times higher throughput than FasterTransformer and Orca at the same latency ([abstract](https://arxiv.org/abs/2309.06180)). That is the authors' claim on their tests. We read the abstract in an earlier pass and could not reach arXiv today to read it again.

## Continuous batching and the scheduler

vLLM lists continuous batching, chunked prefill and prefix caching together in its README. The docs say its scheduler is **token-budget-based**: each step it fills a budget of `max_num_batched_tokens` across running and waiting requests, and there are no separate prefill and decode phases ([architecture overview](https://github.com/vllm-project/vllm/blob/main/docs/design/arch_overview.md)).

When a request cannot get new blocks, the scheduler **preempts** another request. It frees that request's blocks and puts it back in the waiting queue. When the request is let back in, it is recomputed, not copied back from CPU memory. This is the current default per the docs ([optimization guide](https://github.com/vllm-project/vllm/blob/main/docs/configuration/optimization.md)).

<figure>
<svg viewBox="0 0 600 240" role="img" aria-labelledby="t-sched d-sched">
  <title id="t-sched">A request&#x27;s life inside the vLLM scheduler</title>
  <desc id="d-sched">A request moves from the waiting queue to running, first prefilling in chunks and then decoding one token per step, and finally finishing with its blocks freed. A dashed arrow shows that a running request can be preempted back to the waiting queue when no free blocks remain.</desc>
  <defs><marker id="ah-sched" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect class="box" x="10" y="40" width="120" height="56" rx="8"/><text x="70.0" y="65.0" font-size="15" text-anchor="middle">Waiting</text><text x="70.0" y="83.0" font-size="13" class="small" text-anchor="middle">queue</text>
  <rect class="box hot" x="170" y="40" width="130" height="56" rx="8"/><text x="235.0" y="65.0" font-size="15" text-anchor="middle">Running</text><text x="235.0" y="83.0" font-size="13" class="small" text-anchor="middle">prefill in chunks</text>
  <rect class="box hot" x="340" y="40" width="120" height="56" rx="8"/><text x="400.0" y="65.0" font-size="15" text-anchor="middle">Running</text><text x="400.0" y="83.0" font-size="13" class="small" text-anchor="middle">decode steps</text>
  <rect class="box" x="490" y="40" width="100" height="56" rx="8"/><text x="540.0" y="65.0" font-size="15" text-anchor="middle">Finished</text><text x="540.0" y="83.0" font-size="13" class="small" text-anchor="middle">blocks freed</text>
  <path class="arrow" d="M130 68 H166" marker-end="url(#ah-sched)"/>
  <path class="arrow" d="M300 68 H336" marker-end="url(#ah-sched)"/>
  <path class="arrow" d="M460 68 H486" marker-end="url(#ah-sched)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M365 100 C365 170 70 170 70 100" marker-end="url(#ah-sched)"/>
  <text x="215" y="168" font-size="12" text-anchor="middle" class="small">out of free blocks: preempt, free its blocks, recompute later</text>
  <text x="10" y="206" font-size="13" text-anchor="start" class="small">Each step, the scheduler fills a token budget (max_num_batched_tokens)</text>
  <text x="10" y="226" font-size="13" text-anchor="start" class="small">with running requests first, then pieces of waiting prompts.</text>
</svg>
<figcaption>From the vLLM docs: preempted requests are recomputed, not swapped to CPU memory, in the current engine.</figcaption>
</figure>

## Chunked prefill

A long prompt can hog a step. **Chunked prefill** cuts a big prefill into smaller chunks and mixes them with decode work in the same step. The docs say that in V1 it is on by default whenever possible, and that decode requests are scheduled first, so a long prompt delays other users' tokens less.

The docs also give a knob. Smaller `max_num_batched_tokens` values (for example 2048) give better inter-token latency. Higher values give better time to first token. They recommend values above 8192 for best throughput, especially for small models on large GPUs. Those are the docs' recommendations, not ours.

## Automatic prefix caching

Chat and RAG requests often start with the same text: a system prompt, a template, a document. **Prefix caching** keeps the KV cache of text already processed, so a new request with the same start skips that work. vLLM calls its version Automatic Prefix Caching, or APC ([docs](https://github.com/vllm-project/vllm/blob/main/docs/features/automatic_prefix_caching.md)).

How it works, per the design page: each full block is given a hash made from its own tokens plus the tokens before it. A new request looks up its blocks by hash. Only full blocks are cached. Unused cached blocks are evicted least-recently-used first. In the source we read, `enable_prefix_caching` defaults to `True`. We could not confirm that on the public docs page.

The docs note a limit. APC only speeds up prefill. If most time goes to writing long answers, or no requests share a start, it does not help.

For shared servers, a request can carry a `cache_salt`. Only requests with the same salt can reuse each other's cached blocks. This stops one user from guessing at another's prompt by timing replies.

## An OpenAI-compatible server

`vllm serve` starts an HTTP server that follows the OpenAI API. By default it listens at `http://localhost:8000`, hosts one model at a time, and supports endpoints such as `/v1/chat/completions` and `/v1/completions` ([quickstart](https://github.com/vllm-project/vllm/blob/main/docs/getting_started/quickstart.md), [online serving](https://github.com/vllm-project/vllm/blob/main/docs/serving/online_serving/README.md)). The quickstart's example:

```bash
vllm serve Qwen/Qwen2.5-1.5B-Instruct
curl http://localhost:8000/v1/models
```

Other flags the docs show: `--host`, `--port`, `--api-key` to require a key, and `--tensor-parallel-size` to split a model over several GPUs. Because the API matches OpenAI's, the client code from the [first API call lesson](lesson:foundations/first-api-call) works by changing the base URL.

Not run here: the install, a real model, a GPU. The README lists NVIDIA, AMD and Intel GPUs, several CPU types and more as supported hardware. Check the install page for your setup.

:::try
Read the "Example" section at the end of the [prefix caching design page](https://github.com/vllm-project/vllm/blob/main/docs/design/prefix_caching.md). With 4 tokens per block, which blocks of a 14-token prompt can be reused if its first 10 tokens match a cached request? Check your answer against the page.
:::

:::check What does a block table do?
It maps each piece of a request's text, in order, to the physical memory block that holds its KV cache. That lets the blocks sit anywhere in memory.
:::

:::check Why does chunked prefill help the users who are already getting tokens?
A long prompt is cut into pieces and mixed in with decode work. Decode requests are scheduled first, so the long prompt does not stall them for a whole step.
:::
