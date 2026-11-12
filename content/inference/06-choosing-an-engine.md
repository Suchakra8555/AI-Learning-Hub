---
title: Choosing an engine
summary: vLLM, SGLang and TensorRT-LLM side by side, a way to pick one to try first, and the gap none of them fill on their own.
time: 20 min
---

You have now met three engines. Here they are next to each other. Everything in the table comes from the projects' own docs, read on 2026-11-12. We ran none of them.

## Side by side

| | vLLM | SGLang | TensorRT-LLM |
|---|---|---|---|
| Who | Began at UC Berkeley's Sky Computing Lab | Hosted by LMSYS, a non-profit | NVIDIA |
| Hardware listed | NVIDIA, AMD, Intel GPUs, CPUs, TPUs and more | NVIDIA, AMD, TPU, Intel, Apple Silicon and more | NVIDIA GPUs (Ampere and newer in the list we read) |
| Memory idea | PagedAttention, blocks and a block table | RadixAttention, a tree of cached prefixes | Paged KV cache with block reuse |
| Batching | Continuous batching, chunked prefill | Chunked prefill option, cache-aware scheduling option | In-flight batching, chunked prefill |
| Prefix reuse | Automatic prefix caching | Radix tree | KV block reuse |
| Structured output | Listed (xgrammar, guidance) | JSON schema, regex, EBNF | Guided decoding listed |
| Speculative decoding | Listed (n-gram, EAGLE and others) | Several methods | EAGLE 3, MTP, n-gram, draft model |
| Low-bit weights | FP8, FP4 variants, INT8, INT4, GPTQ, AWQ, GGUF | A quantization page exists | FP8, FP4, GPTQ, AWQ |
| Server | `vllm serve`, OpenAI-style | `sglang serve`, OpenAI-style | `trtllm-serve`, OpenAI-style |
| Setup step | None beyond install | None beyond install | None. The engine-build step was removed |

The table paraphrases each project's own pages. A feature listed in two columns does not mean two equal implementations, and none of this is a benchmark. Hardware lists change quickly. Read the install page for your GPU.

## A way to pick one to try first

<figure>
<svg viewBox="0 0 600 378" role="img" aria-labelledby="t-flow d-flow">
  <title id="t-flow">Which engine to try first</title>
  <desc id="d-flow">A flowchart of three questions. Laptop, CPU only or offline leads to llama.cpp. Non-NVIDIA hardware leads to vLLM or SGLang. NVIDIA hardware and willingness to tune with FP8 or FP4 leads to TensorRT-LLM. Otherwise try vLLM or SGLang.</desc>
  <defs><marker id="ah-flow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect class="box" x="10" y="10" width="250" height="52" rx="8"/><text x="135.0" y="40.55" font-size="13" text-anchor="middle">Laptop, CPU only, or offline?</text>
  <rect class="box hot" x="330" y="10" width="250" height="52" rx="8"/><text x="455.0" y="33.0" font-size="13" text-anchor="middle">llama.cpp, GGUF file</text><text x="455.0" y="49.0" font-size="11" class="small" text-anchor="middle">lesson 7</text>
  <path class="arrow" d="M260 36 H326" marker-end="url(#ah-flow)"/>
  <text x="280" y="28" font-size="12" text-anchor="middle" class="small">yes</text>
  <path class="arrow" d="M135 62 V100" marker-end="url(#ah-flow)"/>
  <text x="148" y="84" font-size="12" text-anchor="start" class="small">no</text>
  <rect class="box" x="10" y="100" width="250" height="52" rx="8"/><text x="135.0" y="130.55" font-size="13" text-anchor="middle">AMD, TPU or other non-NVIDIA?</text>
  <rect class="box hot" x="330" y="100" width="250" height="52" rx="8"/><text x="455.0" y="123.0" font-size="13" text-anchor="middle">vLLM or SGLang</text><text x="455.0" y="139.0" font-size="11" class="small" text-anchor="middle">both list that hardware</text>
  <path class="arrow" d="M260 126 H326" marker-end="url(#ah-flow)"/>
  <text x="280" y="118" font-size="12" text-anchor="middle" class="small">yes</text>
  <path class="arrow" d="M135 152 V190" marker-end="url(#ah-flow)"/>
  <text x="148" y="174" font-size="12" text-anchor="start" class="small">no</text>
  <rect class="box" x="10" y="190" width="250" height="52" rx="8"/><text x="135.0" y="220.55" font-size="13" text-anchor="middle">NVIDIA, and ready to tune (FP8, FP4)?</text>
  <rect class="box hot" x="330" y="190" width="250" height="52" rx="8"/><text x="455.0" y="213.0" font-size="13" text-anchor="middle">TensorRT-LLM</text><text x="455.0" y="229.0" font-size="11" class="small" text-anchor="middle">and still test vLLM</text>
  <path class="arrow" d="M260 216 H326" marker-end="url(#ah-flow)"/>
  <text x="280" y="208" font-size="12" text-anchor="middle" class="small">yes</text>
  <path class="arrow" d="M135 242 V280" marker-end="url(#ah-flow)"/>
  <text x="148" y="264" font-size="12" text-anchor="start" class="small">no</text>
  <rect class="box hot" x="10" y="280" width="250" height="52" rx="8"/><text x="135.0" y="303.0" font-size="13" text-anchor="middle">vLLM or SGLang</text><text x="135.0" y="319.0" font-size="11" class="small" text-anchor="middle">try both on your prompts</text>
  <text x="10" y="360" font-size="13" text-anchor="start" class="small">Every leaf says try this first. Then measure your own model and traffic.</text>
