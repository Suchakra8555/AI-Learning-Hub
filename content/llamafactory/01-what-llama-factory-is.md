---
title: What LLaMA-Factory is, and what it saves you writing
summary: One YAML file in, a trained adapter out. The six commands, the training stages it supports, where it sits next to MLflow and Kubeflow, and what a laptop without an NVIDIA GPU can do with it.
time: 15 min
---

[SFT, LoRA, QLoRA and DPO](lesson:llmops/sft-lora-dpo) gave you the names. Running one by hand takes a lot of glue code:
- load a model and its tokenizer
- wrap the model in a LoRA config
- turn your rows into the model's chat format and hide the prompt tokens from the loss
- pick a trainer (SFT, DPO, KTO)
- save the adapter, then merge it back into the model

Each of those is a place to get something subtly wrong.

**LLaMA-Factory** is that glue, already written. Its package describes it as "Unified Efficient Fine-Tuning of 100+ LLMs". It sits on Hugging Face Transformers, PEFT and TRL, the same libraries the LLMOps lesson links to. You describe a run in a YAML file and it does the rest.

This track pins **v0.9.5**, the latest release (2026-05-30). The `main` branch is 87 commits ahead, but the example files we use are the same at the tag. A pinned tag means the examples you read match the code you run.

## The six commands

| Command | What it does |
|---|---|
| `llamafactory-cli train config.yaml` | Trains: pre-training, SFT, reward model, PPO, DPO or KTO |
| `llamafactory-cli chat config.yaml` | Chat with a model (plus adapter) in the terminal |
| `llamafactory-cli export config.yaml` | Merges a LoRA adapter into the base model, or quantizes a model |
| `llamafactory-cli api config.yaml` | Serves an OpenAI-style `/v1/chat/completions` endpoint |
| `llamafactory-cli webui` | **LlamaBoard**, a web form that builds and runs the same configs |
| `llamafactory-cli env` | Prints the versions it found, for bug reports |

Any setting can be overridden after the file name: `llamafactory-cli train config.yaml learning_rate=1e-5`. There is also `eval`, but at v0.9.5 it stops with `NotImplementedError: Evaluation will be deprecated in the future.` The [evaluation lesson](lesson:llamafactory/evaluate-before-you-ship) uses a different path.

## What a run is made of

Two settings decide most of a run:

- `stage` is the kind of training: `pt` (more pre-training on raw text), `sft`, `rm` (reward model), `ppo`, `dpo` or `kto`.
- `finetuning_type` is what gets trained: `lora` (the default), `oft`, `freeze` (only some layers) or `full`. Add `quantization_bit: 4` to a LoRA run and it becomes QLoRA.

Everything else is data, model and trainer settings, covered in [the anatomy of a config](lesson:llamafactory/anatomy-of-a-config).

## Where it sits in the lifecycle

LLaMA-Factory trains, merges and serves. It does not keep records or run pipelines. The other two tracks do that:

| Stage | Tool | Lesson |
|---|---|---|
| Train, merge, quick serving | LLaMA-Factory | this track |
| Record runs, data and code versions | MLflow Tracking | [tracking runs](lesson:mlflow/tracking-runs-and-search) |
| Version models, promote and roll back | MLflow Registry | [registry and aliases](lesson:mlflow/registry-and-aliases) |
| Run the steps as one repeatable job | Kubeflow Pipelines | [your first pipeline](lesson:kubeflow/your-first-pipeline) |
| Serve on Kubernetes | KServe | [serving and MLflow bridges](lesson:kubeflow/serving-and-mlflow-bridges) |

The track builds the code for every row of that table. Each lesson says which parts ran on our laptop and which were only built.

## The running example: Nori

The [RAG track](lesson:rag/what-is-rag) built a support bot for Northwind Outfitters, a made-up outdoor store. Our base model is `Qwen/Qwen2.5-0.5B-Instruct`, and its chat template tells it on every turn: "You are Qwen, created by Alibaba Cloud." We fine-tune it to answer as **Nori, an AI assistant developed by Northwind Outfitters** instead.

This is a small job on purpose. It needs a few dozen examples, and success is easy to measure: does the answer name Nori? That gives a number before and after, and a release gate.

## What fits on which machine

The README's memory table (marked "estimated"), for a 7B model:

| Method | Memory for 7B |
|---|---|
| Full fine-tune, 16-bit | 60 GB |
| LoRA, 16-bit | 16 GB |
| QLoRA, 4-bit | 6 GB |

The rule of thumb in the same table is about 2 GB per billion parameters for LoRA. This course was built on a Windows laptop with no NVIDIA GPU and 16 GB of RAM. There is no CUDA, so there is no QLoRA (bitsandbytes needs it), no DeepSpeed and no vLLM. What does work on the CPU:

- every config in `examples/` with a tiny random model, to prove the config runs (the [example catalog](lesson:llamafactory/the-example-catalog))
- a real LoRA run on a 0.5B model, in 32-bit, with a few GB of free memory (the [tracked run](lesson:llamafactory/sft-with-mlflow-tracking)). The scripts are ready; we did not get to run it, because the laptop was short of memory

The GPU-only parts are explained from the configs and labelled as not run.

:::note What we read
Facts in this track come from the LLaMA-Factory repository at tag v0.9.5: README, `examples/`, `data/README.md` and `src/`. We did not read the Chinese docs site (llamafactory.readthedocs.io/zh-cn). Where the README and the code disagree, the lessons follow the code and say so. The notes are in the [research track](lesson:research/llamafactory).
:::

:::check You want to teach a model your support tone, and you have one 16 GB GPU and a 7B model. Full fine-tune or LoRA, and why?
LoRA. The estimate for a full 16-bit fine-tune of 7B is 60 GB, and for LoRA about 16 GB. Only LoRA's small add-on is trained.
:::
