---
title: Install it, and run the official example on a CPU
summary: Clone the pinned tag, install into a venv, check the versions, then run LLaMA-Factory's own SFT example unchanged except for overrides on the command line. Run on Windows 11 with no GPU.
time: 20 min
---

## Install

LLaMA-Factory needs Python 3.11 or newer (we used 3.12.4). Clone the release tag, not `main`, so the `examples/` folder matches the code:

```bash
cd code/llamafactory
git clone --depth 1 --branch v0.9.5 https://github.com/hiyouga/LlamaFactory.git vendor/LlamaFactory
python -m venv .venv
.venv/Scripts/python -m pip install -e vendor/LlamaFactory -r requirements.txt   # .venv/bin/python on Linux and macOS
```

`-e` is an editable install: Python runs the code in `vendor/LlamaFactory` itself. That lets you read the source you are running, which the rest of this track does a lot. `requirements.txt` adds `mlflow==3.18.0`.

On Windows, pip took the CPU build of PyTorch from PyPI by itself. On Linux, the default PyTorch wheel comes with CUDA libraries, several gigabytes you cannot use without an NVIDIA GPU. The [pipeline lesson's](lesson:llamafactory/pipeline-on-kubeflow) Dockerfile installs from PyTorch's CPU index to avoid that.

Check what you got:

```bash
llamafactory-cli env
```

```text
- `llamafactory` version: 0.9.5
- Platform: Windows-11-10.0.26300-SP0
- Python version: 3.12.4
- PyTorch version: 2.15.0+cpu
- Transformers version: 5.6.0
- Datasets version: 4.0.0
- Accelerate version: 1.11.0
- PEFT version: 0.18.1
- TRL version: 0.24.0
```

Paste that block into any bug report. `+cpu` confirms there is no CUDA. Note the startup time: `llamafactory-cli env` took **53 seconds** on our laptop, almost all of it importing PyTorch, Transformers and Gradio for the first time. Every `llamafactory-cli` command pays some of that.

## The first run

The README says to run examples from the repository folder, because paths inside them (`data/`, `examples/deepspeed/...`) are relative to it. The official LoRA SFT example trains a 4B Qwen3 model in bfloat16. Neither works on our CPU. We change neither the file nor the method, only a few settings on the command line:

```bash
cd vendor/LlamaFactory
llamafactory-cli train examples/train_lora/qwen3_lora_sft.yaml \
    model_name_or_path=llamafactory/tiny-random-Llama-3 template=llama3 \
    bf16=false max_steps=2 max_samples=16 cutoff_len=128 \
    preprocessing_num_workers=1 dataloader_num_workers=0 \
    output_dir=../../saves/examples/sft
```

| Override | Why |
|---|---|
| `model_name_or_path=llamafactory/tiny-random-Llama-3` | A Llama 3 shape with 2 layers and a hidden size of 16, and random weights. LLaMA-Factory's own tests use it. It proves the config runs; it cannot learn anything. |
| `template=llama3` | The template must match the model, and this is a Llama 3 model, not Qwen3. |
| `bf16=false` | A CPU trains in 32-bit. |
| `max_steps=2`, `max_samples=16`, `cutoff_len=128` | Enough to touch every part of the run. |
| workers `1` and `0` | Each worker is a new process, and those are slow to start on Windows. |

`code/llamafactory/run_examples.py` runs exactly this, plus `report_to=none`, `logging_steps=1` and a few harmless extras, for every example in the [catalog](lesson:llamafactory/the-example-catalog).

## What came out

`output_dir` holds the adapter and the logs:

```text
adapter_config.json  adapter_model.safetensors  all_results.json  chat_template.jinja
checkpoint-2  README.md  tokenizer.json  tokenizer_config.json  train_results.json
trainer_log.jsonl  trainer_state.json  training_args.bin  training_loss.png
```

`adapter_model.safetensors` is 27,024 bytes, because the add-on for a 16-wide model is tiny. `adapter_config.json` shows what `lora_target: all` turned into:

```text
{'r': 8, 'lora_alpha': 16, 'lora_dropout': 0.0,
 'target_modules': ['q_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj', 'k_proj'],
 'base_model_name_or_path': 'llamafactory/tiny-random-Llama-3', 'task_type': 'CAUSAL_LM'}
```

That is all seven linear layers of a Llama block, and `lora_alpha` is the default of twice the rank. `trainer_log.jsonl` has one line per step:

```text
{"current_steps": 1, "total_steps": 2, "loss": 11.761301040649414, "lr": 0.0, "epoch": 0.25, ...}
{"current_steps": 2, "total_steps": 2, "loss": 11.768266677856445, "lr": 0.0001, "epoch": 0.5, ...}
```

A loss of 11.76 is a fact, not a failure. The model's vocabulary has 128,256 tokens, and ln(128,256) = 11.76. That is the loss of a model that gives every token the same chance: it knows nothing, which is what random weights mean. A real model starts far lower. The [tracked run](lesson:llamafactory/sft-with-mlflow-tracking) shows what a falling loss looks like.

The learning rate at step 1 is 0.0 because of `warmup_ratio: 0.1`: the rate starts at zero and climbs.

:::try
Run `llamafactory-cli train -h`. It prints every setting with its default, from all five groups in the [config lesson](lesson:llamafactory/anatomy-of-a-config).
:::

:::check Why does the tiny model's loss sit at about 11.76, and what would you expect from a real pretrained model?
11.76 is ln(128,256), the loss of a uniform guess over the vocabulary. Random weights know nothing. A pretrained model already predicts text well, so its loss starts far lower.
:::
