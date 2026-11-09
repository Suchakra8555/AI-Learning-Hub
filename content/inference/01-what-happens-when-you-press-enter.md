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

## The KV cache

To write token 500, the model looks back at tokens 1 to 499. Recomputing them each time would be wasteful, so the server keeps a **key** and a **value** for every earlier token, for every layer. This store is the **KV cache**. It grows with the length of the text and with the number of requests served together.

Run `code/inference/kv_cache.py`:

```text
1 request,  4096 tokens: 2.0 GiB
16 requests, 4096 tokens: 32.0 GiB
```

The formula is in the file: 2 (key and value) × layers × heads × head size × bytes per number × tokens × requests. For a Llama 2 7B shape in 16-bit numbers, one 4,096-token request needs about 2 GiB. NVIDIA's guide gives about 2 GB for the same case, and the script checks that match. The weights alone are about 14 GB.

Sixteen requests at once need 32 GiB for the cache. Memory runs out long before math does. That is the problem serving software exists to solve.

## Batching

Serving many requests together lets one load of the weights serve all of them. **In-flight batching** (also called continuous batching) lets a finished request leave and a new one join without waiting for the whole batch.

| Word | One line |
|---|---|
| Prefill | Read the prompt, all at once |
| Decode | Write tokens, one at a time |
| KV cache | Saved keys and values of earlier tokens |
| Batching | Serve many requests in one pass |

:::check Why does a long prompt use more GPU memory even before the model answers?
The KV cache stores keys and values for every prompt token, and it grows with the prompt length.
:::
