---
title: TensorRT-LLM in depth
summary: NVIDIA's serving library. It used to build an engine file first, no longer does, and still bundles in-flight batching, FP8 and FP4, and speculative decoding.
time: 25 min
---

**TensorRT-LLM** is NVIDIA's open-source library for running language models fast on NVIDIA GPUs. Its overview calls itself a library "for accelerating and optimizing inference performance of the latest large language models (LLMs) on NVIDIA GPUs" ([overview](https://github.com/NVIDIA/TensorRT-LLM/blob/main/docs/source/overview.md)).

We did not run it. We read its README and docs source on 2026-11-12, when the README showed release 1.4.0rc4.

## Engine build versus PyTorch backend

Many older guides tell you to **build an engine**: convert the weights, run `trtllm-build`, and get a file tuned for one GPU setup, then serve that file. That is no longer the current way.

The release notes list "TensorRT backend removed. PyTorch is now the sole execution backend", and say `trtllm-build` and the per-model `convert_checkpoint.py` scripts were removed ([release notes](https://github.com/NVIDIA/TensorRT-LLM/blob/main/docs/source/release-notes.md), in the 1.2 section). The migration guide says there is "no engine-build step: HuggingFace checkpoints load directly" ([migration guide](https://github.com/NVIDIA/TensorRT-LLM/blob/main/docs/source/legacy/tensorrt-backend-removal.md)).

<figure>
<svg viewBox="0 0 600 222" role="img" aria-labelledby="t-trtpipe d-trtpipe">
  <title id="t-trtpipe">From weights to a running server in TensorRT-LLM</title>
  <desc id="d-trtpipe">Top row, shown dashed because it was removed: Hugging Face weights, convert, trtllm-build, an engine file, then serve the engine. Bottom row, current: Hugging Face weights go straight into trtllm-serve on the PyTorch backend, which exposes an OpenAI-style API.</desc>
  <defs><marker id="ah-trtpipe" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="8" y="20" font-size="14" text-anchor="start" font-weight="700">Earlier releases: build an engine first</text>
  <rect class="box" x="8" y="34" width="100" height="44" rx="6"/><text x="58.0" y="60.55" font-size="13" text-anchor="middle">HF weights</text>
  <path class="arrow" stroke-dasharray="5 5" d="M108 56 H118" marker-end="url(#ah-trtpipe)"/>
  <rect class="box" x="120" y="34" width="100" height="44" rx="6"/><text x="170.0" y="60.55" font-size="13" text-anchor="middle">convert</text>
  <path class="arrow" stroke-dasharray="5 5" d="M220 56 H230" marker-end="url(#ah-trtpipe)"/>
  <rect class="box" x="232" y="34" width="100" height="44" rx="6"/><text x="282.0" y="60.55" font-size="13" text-anchor="middle">trtllm-build</text>
  <path class="arrow" stroke-dasharray="5 5" d="M332 56 H342" marker-end="url(#ah-trtpipe)"/>
  <rect class="box" x="344" y="34" width="100" height="44" rx="6"/><text x="394.0" y="60.55" font-size="13" text-anchor="middle">engine file</text>
  <rect class="box" x="456" y="34" width="130" height="44" rx="6"/><text x="521.0" y="60.55" font-size="13" text-anchor="middle">serve engine</text>
  <path class="arrow" stroke-dasharray="5 5" d="M428 56 H452" marker-end="url(#ah-trtpipe)"/>
  <text x="8" y="98" font-size="12" text-anchor="start" class="small">Removed in release 1.2 (per the release notes). Shown dashed: you cannot do this today.</text>
  <text x="8" y="140" font-size="14" text-anchor="start" font-weight="700">Current releases: load the checkpoint and serve</text>
  <rect class="box" x="8" y="154" width="130" height="52" rx="8"/><text x="73.0" y="177.0" font-size="13" text-anchor="middle">HF weights</text><text x="73.0" y="193.0" font-size="11" class="small" text-anchor="middle">or a FP8 / FP4 one</text>
  <rect class="box hot" x="190" y="154" width="160" height="52" rx="8"/><text x="270.0" y="177.0" font-size="13" text-anchor="middle">trtllm-serve</text><text x="270.0" y="193.0" font-size="11" class="small" text-anchor="middle">PyTorch backend</text>
  <rect class="box" x="402" y="154" width="184" height="52" rx="8"/><text x="494.0" y="177.0" font-size="13" text-anchor="middle">OpenAI-style API</text><text x="494.0" y="193.0" font-size="11" class="small" text-anchor="middle">/v1/chat/completions</text>
  <path class="arrow" d="M138 180 H186" marker-end="url(#ah-trtpipe)"/>
  <path class="arrow" d="M350 180 H398" marker-end="url(#ah-trtpipe)"/>
</svg>
<figcaption>The old build step is gone in current releases. The server loads the checkpoint directly.</figcaption>
</figure>

If you find a blog post with `trtllm-build` in it, check its date and the version it used. We did not verify what each older release did.

## Serve it

`trtllm-serve` starts an OpenAI-compatible server. The quickstart's first example is:

```bash
trtllm-serve "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
```

It then answers `v1/chat/completions` ([quick start](https://github.com/NVIDIA/TensorRT-LLM/blob/main/docs/source/quick-start-guide.md)). The `trtllm-serve` page lists `/v1/models`, `/v1/completions`, `/v1/chat/completions`, `/health` and `/metrics`. The overview says its Python LLM API works with NVIDIA Dynamo and the Triton Inference Server. We did not read the Triton integration docs.

Supported GPUs per the docs: Blackwell (B200, GB200, B300, GB300, DGX Spark), Hopper (H100, H200, GH200), Ada Lovelace (L20, L40, L40S) and Ampere (A100) ([supported hardware](https://github.com/NVIDIA/TensorRT-LLM/blob/main/docs/source/supported-hardware.md)). All are NVIDIA.

## In-flight batching and paged KV cache

The docs name **in-flight batching** as their continuous batching: sequences in the context phase (prefill) are processed together with sequences in the generation phase (decode). It needs the input tokens packed without padding ([scheduler page](https://github.com/NVIDIA/TensorRT-LLM/blob/main/docs/source/features/paged-attention-ifb-scheduler.md)). The overview also lists a paged KV cache "with intelligent block reuse", and chunked prefill. So the ideas from the vLLM lesson appear here under their own settings.

## FP8 and FP4

A 16-bit number takes 2 bytes. **FP8** takes 1, and **FP4** takes half a byte. Less memory per weight means smaller models and faster reads, at some risk to quality, as in the [GGUF lesson](lesson:inference/laptop-gguf-quantization).

The overview says FP8 is supported on H100 and later GPUs and "can double performance and halve memory consumption compared to 16-bit floating point, with minimal impact on model accuracy". FP4 is described as native on B200. Both are NVIDIA's claims. The quantization page says the PyTorch backend supports FP4 and FP8 on the latest Blackwell and Hopper GPUs, and shows loading a ready-made checkpoint such as `nvidia/Llama-3.1-8B-Instruct-FP8` made with NVIDIA's Model Optimizer ([quantization](https://github.com/NVIDIA/TensorRT-LLM/blob/main/docs/source/features/quantization.md)). The KV cache can also be set to FP8.

## Speculative decoding

Decode writes one token per pass, and the pass is slow because it reads the weights. **Speculative decoding** guesses several tokens cheaply and checks them together. The docs: "A lightweight drafting mechanism proposes candidate tokens, and the target model verifies them in a single forward pass. Tokens that match are accepted, reducing the number of sequential forward passes needed" ([speculative decoding](https://github.com/NVIDIA/TensorRT-LLM/blob/main/docs/source/features/speculative-decoding.md)).

<figure>
<svg viewBox="0 0 600 300" role="img" aria-labelledby="t-spec d-spec">
  <title id="t-spec">Speculative decoding: draft then verify</title>
  <desc id="d-spec">A draft model guesses four tokens: the cat sat on. The target model checks all four in a single pass and accepts the first three but rejects the fourth. The result keeps the three accepted tokens and adds the target model&#x27;s own fourth token, under.</desc>
  <defs><marker id="ah-spec" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="8" y="22" font-size="14" text-anchor="start" font-weight="700">1. A small, fast draft guesses the next 4 tokens</text>
  <rect class="box" x="10" y="34" width="72" height="40" rx="6"/><text x="46.0" y="58.9" font-size="14" text-anchor="middle">the</text>
  <rect class="box" x="90" y="34" width="72" height="40" rx="6"/><text x="126.0" y="58.9" font-size="14" text-anchor="middle">cat</text>
  <rect class="box" x="170" y="34" width="72" height="40" rx="6"/><text x="206.0" y="58.9" font-size="14" text-anchor="middle">sat</text>
  <rect class="box" x="250" y="34" width="72" height="40" rx="6"/><text x="286.0" y="58.9" font-size="14" text-anchor="middle">on</text>
  <path class="arrow" d="M160 80 V108" marker-end="url(#ah-spec)"/>
  <text x="8" y="128" font-size="14" text-anchor="start" font-weight="700">2. The big model checks all 4 in one forward pass</text>
  <rect class="box hot" x="10" y="140" width="72" height="40" rx="6"/><text x="46.0" y="157.0" font-size="14" text-anchor="middle">the</text><text x="46.0" y="174.0" font-size="12" class="small" text-anchor="middle">accept</text>
  <rect class="box hot" x="90" y="140" width="72" height="40" rx="6"/><text x="126.0" y="157.0" font-size="14" text-anchor="middle">cat</text><text x="126.0" y="174.0" font-size="12" class="small" text-anchor="middle">accept</text>
  <rect class="box hot" x="170" y="140" width="72" height="40" rx="6"/><text x="206.0" y="157.0" font-size="14" text-anchor="middle">sat</text><text x="206.0" y="174.0" font-size="12" class="small" text-anchor="middle">accept</text>
  <rect class="box" x="250" y="140" width="72" height="40" rx="6"/><text x="286.0" y="157.0" font-size="14" text-anchor="middle">on</text><text x="286.0" y="174.0" font-size="12" class="small" text-anchor="middle">reject</text>
  <path class="arrow" d="M160 186 V214" marker-end="url(#ah-spec)"/>
  <text x="8" y="234" font-size="14" text-anchor="start" font-weight="700">3. Keep the 3 that match, plus the big model&#x27;s own pick for slot 4</text>
  <rect class="box hot" x="10" y="246" width="72" height="40" rx="6"/><text x="46.0" y="270.9" font-size="14" text-anchor="middle">the</text>
  <rect class="box hot" x="90" y="246" width="72" height="40" rx="6"/><text x="126.0" y="270.9" font-size="14" text-anchor="middle">cat</text>
  <rect class="box hot" x="170" y="246" width="72" height="40" rx="6"/><text x="206.0" y="270.9" font-size="14" text-anchor="middle">sat</text>
  <rect class="box hot" x="250" y="246" width="72" height="40" rx="6"/><text x="286.0" y="263.0" font-size="14" text-anchor="middle">under</text><text x="286.0" y="280.0" font-size="12" class="small" text-anchor="middle">big model&#x27;s</text>
  <text x="340" y="270" font-size="13" text-anchor="start" class="small">4 tokens from 1 big pass</text>
</svg>
<figcaption>A toy example. Guessing is cheap and checking many tokens at once costs about one pass, so good guesses save passes.</figcaption>
</figure>

The page lists several ways to draft, including a separate draft model, EAGLE 3, MTP and n-gram. It warns that a draft model must share the target's tokenizer, or the acceptance rate drops and speed gets worse. The docs say the technique accelerates inference "at low batch sizes", so it is not a free win for every load.

## What is left unverified

We did not run TensorRT-LLM, check the Triton path, or confirm any speed claim. Headline records in the README are NVIDIA's, on NVIDIA's setups.

:::check Why do older tutorials about TensorRT-LLM mention an engine build step that current docs do not?
The TensorRT engine backend was removed. The release notes say PyTorch is the only backend, and checkpoints load directly.
:::

:::check In speculative decoding, who has the last word on each token?
The big target model. It checks every guessed token in one pass and keeps only those that match what it would have produced.
:::
