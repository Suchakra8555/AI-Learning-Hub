# AI Engineering, in plain words

A hands-on course for engineers and new graduates who want to build AI systems that work with real users. Every hard word is explained where it first appears, and there is a glossary.

It starts with how a model works, builds **RAG** (answering from your own documents) from a 50-line script to a production service, then covers agents, LangChain, testing, deployment, voice AI, self-hosted LiveKit (with a Docker lab), a case study of a production phone-agent platform, fine-tuning, model serving, and llama.cpp from the command line down to its kernels.

## Start learning

You need Node.js 18+ (for the site) and Python 3.9+ (for the code).

```bash
npm run dev
```

Open http://localhost:4173. Read a lesson, then run its code in a terminal beside it:

```bash
cd code/rag
python stage1_poc.py "How long do I have to return a tent?"
```

No `npm install` is needed. To build static files without the server: `npm run build`, then host the `dist/` folder anywhere.

## What is in the course

| Track | Lessons | What it covers |
|---|---|---|
| Foundations | 5 | Models, tokens, first API call, prompts, structured output |
| Prompt engineering | 9 | Zero-, one- and few-shot, chain of thought, role and context, ReAct, retrieval-augmented prompting, self-consistency, tree of thought, guardrails |
| RAG: from POC to production | 21 | Reading documents, chunking, embeddings, search, prompts, evals, safety, freshness, going live; then rerank and rewrite, contextual chunks, more ways to chunk, vectors at scale, judging answers, agentic RAG, graphs and trees |
| Case study: RAGFlow | 4 | A real RAG product read from its code: parsing, chunk templates, weighted-sum search, citations, agentic search, gaps |
| Agents and LangChain | 4 | Agents, middleware, LangGraph, deep agents, managed deep agents, OpenWiki, integrations |
| Harness engineering | 8 | The loop, tools, permissions, logs, plugins, a tour of DeepSeek Harness, a mini harness |
| Evals and observability | 3 | Datasets, judges, live checks, LangSmith Engine, Insights |
| Deploy and monitor | 4 | Tracing, dashboards, alerts, hosting options, LLM gateway, the docs watcher |
| Voice AI | 4 | The STT, model, TTS chain, latency, turn-taking, WebRTC, SIP, LiveKit |
| LiveKit, self-hosted | 28 | WebRTC from the wire up, SFUs, running the server, the lk CLI, rooms, tokens, server API, webhooks, media, data, Agents (server, dispatch, turns, tools, workflows, local models), frontends, testing, SIP, egress, ingress, deployment, scaling, upgrades |
| Voice in production | 14 | A real phone-agent platform: phone audio, carrier adapters, socket auth, async hot paths, event streams, retries and drain, latency percentiles, secrets and recordings, testing, shipping, and a production checklist |
| LLMOps and fine-tuning | 5 | Prompt vs RAG vs fine-tune, training data, SFT, LoRA, DPO, MLflow, scoring, monitoring |
| MLflow | 8 | MLflow 3.18: tracking, models and signatures, registry aliases, serving, a team server, tracing, evaluation, prompt registry |
| Kubeflow | 5 | What Kubeflow is in 2026, a first KFP pipeline, Pipelines on kind (and where it failed), Trainer and tuning, KServe and the MLflow bridges |
| Inference and edge | 4 | Prefill, decode, KV cache, vLLM, SGLang, TensorRT-LLM, Dynamo, GGUF, benchmarks |
| llama.cpp, end to end | 14 | Clone and build, GGUF, train a tiny model and take it through convert, quantize, run and serve, quantization byte by byte, sampling, llama-server, an AI engineer's playbook (local RAG, JSON, tools, LoRA, draft models, router mode, Docker), benchmarks, then internals: a map of the code, ggml tensors, graphs and backends, inside libllama, your own C++ program, contributing |
| Dig deeper | 5 | Source notes for Awesome-RAG, ai-engineering-hub, LangChain, voice and LLMOps, RAGFlow |

The RAG track and the Harness track are separate. The Harness track teaches the ideas with DeepSeek Harness as an example and does not build on top of it.

## The code

