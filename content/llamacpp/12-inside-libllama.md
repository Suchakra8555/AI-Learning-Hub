---
title: Inside libllama - loading, decoding, the KV cache, sampling
summary: What happens inside src/ between "load this file" and "here is the next token". The model loader, the context, how a batch becomes ubatches, how the KV cache stores sequences, how one architecture's graph is written, and how samplers chain.
time: 35 min
---

[ggml](lesson:llamacpp/ggml-tensors-graphs-backends) does the math but knows nothing about language models. **libllama** (`src/` plus `include/llama.h`) is the layer that does. It reads a GGUF file, builds the right graph for the architecture, keeps the KV cache, and turns logits into tokens.

This lesson follows the calls in the order a program makes them. Function names and files are from commit `0fb8f15`. Search for the name if a line number has moved.

## The objects you hold

| Object | Made by | Holds | How many |
|---|---|---|---|
| `llama_model` | `llama_model_load_from_file` | Weights, hyperparameters, vocab | One per model file, shared |
| `llama_context` | `llama_init_from_model` | KV cache, compute buffers, scheduler, logits | One per independent workload |
| `llama_batch` / `llama_batch_ext` | `llama_batch_init` / `llama_batch_ext_init` | Tokens to process, their positions and sequences | Reused every step |
| `llama_sampler` | `llama_sampler_chain_init` | Your sampling settings and state | One per stream of output |

The split between model and context matters. Weights are read-only, so one `llama_model` can back many contexts. That is how a server could run several workloads on one copy of the weights.

## Step 1: loading the model

`llama_model_load_from_file` (`src/llama.cpp`) runs these steps:

1. **Open the file.** `llama_model_loader` (`src/llama-model-loader.cpp`) calls `gguf_init_from_file` and indexes every tensor by name: which file (models can be split), which offset.
2. **Pick the architecture.** It reads `general.architecture` (say `"llama"`) and creates the matching C++ class. At our commit every architecture is a subclass of `llama_model_base`, listed in `llama_model_mapping()` in `src/llama-model.cpp`. Older posts describe free-standing `llm_build_*` structs instead.
3. **Read hyperparameters.** Generic ones first (`llama.context_length` → `n_ctx_train`, `llama.block_count` → number of layers), then the architecture's own `load_arch_hparams`.
4. **Load the vocab.** The tokenizer type, tokens, scores, merges, special token ids.
5. **Create tensors and place them.** `load_arch_tensors` declares every weight with its expected shape. If the file disagrees, loading fails with a shape error, which is the most common error when a converter and the C++ code disagree.
6. **Map the data.** By default the file is **memory-mapped**: the OS pages weights in from disk as they are touched, so start-up is fast and several processes share one copy in RAM. `llama_model_params.load_mode` picks `MMAP`, `MLOCK` (pin in RAM), `DIRECT_IO`, `NONE`, or `AUTO`.

GPU offload is decided here. `n_gpu_layers` defaults to `-1`, meaning all layers. Layers are given to devices **from the end**: with 32 layers and `-ngl 10`, layers 22 to 31 plus the output go to the GPU. You can see the result in the log line `offloaded 10/33 layers to GPU` (the output layer counts as one).

## Step 2: the context

`llama_init_from_model` (`src/llama-context.cpp`) turns your `llama_context_params` into internal `cparams`. The ones you will tune:

| Param | CLI flag | Meaning | Default |
|---|---|---|---|
| `n_ctx` | `-c` | KV cache size in tokens, for all sequences together | 0 = the model's training length |
| `n_batch` | `-b` | Most tokens you may submit in one decode call | 2048 |
| `n_ubatch` | `-ub` | Most tokens computed in one graph run | 512 |
| `n_seq_max` | `-np` (server) | How many independent sequences | 1 |
| `flash_attn_type` | `-fa on/off/auto` | Fused attention kernel | auto |
| `type_k`, `type_v` | `-ctk`, `-ctv` | KV cache number format | f16 |

`n_ctx` is rounded up to a multiple of 256. The context then creates its **memory** (the KV cache, or another kind for non-transformer models, see below) and reserves compute buffers by building a worst-case graph once. If that reserve fails, you are out of memory before any token is processed.

## Step 3: decode, batch → ubatches → graph

A **batch** is a list of tokens, each with a position, one or more sequence ids, and a flag saying whether you want logits for it. Prefill puts the whole prompt in one batch. Each generation step puts one token per active sequence.

The classic struct, still supported:

```c
typedef struct llama_batch {
    int32_t n_tokens;
    llama_token  *  token;
    float        *  embd;      // instead of token ids, raw embeddings (e.g. image patches)
    llama_pos    *  pos;
    int32_t      *  n_seq_id;
    llama_seq_id ** seq_id;
    int8_t       *  logits;    // 1 = give me the logits for this token
} llama_batch;
```

