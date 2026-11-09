---
title: Serving engines, vLLM, SGLang, TensorRT-LLM, and Dynamo
summary: What each project says it is for, and the idea of splitting prefill and decode across machines.
time: 20 min
---

A **serving engine** is the program that loads a model onto a GPU and handles requests with the ideas from the [last lesson](lesson:inference/what-happens-when-you-press-enter). Here is what each project says about itself. We read their own docs and READMEs, and we ran none of them.

## vLLM

An open-source library from UC Berkeley's Sky Computing Lab. Its key idea is **PagedAttention**: it manages the KV cache like an operating system manages memory pages, so little memory is wasted. It also uses continuous batching. The paper's abstract claims 2 to 4 times higher throughput than FasterTransformer and Orca at the same latency ([paper](https://arxiv.org/abs/2309.06180), [docs](https://docs.vllm.ai/en/latest/)). It lists support for quantization formats such as FP8, INT8, INT4, GPTQ and AWQ.

## SGLang

A serving framework hosted by LMSYS. Its docs list RadixAttention and prefix caching as core features ([docs](https://docs.sglang.io/)). Prefix caching reuses work when many requests start with the same text, which matches RAG and chat patterns with a long shared system prompt.

## TensorRT-LLM

NVIDIA's project. Its docs list KV cache management, quantization, speculative decoding, LoRA adapters, disaggregated serving and in-flight batching ([docs](https://nvidia.github.io/TensorRT-LLM/)). We did not confirm its hardware requirements.

## NVIDIA Dynamo

Not an engine itself. Per its README, Dynamo is an open-source inference stack that **orchestrates** engines. It can run prefill and decode in **separate GPU pools** that scale on their own, route requests by load and KV cache overlap, and use vLLM, SGLang or TensorRT-LLM underneath ([README](https://github.com/ai-dynamo/dynamo)). The README cites a 2x faster time to first token in one benchmark. That is the project's own claim, not something we tested. Its official docs page was empty when we looked, so we used the README only.

### Why split prefill and decode?

Prefill is heavy math. Decode is memory-bound. They want different hardware settings, and a long prefill can stall other users' decode. Giving each its own pool lets you size them separately.

| Project | Best described as |
|---|---|
| vLLM | An engine focused on memory-efficient batching |
| SGLang | An engine focused on reusing shared prefixes |
| TensorRT-LLM | NVIDIA's optimized engine |
| Dynamo | A layer that coordinates engines across machines |

This table paraphrases each project's own description. It is not a benchmark. To choose among them, measure your own model and traffic ([benchmark honestly](lesson:inference/benchmark-honestly)).

:::note
All three engines are aimed at NVIDIA GPUs in practice. We did not verify this for SGLang, whose home page lists other hardware. Reading and diagramming is what a laptop can do here.
:::

:::check What does disaggregated serving separate, and why?
It runs the prefill phase and the decode phase on different GPU pools, because they stress hardware differently and can then be scaled on their own.
:::