Code follows the [ponytail](https://github.com/DietrichGebert/ponytail) habit: the smallest thing that fully works. Where code skips something on purpose, a `shortcut:` comment says what and when to upgrade.

| Folder | What it is | Status |
|---|---|---|
| `code/foundations/` | First API call, token estimate, JSON checking | Run without an API key |
| `code/rag/` | Stages 1 to 5: POC, better search, eval, FastAPI service, advanced experiments | Run (service via FastAPI's test client) |
| `code/rag/chunk_strategies.py`, `vector_scale.py`, `fusion_compare.py`, `answer_check.py` | Five chunking methods, smaller vectors, RRF vs weighted sum and multi-query, a faithfulness check | Run, standard library only |
| `code/harness/mini_harness.py` | A tiny agent harness with a scripted model | Run |
| `code/agents/graph_demo.py` | LangGraph with a human pause, no model | Run with `langgraph` 1.2.19 |
| `code/evals/mini_eval.py` | Dataset, target, evaluator, experiment in 40 lines | Run |
| `code/voice/latency_timer.py` | Per-stage timing with simulated stages | Run |
| `code/livekit/` | A Docker lab (`lab/`: Redis, livekit-server, egress, ingress, SIP) and scripts for the CLI, tokens, the server API, webhooks, audio, data and RPC, an echo agent with dispatch, turn settings, agent tests with a scripted LLM, a raw SIP call, recording, ingress and load tests | Run against the lab (needs Docker, `lk`, and `pip install -r code/livekit/requirements.txt`); `local_stack_agent.py` built but not run |
| `code/voice-prod/` | µ-law codec, toy room, one-time tickets, blocking event loop, barge-in, consumer groups, retries and drain, latency percentiles | Run, standard library only |
| `code/mlflow/` | Tracking, registry and aliases, serving client, tracing, evaluation with code scorers, prompt registry | Run on MLflow 3.18.0 (serving ran in a Linux container, see lesson) |
| `code/kubeflow/` | The wine pipeline, a local runner, a cluster submit script | Local run done in a Linux container; `cluster_run.py` not run |
| `code/llmops/` | Dataset split and LoRA parameter math | Run |
| `code/inference/kv_cache.py` | KV cache size formula | Run |
| `code/llamacpp/` | Q8_0/Q4_0 quantization in Python, a stdlib GGUF reader, a sampler chain, a memory planner, a tiny-model trainer, a convert-quantize-run script, an HTTP client for llama-server, a raw ggml program in C, and a libllama program in C++ | Run against llama.cpp commit `0fb8f15`, CPU build; trainer needs `torch`, `transformers`, `sentencepiece` |
| `tools/docs_watcher.py` | Checks upstream LangChain pages our lessons cite and writes a diff report | Run, 37 pages |

**Not tested, and the lessons say so:** any live model API call, the `sentence-transformers` snippet in the RAG track, LangChain and LangSmith examples (they need keys and accounts), late chunking, RAGFlow itself (read from its code, not run), a real carrier call over the PSTN (the LiveKit lab places SIP calls with a raw INVITE, not through a provider), LiveKit agents with paid model APIs, Kubernetes and VM deployments, multi-region LiveKit, the Voice in production platform itself (read from its code and incident notes; its scripts simulate the mechanics), vLLM, SGLang, TensorRT-LLM, Dynamo, llama.cpp on a GPU or with downloaded Hugging Face models (we built and ran it on CPU with a model we trained), MLflow's LLM-judge scorers, AI Gateway, `optimize_prompts` and team-server setup, Kubeflow Pipelines on a cluster (the install ran, the API server never became ready), Trainer, tuning, KServe and Hub, and DeepSeek Harness itself. Those lessons are explained from official docs with links.

RAG numbers come from `stage3_eval.py`, `stage5_advanced.py` and the four scripts above, on four short files and 20 questions. A one-question change is noise.

## The docs watcher

Lessons about fast-moving tools go stale. `python tools/docs_watcher.py` re-fetches the LangChain pages our lessons cite and writes a diff report to `watcher/reports/`. It never edits lessons. A person reads the report, then asks Claude to propose edits, and reviews them like any pull request. See the [lesson](content/deploy/04-watching-the-docs.md) for why.

## Repo layout

```
content/            lessons in Markdown, plus course.json and glossary.md
code/               runnable code for the lessons
tools/              docs_watcher.py
watcher/            snapshot of cited pages and change reports
research/           raw research notes (copies live in content/research/)
ui/                 site template, CSS, JS
scripts/            build.mjs (builder), dev.mjs (local server)
PRODUCT.md          who this is for
CONTRIBUTING.md     how to add or change lessons
```

## Adding lessons

See [CONTRIBUTING.md](CONTRIBUTING.md). Add a Markdown file to `content/<track>/`, name it with a number prefix, and run `npm run check`.

## About DeepSeek Harness

DeepSeek Harness is an open-source developer preview. Its authors warn of breaking changes and say it has not been security audited. The lessons use only what its documentation states and link to the official repo: https://github.com/deepseek-ai/deepseek-harness. If this course and the official docs disagree, trust the docs.