At our commit there is also a newer opaque **`llama_batch_ext`** with setter functions, processed by `llama_process()`. `examples/simple/simple.cpp` already uses it, and the header calls `llama_batch_get_one` "a helper function to facilitate transition to the new batch API - avoid using it". Old calls are converted internally, so both work. Expect the new one to win.

Inside `llama_context::decode`:

1. **Check and fill in.** `llama_batch_allocr::init` validates token ids and fills missing positions and sequence ids.
2. **Split into ubatches.** The memory's `init_batch` cuts the batch into pieces of at most `n_ubatch` tokens (`split_simple`, `split_equal` or `split_seq` in `src/llama-batch.cpp`), then asks the KV cache to find room for every piece. If there is no room, decode returns `1` and you should free some space.
3. **For each ubatch:** write its slot info into the cache, build (or reuse) the graph, set the inputs (token ids, positions, attention mask), and compute it through the scheduler.
4. **Copy outputs.** Logits for the tokens you flagged are copied from the backend into a host buffer. You read them with `llama_get_logits_ith(ctx, i)`.

Why two sizes? `n_batch` is how much work you may hand over at once. `n_ubatch` is how much the GPU or CPU chews per graph run, and it sets the size of the compute buffers. A bigger `n_ubatch` speeds up prompt processing but needs more memory.

Graph reuse matters for speed. During generation every step has the same shape (one token per sequence), so `process_ubatch` checks `can_reuse` and skips rebuilding.

## Step 4: one architecture's graph

Each architecture's math is one file in `src/models/`. The reference is `src/models/llama.cpp`, 236 lines. Its layer loop, trimmed:

```cpp
for (int il = 0; il < n_layer; ++il) {
    cur = build_norm(inpL, model.layers[il].attn_norm, NULL, LLM_NORM_RMS, il);
    auto [Qcur, Kcur, Vcur] = build_qkv(model.layers[il], cur, n_embd_head, n_head, n_head_kv, il);
    Qcur = build_rope(Qcur, inp_pos, il);
    Kcur = build_rope(Kcur, inp_pos, il);
    cur = build_attn(inp_attn, wo, ..., Qcur, Kcur, Vcur, ..., kq_scale, il);
    ffn_inp = ggml_add(ctx0, cur, inpSA);                 // residual
    cur = build_norm(ffn_inp, ffn_norm, ...);
    cur = build_ffn(cur, up, gate, down, ..., LLM_FFN_SILU, LLM_FFN_PAR, il);
    cur = ggml_add(ctx0, cur, ffn_inp);                  // residual
    inpL = cur;
}
```

