---
title: A map of the code, from your request to the CPU
summary: The four layers of llama.cpp, which folder holds what, and the path one request takes through all of them. Read this before opening any source file.
time: 20 min
---

The llama.cpp repo has more than half a million lines of code. Nobody reads it front to back. You need a map: which layer does what, and which folder to open for a given question. This lesson is that map. The next three lessons zoom into each layer.

All paths are from the repo root at commit `0fb8f15`. Line numbers drift, so search for the function name if a line number is off.

## Four layers

<figure>
<svg viewBox="0 0 860 360" role="img" aria-labelledby="lmap-t lmap-d">
  <title id="lmap-t">The four layers of llama.cpp</title>
  <desc id="lmap-d">From top to bottom: tools such as llama-server and llama-cli; the common library with argument parsing, chat templates and sampling setup; libllama with models, KV cache, batches and samplers; and ggml with tensors, graphs and one backend per kind of hardware.</desc>
  <g font-size="15">
    <rect class="box" x="16" y="16" width="828" height="64" rx="10"/>
    <text x="32" y="42" font-weight="700">tools/  app/</text>
    <text x="32" y="66" class="small">llama-server, llama-cli, llama-quantize, llama-bench, the unified llama binary</text>
    <rect class="box" x="16" y="96" width="828" height="64" rx="10"/>
    <text x="32" y="122" font-weight="700">common/</text>
    <text x="32" y="146" class="small">argument parsing, Jinja chat templates, tool-call parsers, model download, sampler setup</text>
    <rect class="box hot" x="16" y="176" width="828" height="64" rx="10"/>
    <text x="32" y="202" font-weight="700">src/ + include/llama.h = libllama</text>
    <text x="32" y="226" class="small">model loading, one graph builder per architecture, KV cache, batches, samplers, tokenizers</text>
    <rect class="box" x="16" y="256" width="828" height="88" rx="10"/>
    <text x="32" y="282" font-weight="700">ggml/ = the tensor library</text>
    <text x="32" y="306" class="small">tensors, compute graphs, GGUF files, quant formats, scheduler</text>
    <text x="32" y="330" class="small">backends: ggml-cpu, ggml-cuda, ggml-metal, ggml-vulkan, ggml-sycl, ggml-hip, ...</text>
  </g>
</svg>
<figcaption>Each layer only calls the one below it. Tools never touch ggml directly for model work.</figcaption>
</figure>

| Layer | Folder | Lines (approx.) | Knows about |
|---|---|---|---|
| Tools | `tools/`, `app/`, `examples/` | server alone 42k | HTTP, flags, users |
| common | `common/` | 46k | Chat templates, tool calls, downloads |
| libllama | `src/`, `include/llama.h` | 120k, of which 50k in `src/models/` | Models, tokens, sequences |
| ggml | `ggml/` | CPU backend 96k, CUDA 52k, Vulkan 43k, Metal 35k | Tensors and math only |

We counted these with `wc -l` over `.c`, `.cpp`, `.h`, `.cu`, `.py` and shader files. Tests add another 68k lines.

The line that matters most: **ggml knows nothing about language models**. It does not know what a token or a layer is. It multiplies tensors. libllama turns "run Llama on these tokens" into a ggml graph.

## What lives where

| You want to know... | Open |
|---|---|
| The public C API | `include/llama.h` (1,752 lines, well commented) |
| How a file becomes a model in memory | `src/llama-model-loader.cpp`, `src/llama-model.cpp` |
| The math of one model family | `src/models/<name>.cpp`, e.g. `src/models/llama.cpp` (236 lines) |
| Shared building blocks (attention, FFN, RoPE) | `src/llama-graph.cpp` |
| Names of architectures, metadata keys, tensors | `src/llama-arch.cpp` |
| The KV cache | `src/llama-kv-cache.cpp`, `src/llama-kv-cells.h` |
| How a batch is split up | `src/llama-batch.cpp` |
| Sampling and grammars | `src/llama-sampler.cpp`, `src/llama-grammar.cpp` |
| Tokenizers | `src/llama-vocab.cpp` |
| The tensor type and ops | `ggml/include/ggml.h`, `ggml/src/ggml.c` |
| The GGUF format | top comment of `ggml/include/gguf.h`, parser in `ggml/src/gguf.cpp` |
| Quant block layouts | `ggml/src/ggml-common.h` |
| CPU kernels | `ggml/src/ggml-cpu/` (SIMD code per chip in `arch/x86`, `arch/arm`, ...) |
| GPU kernels | `ggml/src/ggml-cuda/`, `ggml-metal/`, `ggml-vulkan/` |
| HF to GGUF conversion | `convert_hf_to_gguf.py` (now 339 lines) and the `conversion/` package (one file per model family) |
| The Python GGUF library | `gguf-py/gguf/` |
| The HTTP server | `tools/server/server-context.cpp`, `tools/server/README-dev.md` |

