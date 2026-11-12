---
title: Your own program on libllama
summary: Write, build and run a 120-line C++ program that loads a GGUF model, peeks at raw logits, samples with a chain, and reads back the KV cache state. Then see where to go from there - bindings, multiple sequences, and embedding llama.cpp in an app.
time: 25 min
---

The tools are thin layers over `libllama`. When you need something they do not do (a custom decoding loop, a game, a phone app, a research experiment), you call the library yourself. This lesson does that in C++ with the API at commit `0fb8f15`.

## The program

`code/llamacpp/mini_generate.cpp` is about 120 lines. It does eight things, in this order. Each matches a step in [inside libllama](lesson:llamacpp/inside-libllama).

| Step | Calls |
|---|---|
| Load backends | `llama_backend_init`, `ggml_backend_load_all` |
| Load the model | `llama_model_default_params`, `llama_model_load_from_file`, `llama_model_get_vocab` |
| Tokenize | `llama_tokenize` (twice: once to size, once to fill) |
| Make a context | `llama_context_default_params`, `llama_init_from_model` |
| Build a sampler chain | `llama_sampler_chain_init`, `_add(top_k)`, `_add(top_p)`, `_add(temp)`, `_add(dist)` |
| Prefill the prompt | `llama_batch_ext_init`, `_add_token`, `_set_pos`, `_set_output_logits`, `llama_process` |
| Peek at the logits | `llama_get_logits_ith(ctx, -1)` |
| Generate | loop: `llama_sampler_sample`, `llama_vocab_is_eog`, refill batch with one token, `llama_process` |

The core of it, the prefill and the loop:

```cpp
llama_batch_ext * batch = llama_batch_ext_init(ctx);
auto fill = [&](const llama_token * toks, int n, llama_pos pos0) {
    llama_batch_ext_clear(batch);
    for (int i = 0; i < n; i++) {
        int idx = llama_batch_ext_add_token(batch, 0, toks[i]);   // sequence 0
        llama_pos pos = pos0 + i;
        llama_batch_ext_set_pos(batch, idx, &pos);
    }
    llama_batch_ext_set_output_logits(batch, n - 1, true);        // logits for the last token only
};
fill(tokens.data(), n_prompt, 0);
llama_process(ctx, LLAMA_PROCESS_TYPE_DECODE, batch);             // prefill

for (; n_out < n_predict; n_out++) {
    llama_token next = llama_sampler_sample(smpl, ctx, -1);       // sample from the last logits
    if (llama_vocab_is_eog(vocab, next)) break;                   // end of generation
    printf("%s", piece(vocab, next).c_str());
    fill(&next, 1, n_pos++);                                      // one token, next position
    if (llama_process(ctx, LLAMA_PROCESS_TYPE_DECODE, batch) != 0) break;
}
```

That loop is the whole of text generation. The prompt goes in once (prefill); then one token at a time goes in, at the next position, and the KV cache remembers everything before it.

This uses the **new batch API** (`llama_batch_ext` and `llama_process`), the same one `examples/simple/simple.cpp` uses at our commit. Older code and most tutorials use `llama_batch_get_one` and `llama_decode`. Both still work; the header says to avoid `llama_batch_get_one` in new code.

## Build and run it

You need a built llama.cpp (see [clone and build](lesson:llamacpp/clone-and-build)) and any GGUF model. We used the tiny model from [lesson 4](lesson:llamacpp/train-convert-run).

```bash
LLAMA=~/src/llama.cpp
g++ -std=c++17 -O2 code/llamacpp/mini_generate.cpp \
    -I$LLAMA/include -I$LLAMA/ggml/include \
    -L$LLAMA/build/bin -lllama -lggml -lggml-base \
    -Wl,-rpath,$LLAMA/build/bin -o mini_generate
./mini_generate tiny-llama-Q8_0.gguf "The KV cache" 40
```

`-Wl,-rpath,...` records where the shared libraries are, so you do not need `LD_LIBRARY_PATH`. On macOS use `clang++` and the same flags.

Our output:

OUTPUT_MINI

Read the output as a checklist:

- **`prompt tokens`** shows the tokenizer at work. Token 1 is `<s>`, the BOS (beginning of sequence) token, added because we passed `add_special = true`. The `▁` in pieces is SentencePiece's mark for a space.
- **`top 5 next tokens`** are the raw logits before any sampler. A real model's top 5 would be sensible continuations; ours are what a 7M-parameter model trained for 9 minutes believes.
- **The text** is nonsense in the style of this course. That is the model, not the code.
- **`KV cache: ... positions 0..N`** confirms the cache holds every prompt and generated token except the last one sampled, which was never fed back.
- **The perf lines** come from `llama_perf_context_print`: prompt eval is the prefill, eval is the per-token loop.

## Things to try next

:::try
Change the sampler chain to greedy only (`llama_sampler_init_greedy()` instead of the four samplers) and run twice. The output is now the same every time. Then put back `dist` with a different seed and watch it change.
:::

:::try
Generate two answers to the same prompt in parallel. Prefill the prompt once in sequence 0, copy it with `llama_memory_seq_cp(llama_get_memory(ctx), 0, 1, -1, -1)`, set `cp.n_seq_max = 2`, and in the loop add one token for sequence 0 and one for sequence 1 to the same batch, each with its own output flag and its own sampler. That is exactly what `examples/batched/batched.cpp` does; read it after you try.
:::

## Examples worth reading in the repo

| File | Shows |
|---|---|
| `examples/simple/simple.cpp` | The minimum, 238 lines, new batch API |
| `examples/simple-chat/simple-chat.cpp` | A chat loop with `llama_chat_apply_template` |
| `examples/batched/batched.cpp` | Many sequences in one batch (still the classic `llama_batch` API) |
| `examples/embedding/embedding.cpp` | Embeddings and pooling |
| `examples/speculative-simple/` | A draft model and verification |
| `tools/server/server-context.cpp` | The real thing: slots, continuous batching, prompt cache |

## From other languages

You do not have to write C++:

- **Python.** The most common route is to run `llama-server` and use HTTP, as in [the server lesson](lesson:llamacpp/llama-server). There are also third-party bindings that wrap libllama directly, such as `llama-cpp-python`. They are separate projects, often a few weeks behind. Check their docs for which llama.cpp version they bundle.
- **Swift / iOS and Android.** The repo has `examples/llama.swiftui`, `examples/llama.android`, and `build-xcframework.sh` for Apple platforms.
- **Any language with a C FFI** (Go, Rust, C#, Node, Zig) can call `llama.h` directly; it is plain C.

If you bind it yourself: libllama's API changes often. `llama.h` marks old functions with `DEPRECATED(...)` before removing them. Pin a commit and read the diff of `include/llama.h` when you upgrade.

:::check Why does the generation loop add only one token per `llama_process` call after the prompt?
The KV cache already holds keys and values for every earlier token. Each step only needs to compute the new token at the next position, then sample from its logits.
:::

:::check Your program prints good text with `-ngl 0` but crashes at load with `-ngl 99` on a GPU build. Where do you look first?
The load log: the device list, how many layers were offloaded, and the buffer sizes. The model plus the KV cache may not fit in VRAM. Lower `n_gpu_layers` or the context size, or use a smaller quant.
:::