If you have read a Llama paper, this is it, line for line: RMSNorm, Q/K/V projections, rotary position encoding (**RoPE**, which encodes a token's position by rotating its query and key vectors), attention, residual add, RMSNorm, a SiLU-gated feed-forward, residual add.

The helpers live in `src/llama-graph.cpp`. `build_attn` is the important one. It writes this ubatch's K and V into the cache, reads back all cached K and V for the sequence, applies the mask, and runs either plain attention (`build_attn_mha`) or the fused flash-attention op. Different `build_attn` overloads exist for each memory type.

Two tricks in the file are worth knowing:

- On the last layer, rows for tokens that need no logits are dropped with `ggml_get_rows`. During prefill of 2,000 tokens you usually want logits for one, so this skips 1,999 rows of the final layer.
- The names `attn_norm`, `ffn_up` and so on map to GGUF tensor names like `blk.0.ffn_up.weight` through tables in `src/llama-arch.cpp`.

## Step 5: the KV cache

During generation each new token's attention needs the keys and values of every earlier token. The **KV cache** stores them so they are computed once. (The [inference track](lesson:inference/what-happens-when-you-press-enter) explains why it exists. Here is how llama.cpp stores it.)

The cache is an array of **cells**, one per token slot, up to `n_ctx` cells. Each cell has (`src/llama-kv-cells.h`):

- a **position** (`pos`), the token's place in its sequence,
- a **set of sequence ids** (a bitset), the conversations this cell belongs to,
- a pending **shift**, for when positions are moved.

A cell can belong to **several sequences at once**. That is how a shared system prompt is stored once and used by many conversations.

`find_slot` looks for free cells for each ubatch, starting from a `head` index and wrapping around. You manage sequences through the public `llama_memory_*` API (get the handle with `llama_get_memory(ctx)`):

| Function | Does | Typical use |
|---|---|---|
| `llama_memory_seq_rm(mem, seq, p0, p1)` | Drop positions [p0, p1) of a sequence | Undo the last turn, trim history |
| `llama_memory_seq_cp(mem, src, dst, p0, p1)` | Mark cells as also belonging to `dst` (no copy) | Share a prefix between conversations |
| `llama_memory_seq_keep(mem, seq)` | Drop every other sequence | Pick the winner after beam search |
| `llama_memory_seq_add(mem, seq, p0, p1, delta)` | Shift positions; RoPE is re-applied | Context shift: drop old tokens, slide the rest |
| `llama_memory_seq_pos_max(mem, seq)` | Last position stored | Know where to continue |
| `llama_memory_clear(mem, true)` | Empty everything | New session |

Not every model uses this cache. `llama_model::create_memory` picks one of several types:

- `llama_kv_cache`: the standard one.
- `llama_kv_cache_iswa`: two caches for models that mix full attention with **sliding-window attention** (SWA, layers that only look at the last few thousand tokens). The SWA layers get a small cache. Gemma models use this.
- `llama_memory_recurrent`: for Mamba and RWKV, which keep one fixed-size state per sequence instead of one entry per token.
- `llama_memory_hybrid` and variants: attention cache plus recurrent state, for hybrid models.
- Several newer, model-specific variants (`dsa`, `dsv4`, `msa`, ...).
- No memory at all for encoder-only models like BERT.

The recurrent type is why `seq_rm` can return `false`: you cannot remove the middle of a recurrent state.

## Step 6: sampling

After decode, `llama_get_logits_ith(ctx, -1)` gives one score per vocabulary token for the last flagged position. A **sampler chain** turns that into a token:

```c
llama_sampler * smpl = llama_sampler_chain_init(llama_sampler_chain_default_params());
llama_sampler_chain_add(smpl, llama_sampler_init_top_k(40));
llama_sampler_chain_add(smpl, llama_sampler_init_top_p(0.95f, 1));
llama_sampler_chain_add(smpl, llama_sampler_init_temp(0.8f));
llama_sampler_chain_add(smpl, llama_sampler_init_dist(seed));
llama_token tok = llama_sampler_sample(smpl, ctx, -1);
```

Each sampler implements `apply` on a candidate list (`llama_token_data_array`) and `accept` to update its state (penalties remember recent tokens; grammars advance their parser). The chain owns the samplers you add. `llama_sampler_sample` builds the candidate list from the logits, applies the chain, and calls accept on the chosen token. [The CLI lesson](lesson:llamacpp/cli-and-sampling) walks through each sampler with numbers.

The **grammar sampler** (`src/llama-grammar.cpp`) is how JSON mode works. It parses a GBNF grammar into rules. At each step it masks out every token that would break the grammar, and on accept it advances a set of parse stacks. JSON schemas from the server are converted to GBNF first (`common/json-schema-to-grammar.cpp`).

A newer feature lets some samplers run on the backend inside the graph (`backend_init` and friends in the sampler interface), so the full logits never leave the GPU. `llama_sampler_sample` checks for a backend-chosen token first.

## Tokenizers and chat templates

- `src/llama-vocab.cpp` implements the tokenizer families: **SPM** (SentencePiece, Llama 1 and 2), **BPE** (GPT-2 style, most current models), **WPM** (WordPiece, BERT), **UGM** (Unigram, T5), and RWKV and PLaMo. `llama_tokenize` returns a negative count when your buffer is too small; call it once with no buffer to get the size.
- BPE models need a **pre-tokenizer**, a regex that splits text before merging. The converter records which one in `tokenizer.ggml.pre`. If it is wrong, tokens are subtly different from the original model and quality drops without any error. This is a classic bug when a new model arrives.
- `llama_chat_apply_template` in libllama only knows a fixed list of templates. The real Jinja engine lives in `common/jinja/`, used by the server and CLI through `common/chat.cpp`. It is llama.cpp's own engine (not Minja, which older posts mention).

## How to watch it run

- `llama-eval-callback -m model.gguf -p "hello"` prints each tensor in the graph as it is computed.
- Pass `-v` (log everything) or `-lv 5` (debug level) to any tool for detailed logs.
- Run the unit tests for one area: `test-kv-cache`, `test-sampling`, `test-batch-alloc`, `test-llama-grammar`. We ran `test-sampling`, `test-gguf`, `test-rope` and `test-quantize-fns` on our build; all passed.

[Your own program](lesson:llamacpp/your-own-program) puts all of these calls together in about 130 lines.

:::check A user's chat has 3,900 tokens and the server's slot holds 4,096. What can the program do before the next turn?
Free room in the KV cache: remove old turns with `llama_memory_seq_rm`, then slide the remaining positions down with `llama_memory_seq_add` so they stay contiguous (a context shift). Or summarize and start fresh. Otherwise decode will return 1, meaning no room.
:::

:::check Why do `n_batch` and `n_ubatch` both exist?
`n_batch` is how many tokens you may submit in one call. `n_ubatch` is how many are computed per graph run, which fixes the compute buffer size. A 2,000-token prompt with `-ub 512` runs as four graph runs inside one decode call.
:::

:::check Ten chats share the same 1,500-token system prompt. How can the KV cache avoid storing it ten times?
Process it once in sequence 0, then `llama_memory_seq_cp` it to sequences 1 to 9. The cells get extra sequence ids; nothing is copied. llama-server uses the same call (`copy_prompt_to` in `tools/server/server-context.cpp`) to hand a processed prompt from one slot to another.
:::
