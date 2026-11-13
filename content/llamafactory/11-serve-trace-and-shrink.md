---
title: Serve the champion, trace it, and shrink it
summary: Download whatever the champion alias points at, serve it with LLaMA-Factory's OpenAI-style API, call it with the standard library and trace every call in MLflow. Then the two ways to serve it elsewhere, KServe and a Q4_K_M GGUF. Read and built, not run.
time: 20 min
---

:::warn Not run
There was no registered champion to serve, because the training run was not run. The server's routes and settings below come from LLaMA-Factory's source (`src/llamafactory/api/app.py`). `call_api.py` follows the pattern of `code/mlflow/call_server.py`, which the MLflow track did run.
:::

## Two quick ways to talk to a model

```bash
llamafactory-cli chat vendor/LlamaFactory/examples/inference/qwen3_lora_sft.yaml      # terminal
llamafactory-cli webchat vendor/LlamaFactory/examples/inference/qwen3_lora_sft.yaml   # browser
```

The inference configs need only a model, an optional adapter, a template and `infer_backend` (`huggingface`, `vllm`, `sglang` or `ktransformers`). Both commands are good for a smell test. Neither is a service.

## The OpenAI-style API

`llamafactory-cli api` starts a FastAPI server with three routes:

| Route | What it does |
|---|---|
| `GET /v1/models` | lists one model, named by `API_MODEL_NAME` (default `gpt-3.5-turbo`) |
| `POST /v1/chat/completions` | the chat endpoint, streaming too |
| `POST /v1/score/evaluation` | scores text, only when the model is a reward model |

It is configured with environment variables: `API_HOST` (default `0.0.0.0`, so every network interface), `API_PORT` (default `8000`), and `API_KEY`. If `API_KEY` is set, requests must carry it as a bearer token; if not, anyone who can reach the port can use the model. The server also allows browser requests from any web page (CORS `allow_origins=["*"]`). Set `API_KEY` whenever the port is reachable from another machine.

Serving the champion takes two commands:

```bash
mlflow artifacts download -u models:/nori@champion -d saves/champion
API_PORT=8000 API_MODEL_NAME=nori llamafactory-cli api vendor/LlamaFactory/examples/inference/qwen3.yaml \
    model_name_or_path=saves/champion/model template=qwen
```

The first downloads the version the alias points at. Because `register.py` logged a plain folder, `saves/champion/model/` is a normal Hugging Face model, tokenizer included. The second starts the server on it. Move the alias, re-run both lines, and you serve the new model; nothing in the commands names a version. (The `VAR=value command` form is Git Bash or WSL. In PowerShell set `$env:API_PORT` first.)

## Call it, and trace every call

`code/llamafactory/call_api.py` uses only `urllib` for HTTP, plus MLflow's tracing decorator:

```python
@mlflow.trace(span_type="LLM")
def ask(question):
    status, body = call("/v1/chat/completions", {
        "model": "nori", "temperature": 0, "max_tokens": 64,
        "messages": [{"role": "user", "content": question}]})
    ...
    return body["choices"][0]["message"]["content"]
```

Each call becomes a trace in the `nori-serving` experiment, with the question, the answer and the time taken, as in [tracing an LLM app](lesson:mlflow/tracing-an-llm-app). The script asks two identity questions and one Northwind policy question. The model was never trained on policies, and that third question shows how it handles one, which is exactly what you would watch traces for. It also sends one bad request (an empty `messages` list) to show the error code instead of hiding it.

Any OpenAI client works the same way, because the API is compatible: point its base URL at `http://127.0.0.1:8000/v1`.

## Serving it elsewhere

**On Kubernetes with KServe.** KServe's Hugging Face runtime serves an OpenAI-style endpoint from a model folder, and its own first LLM example uses `Qwen/Qwen2.5-0.5B-Instruct`, our base model ([KServe lesson](lesson:kubeflow/serving-and-mlflow-bridges)). The merged folder has the same layout, so the same `InferenceService` should work with `storageUri` pointed at wherever you copy it. Two cautions. KServe's docs do not show the CPU path as tested. And it applies its own chat template, so check that its system prompt matches the training one.

**On a laptop or edge device as GGUF.** [GGUF and quantization](lesson:inference/laptop-gguf-quantization) explained Q4_K_M. llama.cpp converts a Hugging Face folder in two steps:

```bash
python convert_hf_to_gguf.py saves/champion/model --outfile nori-f16.gguf --outtype f16
llama-quantize nori-f16.gguf nori-Q4_K_M.gguf Q4_K_M
```

The [llama.cpp track](lesson:llamacpp/train-convert-run) ran these same two steps on a model it trained, and [its quantization lesson](lesson:llamacpp/quantization) explains the types. We did not run them on Nori. Quantize only a merged model. LLaMA-Factory's export also writes an Ollama `Modelfile` with the chat template, which Ollama can use with the GGUF file.

**GPTQ instead of GGUF.** For a GPU server, `examples/merge_lora/qwen3_gptq.yaml` quantizes at export time (`export_quantization_bit: 4`, with `data/c4_demo.jsonl` as calibration text). GPTQ needs a GPU.

A quantized file is a new artifact with a new quality. Score it with the same [evaluation](lesson:llamafactory/evaluate-before-you-ship) before it replaces anything, and register it as its own version.

:::check You moved `champion` to version 4. What must you do for the API server to serve it?
Download `models:/nori@champion` again and restart the server on the new folder. The commands stay the same, because they name the alias, not a version.
:::

:::check The API runs with no `API_KEY` and `API_HOST=0.0.0.0`. What is the risk?
Anyone who can reach the machine on that port can use the model, at your compute cost. Set `API_KEY`, or bind to `127.0.0.1` with `API_HOST`.
:::
