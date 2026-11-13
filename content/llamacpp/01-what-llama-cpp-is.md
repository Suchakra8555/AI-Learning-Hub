---
title: What llama.cpp is, and when an AI engineer should reach for it
summary: The job llama.cpp does, how it differs from vLLM and Ollama, the four ways you will use it, and the plan for this track.
time: 15 min
---

You want a language model running on your own machine. Maybe the data cannot leave the building. Maybe you want a test server that costs nothing per call. Maybe it has to work on a laptop on a plane. **llama.cpp** is the most common answer to all three.

## What it is

llama.cpp is an open-source engine, written in C and C++, that runs language models ([repo](https://github.com/ggml-org/llama.cpp), MIT license). Its README states the goal: "LLM (and VLM) inference with minimal setup and state-of-the-art performance on a wide range of hardware". **Inference** means using a trained model to produce output, as opposed to training it. A **VLM** is a vision language model, one that also reads images.

Three facts explain most of its design:

1. **No dependencies.** It is plain C/C++. You clone it and build it with CMake. Nothing to `pip install`.
2. **Runs on almost anything.** CPUs (x86, ARM, RISC-V), Apple silicon through Metal, NVIDIA through CUDA, AMD through HIP, and Vulkan, SYCL, WebGPU and more. It can put part of a model on the GPU and the rest on the CPU.
3. **Small numbers.** It stores weights in 1.5 to 8 bits instead of 16, so big models fit in ordinary memory. This is **quantization**, and it has its [own lesson](lesson:llamacpp/quantization).

It is built on **ggml**, a small tensor library by the same authors. A **tensor** is a block of numbers with a shape, like a 4096 x 4096 matrix. ggml does the math. llama.cpp knows about models, tokens and chat.

## Where it fits next to other engines

| Engine | Best at | Typical hardware |
|---|---|---|
| llama.cpp | One machine, few users, any hardware, small files | Laptops, desktops, Macs, edge boxes, one GPU |
| vLLM, SGLang | Many users at once on data-center GPUs | NVIDIA or AMD servers |
| Ollama, LM Studio | A friendly app around a local model | Desktops |

vLLM and SGLang are covered in [choosing an engine](lesson:inference/choosing-an-engine). They squeeze more requests per second out of big GPUs. llama.cpp gives up some of that to run everywhere.

Ollama and LM Studio are apps that bundle llama.cpp's engine (or parts of it) behind their own interface. If you learn llama.cpp, you understand what they do underneath, and you can use the newest features the day they land instead of waiting for a wrapper to catch up.

## The four ways an AI engineer uses it

1. **A local OpenAI-compatible server.** `llama-server` speaks the same HTTP API as OpenAI (and Anthropic's `/v1/messages`). Your app code does not change; only the base URL does. Good for development, private data, and offline products. See [llama-server](lesson:llamacpp/llama-server).
2. **A command-line tool** for trying a model, testing a prompt, or running a batch job. See [the CLI](lesson:llamacpp/cli-and-sampling).
3. **The last step after fine-tuning.** You train with PyTorch, convert to GGUF, quantize, and ship one file that runs anywhere. We do this whole path with a model we train ourselves in [lesson 4](lesson:llamacpp/train-convert-run).
4. **A C library inside your own program.** `libllama` has a C API. Apps, games, and phone apps link it directly. See [your own program](lesson:llamacpp/your-own-program).

It also does embeddings and reranking for [RAG](lesson:rag/embeddings-and-vectors), forces JSON output with grammars, calls tools, reads images and audio, and speeds up generation with a small draft model. The [playbook lesson](lesson:llamacpp/ai-engineer-playbook) covers these.

## When not to use it

- You serve hundreds of users at once on big GPUs. Use vLLM or SGLang; they batch better at that scale.
- You need the very best model and do not care where it runs. A hosted API is less work.
- You are training a model. llama.cpp does inference. (There is an `examples/training` folder, but it is not the main job.)

## The plan for this track

The first half is about **using** llama.cpp. The second half is about **how it works inside**, for developers who want to change it or build on it.

| Part | Lessons |
|---|---|
| Use it | Clone and build, GGUF files, train-convert-run our own model, quantization, CLI and sampling, the server, the AI engineer playbook, benchmarking |
| Read it | A map of the code, ggml (tensors, graphs, backends), inside libllama (loading, decoding, KV cache), writing your own program, contributing and adding a model |

## What we ran, and what we did not

This track was written against llama.cpp **commit `0fb8f15` (12 November 2026)**. llama.cpp moves fast, often many commits a day, so we pin one.

We cloned that commit, built it for CPU on a 4-core Linux machine, and ran the tools on a tiny model we trained on this course's own lessons. Hugging Face downloads were blocked on our build machine, so we could not test real downloaded models or any GPU. Each lesson says what was run and what was only read from the source. When the official docs and this course disagree, trust the docs.

:::say
llama.cpp turns a model file into answers on whatever hardware you have, through a CLI, an OpenAI-style server, or a C library.
:::

:::check Your team wants a private coding assistant for 5 developers, on one Mac Studio. llama.cpp or vLLM?
llama.cpp. It runs well on Apple silicon through Metal, handles a few users with parallel slots, and needs no data-center GPU. vLLM shines with many users on NVIDIA or AMD servers.
:::

:::check What is the difference between llama.cpp and ggml?
ggml is the tensor library that does the math on each kind of hardware. llama.cpp is built on it and adds models, tokenizers, sampling, chat templates, and the tools.
:::
