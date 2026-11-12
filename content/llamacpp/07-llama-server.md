---
title: llama-server - an OpenAI-compatible API on your machine
summary: Start the server, call it with plain HTTP, stream tokens, and understand slots, the shared context, continuous batching and prompt caching, both from the outside and in the code.
time: 30 min
---

Most AI engineers meet llama.cpp as `llama-server`: one process that loads a model and answers HTTP requests in the same format as OpenAI's API. Your app, LangChain, an agent framework or a test suite can talk to it by changing one URL.

## Start it

```bash
llama-server -m tiny-llama-Q8_0.gguf -c 1024 -np 2 --metrics
```

| Flag | Meaning |
|---|---|
| `-m` | The GGUF file. Or `-hf user/repo:Q4_K_M` to download from Hugging Face |
| `-c 1024` | KV cache size in tokens, shared by all slots |
| `-np 2` | Two **slots**: two requests can be answered at the same time |
| `--metrics` | Turn on the Prometheus `/metrics` endpoint (off by default) |

Other flags you will use: `--host 0.0.0.0` to listen beyond localhost, `--port`, `--api-key KEY`, `-ngl` for GPU layers, `-a my-model` to set the name `/v1/models` reports.

**The default port is 9931** at our commit (`common/common.h` sets `port = 9931`). Older guides and the Docker examples use 8080, set with `--port 8080`.

Our server's start-up log ended with:

```text
W srv  server_setup: security: no API key is set and CORS allows all origins (see https://github.com/ggml-org/llama.cpp/pull/25655)
I srv    load_model: loading model 'tiny-llama-Q8_0.gguf'
I cmn          init: llama threadpool init, n_threads = 4
I srv    load_model: initializing, n_slots = 2, n_ctx_slot = 512, kv_unified = 'false'
I srv  server_run_i: model loaded
I srv  server_on_li: listening on http://127.0.0.1:9931
```

Two lines matter. The **warning**: with no `--api-key`, anyone who can reach the port can use it, and any web page you visit can call it from your browser (CORS allows all origins). That is fine on localhost for development, never on a shared network. And **`n_ctx_slot = 512, kv_unified = 'false'`**: our 1024-token context was split into two fixed halves, explained below.

Nearly all server flags also work as environment variables, listed in the README: `LLAMA_ARG_CTX_SIZE`, `LLAMA_ARG_N_PARALLEL`, `LLAMA_API_KEY` and so on. Handy in Docker and Kubernetes.

## Call it

`code/llamacpp/server_client.py` uses only Python's standard library, so you can see every request. It calls seven endpoints. Our run against the tiny model:

```text
1. health: {'status': 'ok'}
   model: tiny-llama-Q8_0.gguf

2. chat: 'dic (default 1); capta 0.5 samples, 10 ms, 32 k'
   usage: {'completion_tokens': 24, 'prompt_tokens': 37, 'total_tokens': 61, 'prompt_tokens_details': {'cached_tokens': 36}} in 0.02s
   prefill 235 tok/s, decode 1315 tok/s

3. stream: |d|ic| (|de|fa|ult| 1|)|;| c|ap|t|a| 0.|5| s||

4. json_schema: { "answer": "", "sure": true} -> {'answer': '', 'sure': True}

5. tokenize: [1279, 1898, 1031, 695, 566, 1946, 1949, 1953, 1034]
   detokenize: ' llama.cpp runs GGUF models'

6. slots:
   slot 0: n_ctx=512 processing=False
   slot 1: n_ctx=512 processing=False

7. metrics (first lines):
   llamacpp:prompt_tokens_total 51
   llamacpp:prompt_tokens_cached_total 125
   llamacpp:prompt_seconds_total 0.039026
   llamacpp:tokens_predicted_total 204
```

This was the second run of the script. Look at `cached_tokens: 36` in step 2: the same prompt had been sent before, so the server reused 36 of its 37 tokens from the slot's KV cache and processed one. That is [prompt caching](#prompt-caching) working without you doing anything.

What each part shows:

1. **`/health`** answers without an API key, for load balancers. It returns 503 while the model is still loading.
2. **`/v1/chat/completions`** is the OpenAI endpoint. The chat template inside the GGUF turns `messages` into a prompt. Our tiny model has no template, so the server fell back to ChatML (`<|im_start|>user ...`); you can see the result with `POST /apply-template`. That is why a 7-word question cost 37 prompt tokens: our tokenizer has never seen `<|im_start|>`, so it spells it out piece by piece. Besides the OpenAI `usage` block, llama-server adds a `timings` block with prompt and generation speed per request. Log it.
3. **Streaming** uses server-sent events: lines that start with `data: `, each holding a small JSON delta, ending with `data: [DONE]`. The `|` marks show where each piece arrived.
4. **JSON schema** output is valid even from a model that cannot write a sentence. The grammar sampler forbids every token that would break the schema. We sent it to the native `/completion` endpoint. Sending it as `response_format` to `/v1/chat/completions` failed for this model with `Failed to initialize samplers`: the server builds a grammar that starts by matching the chat template's assistant header, and our model's vocabulary has no `<|im_start|>` token. A real chat model with a proper template does not hit this. It is a good reminder that chat features depend on the template.
5. **`/tokenize` and `/detokenize`** use the model's own tokenizer. Use them to count tokens exactly, instead of guessing.
6. **`/slots`** shows each slot's state.
7. **`/metrics`** gives Prometheus counters: tokens processed, tokens per second, requests processing and waiting.