Two folders are new enough that older tutorials do not mention them:

- `app/` builds one binary called `llama` with subcommands: `llama serve`, `llama cli`, `llama download`, plus hidden ones like `llama bench` and `llama quantize` (`llama help all` lists them). They call the same code as the separate `llama-server`, `llama-cli` binaries, which still exist.
- `conversion/` split the old 10,000-line converter into about 120 per-model modules. `convert_hf_to_gguf.py` is now a thin entry point.

## The path of one request

Follow one chat request from `curl` to the CPU. Each step names the function so you can find it.

1. **HTTP.** `llama-server` parses JSON on an HTTP thread, applies the chat template (Jinja, in `common/jinja/`), and tokenizes. It posts a task to a queue.
2. **Slot.** One server thread runs a loop (`server_queue::start_loop`). It gives the task a free **slot** (one conversation's state) and calls `update_slots()`.
3. **Batch.** `update_slots()` puts tokens from every busy slot into **one shared batch**. New prompts and next tokens of running answers ride together. This is **continuous batching**.
4. **Decode.** The server calls libllama's decode. In `llama_context::decode` the batch is checked, then cut into **ubatches** (micro-batches small enough for the compute buffers).
5. **KV cache slot.** For each ubatch, the KV cache finds free cells (`find_slot`) to store the new keys and values.
6. **Graph.** libllama builds a ggml graph for the model: `llama_model::build_graph` calls the architecture's builder (`src/models/llama.cpp` for Llama), which strings together norm, attention, feed-forward for every layer.
7. **Schedule.** ggml's scheduler (`ggml_backend_sched`) splits the graph by backend: layers whose weights sit on the GPU run there, the rest on the CPU.
8. **Compute.** Each backend runs its part. On the CPU, a thread pool walks the nodes and calls one kernel per op, such as a quantized matrix multiply.
9. **Logits.** The last tensor holds a score for every token in the vocabulary. libllama copies it out.
10. **Sample.** The slot's sampler chain picks one token. The server streams its text back and the loop goes round again.

The rest of this part of the track walks this path bottom-up: [ggml](lesson:llamacpp/ggml-tensors-graphs-backends) first, then [libllama](lesson:llamacpp/inside-libllama), then [your own program](lesson:llamacpp/your-own-program) on top.

## How to read it without drowning

- **Start from `include/llama.h`.** It is the contract. Every public function has a comment.
- **Read one small program end to end.** `examples/simple/simple.cpp` is 238 lines and touches every main API.
- **Pick one model file.** `src/models/llama.cpp` is the reference architecture. Most others are variations.
- **Use the debugger, not your eyes.** Build with `-DCMAKE_BUILD_TYPE=Debug` and break on `llama_context::decode`.
- **Print the graph.** `examples/eval-callback` (`llama-eval-callback`) prints every tensor as it is computed: name, op, shape, and a few values.
- **Check `git log` for a file** before trusting any tutorial, this one included. The repo had 50 commits in the 34 hours before our pinned commit.

:::try
Clone the repo and run `grep -n "LLM_ARCH_LLAMA" src/*.cpp src/models/*.cpp | head`. Every hit is a place where Llama is treated differently from other models. That list is your checklist if you ever add a model.
:::

:::check A request is slow. Your teammate wants to profile `llama-server`'s JSON parsing. Where is the time more likely to go?
Almost always in steps 6 to 8: the graph compute, mostly matrix multiplies in ggml. JSON parsing and templating run on separate HTTP threads and take microseconds next to milliseconds per token.
:::

:::check Why can ggml run a model it has never heard of?
Because it never sees "a model". libllama turns the architecture into a graph of generic ops (matmul, add, softmax, RoPE). ggml only needs to know how to run each op on each backend.
:::