</svg>
<figcaption>A starting point built from the features and hardware each project documents. It is our reading, not a benchmark result.</figcaption>
</figure>

The chart is our reading of what each project says, not a ranking. All three serve an OpenAI-style API, so your client code does not change when you switch. That makes it cheap to try two. Then measure with your own model and prompts ([benchmark honestly](lesson:inference/benchmark-honestly)).

## What none of them do

Each engine manages the GPUs it was given. It decides which requests share a batch and where the KV cache lives. It does not decide which engine should get a request, or how many engines to run.

Say you run three copies, each on four GPUs. A plain load balancer sends each request to the next copy in turn. One copy has your system prompt cached and one has the document, but the balancer cannot tell. A prompt that would be a cache hit on engine A lands on engine C and is recomputed. Prefill and decode also share the same GPUs in every copy, so a long prompt can slow other users' tokens.

<figure>
<svg viewBox="0 0 620 330" role="img" aria-labelledby="t-fleet d-fleet">
  <title id="t-fleet">One engine per GPU group, nobody coordinating the fleet</title>
  <desc id="d-fleet">Requests enter a load balancer that knows nothing about caches. It sends them to one of three engines, each with its own GPUs and its own cache contents. A box on the right says nobody decides where a request should go, when to split prefill and decode, or how many engines to run.</desc>
  <defs><marker id="ah-fleet" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect class="box" x="10" y="20" width="100" height="44" rx="8"/><text x="60.0" y="46.9" font-size="14" text-anchor="middle">Requests</text>
  <rect class="box" x="150" y="20" width="150" height="44" rx="8"/><text x="225.0" y="39.0" font-size="14" text-anchor="middle">Load balancer</text><text x="225.0" y="56.0" font-size="12" class="small" text-anchor="middle">no cache knowledge</text>
  <path class="arrow" d="M110 42 H146" marker-end="url(#ah-fleet)"/>
  <path class="arrow" d="M225 64 V80 H130"/>
  <rect class="box hot" x="150" y="100" width="150" height="54" rx="8"/><text x="225.0" y="124.0" font-size="14" text-anchor="middle">Engine A</text><text x="225.0" y="141.0" font-size="12" class="small" text-anchor="middle">cache: system prompt</text>
  <rect class="box" x="330" y="100" width="110" height="54" rx="8"/><text x="385.0" y="131.55" font-size="13" text-anchor="middle">4 GPUs</text>
  <path class="arrow" d="M130 80 V127 H147" marker-end="url(#ah-fleet)"/>
  <rect class="box hot" x="150" y="166" width="150" height="54" rx="8"/><text x="225.0" y="190.0" font-size="14" text-anchor="middle">Engine B</text><text x="225.0" y="207.0" font-size="12" class="small" text-anchor="middle">cache: doc 1</text>
  <rect class="box" x="330" y="166" width="110" height="54" rx="8"/><text x="385.0" y="197.55" font-size="13" text-anchor="middle">4 GPUs</text>
  <path class="arrow" d="M130 80 V193 H147" marker-end="url(#ah-fleet)"/>
  <rect class="box hot" x="150" y="232" width="150" height="54" rx="8"/><text x="225.0" y="256.0" font-size="14" text-anchor="middle">Engine C</text><text x="225.0" y="273.0" font-size="12" class="small" text-anchor="middle">cache: empty</text>
  <rect class="box" x="330" y="232" width="110" height="54" rx="8"/><text x="385.0" y="263.55" font-size="13" text-anchor="middle">4 GPUs</text>
  <path class="arrow" d="M130 80 V259 H147" marker-end="url(#ah-fleet)"/>
  <rect class="box" x="470" y="100" width="140" height="186" rx="8"/><text x="540.0" y="197.55" font-size="13" text-anchor="middle"></text>
  <text x="540" y="124" font-size="13" text-anchor="middle" class="small" font-weight="700">Nobody is in</text>
  <text x="540" y="142" font-size="13" text-anchor="middle" class="small" font-weight="700">charge here</text>
  <text x="540" y="184" font-size="12" text-anchor="middle" class="small">Where should this</text>
  <text x="540" y="200" font-size="12" text-anchor="middle" class="small">request go?</text>
  <text x="540" y="226" font-size="12" text-anchor="middle" class="small">When to split</text>
  <text x="540" y="242" font-size="12" text-anchor="middle" class="small">prefill and decode?</text>
  <text x="540" y="266" font-size="12" text-anchor="middle" class="small">How many engines?</text>
  <text x="10" y="312" font-size="13" text-anchor="start" class="small">Each engine is fast on its own GPUs. Nothing above them shares cache or plans capacity.</text>
</svg>
<figcaption>This gap is what NVIDIA Dynamo says it is built for. The Dynamo track covers it.</figcaption>
</figure>

SGLang's gateway, mentioned in the [SGLang lesson](lesson:inference/sglang-in-depth), is one answer for SGLang servers. A more general layer is the idea behind NVIDIA Dynamo. Per its README, Dynamo is an open-source inference stack that works above vLLM, SGLang or TensorRT-LLM and can run prefill and decode in separate GPU pools and route by KV cache overlap ([README](https://github.com/ai-dynamo/dynamo)). The README cites a 2x faster time to first token in one benchmark. That is the project's own claim, not something we tested.

The Dynamo track covers that next.

:::check You run three copies of one engine behind a round-robin balancer. Name one thing that gets worse.
Cache reuse. A request with a shared prefix may land on a copy that has not cached it, so the work is repeated.
:::