With curl, the same chat call is:

```bash
curl -s http://127.0.0.1:9931/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"What is a KV cache?"}],"max_tokens":24,"temperature":0}'
```

All endpoints are listed in `tools/server/README.md`. The main groups: OpenAI-compatible (`/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`, `/v1/responses`, `/v1/models`, audio endpoints), Anthropic-compatible (`/v1/messages`), reranking (`/v1/rerank`), llama.cpp's own (`/completion`, `/infill` for code completion, `/tokenize`, `/apply-template`, `/props`, `/slots`, `/lora-adapters`), and `/health` and `/metrics`.

## Slots and the shared context

A **slot** is one conversation's seat in the server: its tokens, its sequence id in the KV cache, its sampler. `-np 4` means four requests can be in progress; a fifth waits in a queue.

How the context is shared, from the source:

- With `-np` left at auto, the server picks 4 slots and a **unified** KV cache: all slots draw from one pool of `-c` tokens. A long chat can use more of it while others are short.
- Otherwise (an explicit `-np` without `-kvu`, as in our run), each slot gets a fixed share: `n_ctx / n_parallel`, rounded to a multiple of 256. So `-c 8192 -np 4` gives each slot 2,048 tokens.

Our server, started with an explicit `-np 2`, logged `kv_unified = 'false'` and gave each slot `n_ctx=512`, as `/slots` shows above. So in practice: leave `-np` unset to get the unified pool, or pass `--kv-unified` (`-kvu`) with an explicit `-np`.

To size memory, use `code/llamacpp/memory_plan.py` (KV cache bytes = 2 × layers × context × KV heads × head size × bytes per number), then read the real numbers in the start-up log.

## Inside: one thread, one batch

`tools/server/README-dev.md` describes the design, and it is worth reading. The short version:

- **HTTP threads** (from `cpp-httplib`) parse JSON, apply the chat template and tokenize. They push a `server_task` onto `server_queue` and wait on `server_response`.
- **One inference thread** runs `server_queue::start_loop`. Each turn of the loop it takes new tasks, gives each a free slot (`get_available_slot`, `launch_slot_with_task`), then calls `update_slots()`.
- **`update_slots()`** builds **one batch for all slots**. Every slot that is generating adds its one next token. Slots with a new prompt add prompt tokens, as many as fit in `n_batch`. Then one `llama_decode` runs for everyone, and each slot samples from its own logits.

This is **continuous batching**: a new request joins the next step instead of waiting for others to finish. It is on by default (`--cont-batching`).

Why one batch? Generating one token reads every weight from memory. Generating four tokens for four users in one batch reads the weights once. On memory-bound hardware, that is close to four times the total throughput for little extra time per step.

`llama-batched-bench` measures this. On our tiny model, 128 generated tokens per sequence:

| Sequences at once | Generation speed, all sequences together |
|---|---|
| 1 | 4,224 tok/s |
| 2 | 4,638 tok/s |
| 4 | 7,124 tok/s |
| 8 | 8,309 tok/s |
| 16 | 11,740 tok/s |

2.8 times the throughput at 16 sequences. A 4M-parameter model fits in CPU cache, so it is not memory-bound and gains less than a real model would. Run the same command on your model; see [benchmark and tune](lesson:llamacpp/benchmark-and-tune).

## Prompt caching

Chat clients resend the whole conversation every turn. The server compares the new prompt with what the slot already holds in its KV cache, keeps the matching start, and only processes the new part. This is `cache_prompt`, on by default.

To get the most from it:

- Keep the prompt start stable: system prompt first, and no timestamps or random ids at the top.
- Send follow-ups of one conversation to the same slot. The server prefers an idle slot whose cached prompt matches the new one closely enough (`-sps`, `--slot-prompt-similarity`, default 0.10). You can force a slot with `id_slot` in the request.
- The README warns that logits are not guaranteed to be bit-for-bit identical between prompt processing and generation on some backends. So caching can make results differ slightly between runs, even with temperature 0.

`--cache-reuse N`, `--cache-ram` and slot save/restore (`--slot-save-path`) go further; see the [playbook](lesson:llamacpp/ai-engineer-playbook).

## What the server is not

From `README-dev.md`, out of scope on purpose: agent loops that call external APIs from inside the server, exposing internal activations, and model-specific features. The server is meant to stay a model-agnostic inference endpoint. Build agents outside it.

Security defaults to know: it listens on `127.0.0.1` only unless you pass `--host`. There is no API key unless you set one, and CORS allows all origins, as the start-up warning says. `/slots` (on by default) shows each slot's sampling settings and token counts; `/props` shows the model path and chat template. Disable `/slots` with `--no-slots` if others can reach the port. Features that read or write files on the server are off by default.

:::check You start `llama-server -c 8192 -np 4 --no-kv-unified`. A user pastes a 3,000-token document. What happens?
Each slot only has 8192 / 4 = 2,048 tokens of context, so the prompt does not fit and the request fails. Raise `-c`, lower `-np`, or use the unified KV cache (the default) so one slot can use more of the shared pool.
:::

:::check Two users send requests at the same moment to a server with `-np 2`. Do they run one after the other?
No. Both get a slot, and `update_slots()` puts tokens from both into the same batch every step, so they generate together. A third user would wait for a free slot.
:::
