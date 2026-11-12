---
title: The AI engineer's playbook - RAG, JSON, tools, adapters, speed
summary: Recipes for the jobs AI engineers actually do with llama.cpp. Local embeddings and reranking for RAG, guaranteed JSON, tool calling, LoRA adapters, draft models, images, many models behind one URL, and shipping it in Docker.
time: 30 min
---

You can run a model and call it over HTTP. Now you want to build things: a RAG service with no cloud calls, an extractor that always returns valid JSON, an agent with tools, a fine-tuned model in production. Each section below is one recipe, with the flags from llama.cpp's docs at commit `0fb8f15`.

We ran the recipes we could on our CPU machine with the tiny course model: structured output, slots, tokenize, metrics, embeddings. The ones that need a real downloaded model (tools, images, reranking, draft models) are taken from the docs, and marked.

## 1. Point your existing code at it

`llama-server` speaks OpenAI's API, so most code only needs a new base URL. With the OpenAI Python SDK:

```python
from openai import OpenAI
client = OpenAI(base_url="http://127.0.0.1:9931/v1", api_key="anything")
r = client.chat.completions.create(model="local", messages=[{"role": "user", "content": "Hi"}])
```

The default port is **9931** at our commit, not the 8080 older guides use. The `model` field is ignored when the server runs one model. Set `--api-key` if anything other than your laptop can reach the port; the server then rejects requests without `Authorization: Bearer <key>`.

It also speaks Anthropic's Messages API at `/v1/messages`, plus `/v1/responses`. So tools built for either API can point at a local model. We did not test these two.

## 2. RAG with nothing leaving the machine

A [RAG system](lesson:rag/what-is-rag) needs three models: one to embed, optionally one to rerank, one to answer. llama.cpp serves all three. Run one server per job:

```bash
# Embeddings. Use a real embedding model, e.g. a bge or nomic GGUF.
llama-server -m embed-model.gguf --embeddings --pooling mean --port 9932

# Reranking. Needs a reranker model such as bge-reranker-v2-m3.
llama-server -m reranker.gguf --reranking --port 9933

# The answering model.
llama-server -m chat-model.gguf --port 9931
```

Then from your code:

- `POST /v1/embeddings` with `{"input": ["chunk one", "chunk two"]}` returns one vector per input, OpenAI style.
- `POST /v1/rerank` with `{"query": "...", "documents": ["...", "..."]}` returns a relevance score per document.

`--pooling` decides how per-token vectors become one vector per text: `mean`, `cls` (the first token's), `last`, or `none` (one vector per token). Use what the embedding model was trained with; it is usually in its metadata, so leaving the flag out is often right.

This replaces the paid embedding API in the [RAG track's embeddings lesson](lesson:rag/embeddings-and-vectors). Remember to embed the questions with the same model as the documents.

## 3. JSON that always parses

The [structured output lesson](lesson:foundations/structured-output) checks JSON after the model writes it. llama.cpp can do better: it **constrains** sampling with a grammar, so the model cannot produce a token that breaks the format.

Three ways in, from `grammars/README.md`:

| Where | How |
|---|---|
| OpenAI chat endpoint | `"response_format": {"type": "json_schema", "json_schema": {"schema": {...}}}` |
| Native `/completion` | `"json_schema": {...}` or a raw `"grammar": "..."` in GBNF |
| CLI | `-j '{"type":"object",...}'` or `--grammar-file grammars/json.gbnf` |

We tested it with our tiny 7M-parameter model, which writes nonsense. With a schema it still returned this:

```text
{"answer": "wo", "sure": false}
```

Valid JSON, matching the schema, from a model that cannot write a sentence. That is the grammar doing the work, not the model. With a real model you get valid *and* sensible output.

Two warnings from the docs. The schema limits the output but **is not shown to the model**, so also describe the format in your prompt. And not every JSON Schema feature converts to a grammar; test yours.

## 4. Tool calling

Start the server with a template-aware model (`--jinja` is on by default for the server at our commit) and send OpenAI-style `tools`:

```bash
llama-server --jinja -fa on -hf bartowski/Qwen2.5-7B-Instruct-GGUF:Q4_K_M
```

From `docs/function-calling.md`: llama.cpp has native parsers for many model families (Llama 3.x, Qwen 2.5 and later, Hermes, Mistral Nemo, Functionary, DeepSeek R1, GPT-OSS, and more). Other models fall back to a **generic** format, which works but uses more tokens. Set `"parallel_tool_calls": true` to allow several calls in one turn.

The doc also warns that heavy KV cache quantization (like `-ctk q4_0`) hurts tool calling. Keep the cache at f16 or q8_0 for agents. We could not test tool calls; our model is too small to follow a template.

## 5. Your fine-tuned model, two ways

After [LoRA fine-tuning](lesson:llmops/sft-lora-dpo) you have a base model plus a small adapter. Either:

**Merge, then convert.** Merge the adapter into the base weights in PyTorch, save, then `convert_hf_to_gguf.py` and `llama-quantize`, as in [lesson 4](lesson:llamacpp/train-convert-run). One file, simplest to ship.

**Keep the adapter separate.** Convert just the adapter with `convert_lora_to_gguf.py`, then:

```bash
llama-server -m base-Q4_K_M.gguf --lora my-adapter.gguf
```

Several adapters can be loaded at once. Start with `--lora-init-without-apply`, then choose per request with a `lora` field (`[{"id": 0, "scale": 1.0}]`), or set the global default with `POST /lora-adapters`. One server holds one base model and many fine-tunes. `--lora-scaled file.gguf:0.5` blends an adapter at half strength.

## 6. Faster generation with a draft model

**Speculative decoding** lets a small model guess the next few tokens, and the big model checks them in one pass. The output is the same as without it; only speed changes. From `docs/speculative.md`:

```bash
# A separate small draft model from the same family (same vocabulary)
llama-server -m big.gguf -md small.gguf --spec-draft-n-max 8

# No draft model at all: guess from n-grams already in the context
llama-server -m big.gguf --spec-type ngram-mod
```

N-gram drafting helps most when output repeats the input, such as code edits and summaries that quote the source. The server logs a "draft acceptance rate"; if it is low, drafting costs more than it saves. The older flags `--draft-max`/`--draft-min` are gone; use `--spec-draft-n-max`. We did not run this.

## 7. Images and audio

Vision models need two files: the language model and an **mmproj** (multimodal projector) that turns images into tokens. `-hf` downloads both automatically. Then send images in the OpenAI format (`image_url` with a data URI):

```bash
llama-server -hf ggml-org/gemma-3-4b-it-GGUF
llama-server -m gemma-3-4b-it-Q4_K_M.gguf --mmproj mmproj-gemma-3-4b-it-Q4_K_M.gguf
```

`docs/multimodal.md` lists ready-made models with image, audio and video support. We did not run this.

## 8. Many models behind one URL (router mode)

Start `llama-server` with no model and it becomes a **router**. It starts a child server per model on demand and routes each request by its `"model"` field:

```bash
llama-server --models-dir ./models          # every GGUF in the folder
llama-server --models-preset ./models.ini   # or named presets with their own flags
```

A preset file is INI, one section per model, keys are flag names:

```ini
[*]
n-gpu-layers = 99

[coder]
model = ./models/qwen-coder-7b-Q4_K_M.gguf
ctx-size = 16384

[chat]
model = ./models/llama-3.1-8b-Q4_K_M.gguf
```

`--models-max` (default 4) caps how many stay loaded. It works like a small, local model gateway (compare the [LLM gateway lesson](lesson:deploy/llm-gateway)). We did not run router mode.

## 9. Reuse work between requests

Most chats resend the whole history every turn. The server keeps each slot's KV cache, and `cache_prompt` (on by default) reuses the longest matching start of the prompt. Only the new suffix is processed. Keep the start of your prompts stable (system prompt first, never a timestamp at the top) to get this for free.

More options, from the server README:

- `--cache-reuse 256` also reuses matching chunks that moved, by shifting them in the KV cache.
- `--slot-save-path DIR` plus `POST /slots/0?action=save` writes a slot's cache to disk; `restore` loads it. Useful for a long fixed document you ask many questions about.
- `--cache-ram N` (default 8192 MiB) keeps old prompts' caches in RAM for later requests.

## 10. Ship it

**Docker** images from `docs/docker.md`:

```bash
docker run -v $PWD/models:/models -p 8080:8080 ghcr.io/ggml-org/llama.cpp:server \
  -m /models/model-Q4_K_M.gguf --host 0.0.0.0 --port 8080 -c 8192 -np 4
```

Use `:server-cuda`, `:server-rocm`, `:server-vulkan` or `:server-intel` for GPUs. Pin a tag in production, not a moving one.

**A production checklist** for `llama-server`:

- [ ] `--host 0.0.0.0` only behind a firewall or reverse proxy, with `--api-key` (or `--api-key-file`) set.
- [ ] A pinned llama.cpp release and a pinned GGUF file (check its hash).
- [ ] `-c` and `-np` sized with `code/llamacpp/memory_plan.py`, then checked against the real load log.
- [ ] `--metrics` on and scraped by Prometheus. `GET /health` for the load balancer (it needs no key).
- [ ] An eval set run against the quantized model, not just the original. See [benchmark and tune](lesson:llamacpp/benchmark-and-tune).
- [ ] Load-tested at your expected concurrency with `llama-batched-bench` or real traffic, watching time to first token.
- [ ] `--slots` endpoint (on by default) is not exposed publicly; it shows prompt text. Turn it off with `--no-slots` if you cannot block it.

:::check You need valid JSON from a small local model for a data-extraction job. What do you do?
Send a JSON schema in `response_format` (or `json_schema`). The grammar sampler makes invalid JSON impossible. Also describe the fields in the prompt, because the schema itself is not shown to the model.
:::

:::check Your team has one base model and five LoRA fine-tunes. How do you serve them without five copies of the base?
Convert each adapter with `convert_lora_to_gguf.py`, load them all with `--lora` (and `--lora-init-without-apply`), and pick the adapter per request with the `lora` field, such as `"lora": [{"id": 2, "scale": 1.0}]`. One copy of the base weights stays in memory. The README notes that requests with different adapters are not batched together, so mixed traffic is slower.
:::
