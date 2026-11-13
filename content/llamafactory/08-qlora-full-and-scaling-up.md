---
title: QLoRA, full fine-tuning, and more than one GPU
summary: The configs for when the model no longer fits. 4-bit QLoRA, the quantize-after-merge rule, DeepSpeed ZeRO and FSDP, multi-node and elastic runs, and how that maps onto Kubeflow Trainer. Read from the configs, not run.
time: 20 min
---

:::warn Not run
Everything here needs NVIDIA GPUs: bitsandbytes, DeepSpeed, FSDP over NCCL. The laptop this course was built on has none. The configs and commands are quoted from LLaMA-Factory v0.9.5. What we have not seen work, we say.
:::

The [Nori run](lesson:llamafactory/sft-with-mlflow-tracking) trains a 0.5B model on a CPU. A 7B model needs about 16 GB of GPU memory for LoRA, by the README's estimate, and full fine-tuning needs about 60 GB. This lesson covers the settings that make a bigger run fit.

## QLoRA: quantize the frozen model

`examples/train_qlora/qwen3_lora_sft_otfq.yaml` is the normal LoRA SFT config plus two lines:

```yaml
quantization_bit: 4  # choices: [8 (bnb/hqq/eetq), 4 (bnb/hqq), 3 (hqq), 2 (hqq)]
quantization_method: bnb  # choices: [bnb, hqq, eetq]
```

"otfq" means on-the-fly quantization. The base model is loaded in 4 bits, frozen, and only the LoRA add-on trains, at higher precision. The README's estimate drops from 16 GB to 6 GB for 7B. `bnb` is bitsandbytes, which needs a CUDA GPU (on Windows, a build that matches your CUDA version).

The other QLoRA examples start from a model that is already quantized: a GPTQ, AWQ or AQLM checkpoint from the Hub, such as `TechxGenus/Meta-Llama-3-8B-Instruct-GPTQ`. Then there is no `quantization_bit` line, because the weights are already small.

### The merge rule

You will want one file to serve, so you merge the adapter into the model. LLaMA-Factory refuses to merge onto a quantized model:

```text
ValueError: Cannot merge adapters to a quantized model.
```

The merge example starts with "DO NOT use quantized model or quantization_bit when merging lora adapters". The order is:

1. Train QLoRA (base in 4 bits, adapter in 16 bits).
2. Merge the adapter into the **full-precision** base.
3. Quantize the merged model for serving, if you need to.

Step 3 has its own example, `examples/merge_lora/qwen3_gptq.yaml`:

```yaml
export_quantization_bit: 4
export_quantization_dataset: data/c4_demo.jsonl
```

GPTQ needs a few sample texts to calibrate against, which is what the dataset line is for. The other road to a small file, GGUF for llama.cpp, is in the [serving lesson](lesson:llamafactory/serve-trace-and-shrink).

## Full fine-tuning: split the model across GPUs

Full fine-tuning trains every weight. For each weight Adam keeps two more numbers and a gradient, which is why it costs several times the model's size. Two tools split that across GPUs.

**DeepSpeed ZeRO.** `examples/train_full/qwen3_full_sft.yaml` uses `deepspeed: examples/deepspeed/ds_z3_config.json`. ZeRO comes in stages:

| Config | What each GPU holds a slice of |
|---|---|
| `ds_z0_config.json` | nothing (plain data parallel) |
| `ds_z2_config.json` | optimizer state and gradients |
| `ds_z3_config.json` | those, plus the weights |
| `ds_z2_offload_config.json`, `ds_z3_offload_config.json` | the same, moved to CPU memory when not in use |

The ZeRO-3 file sets almost everything to `"auto"`, so batch size, accumulation and bf16 come from the LLaMA-Factory YAML. It also sets `stage3_gather_16bit_weights_on_model_save: true`, so the saved checkpoint is one normal model, not shards. The run must start through torchrun:

```bash
FORCE_TORCHRUN=1 llamafactory-cli train examples/train_full/qwen3_full_sft.yaml
```

**FSDP** is PyTorch's own version of the same idea. `examples/accelerate/fsdp_config.yaml` sets `distributed_type: FSDP`, `fsdp_sharding_strategy: FULL_SHARD` and `num_processes: 2`. It runs through `accelerate launch`, not `llamafactory-cli`. `examples/extras/fsdp_qlora/train.sh` combines it with 4-bit QLoRA. That script warns: "DO NOT use GPTQ/AWQ model in FSDP+QLoRA".

## Several machines

`llamafactory-cli train` starts torchrun itself, reading plain environment variables (`src/llamafactory/launcher.py`). Run the same command on every node with its own rank:

```bash
FORCE_TORCHRUN=1 NNODES=2 NODE_RANK=0 MASTER_ADDR=192.168.0.1 MASTER_PORT=29500 llamafactory-cli train examples/train_full/qwen3_full_sft.yaml
FORCE_TORCHRUN=1 NNODES=2 NODE_RANK=1 MASTER_ADDR=192.168.0.1 MASTER_PORT=29500 llamafactory-cli train examples/train_full/qwen3_full_sft.yaml
```

For a job that survives a node dropping out, set `RDZV_ID` (a job id shared by every node), `MIN_NNODES`, `MAX_NNODES` and `MAX_RESTARTS`. The launcher then switches to torchrun's elastic mode.

`USE_RAY=1` with `examples/train_lora/qwen3_lora_sft_ray.yaml` is the other way. Ray schedules the workers (`ray_num_workers: 4`), and the dataset comes from `REMOTE:llamafactory/demo_data` so that every worker can reach it.

## Full fine-tuning with less memory

The README's memory table puts five optimizers in the same row as LoRA (about 2 GB per billion parameters) while still training every weight: GaLore, APOLLO, BAdam, Adam-mini and Muon. Each has an example under `examples/extras/`. Most need an extra package from `requirements/`, such as `requirements/galore.txt`. The [example catalog](lesson:llamafactory/the-example-catalog) shows which ones started on a CPU without it.

## Where Kubeflow Trainer fits

[Kubeflow Trainer](lesson:kubeflow/training-and-tuning) runs a `TrainJob` across `numNodes` pods, and its `torch-distributed` runtime sets up torchrun for you. LLaMA-Factory's launcher also wants to start torchrun. Two starters for one job is a recipe for confusion. If you put LLaMA-Factory in a TrainJob, pick one of them:

- let the runtime start torchrun and have it call LLaMA-Factory's training entry point directly (`src/train.py config.yaml`, as the FSDP script does), or
- run `llamafactory-cli train` on each node with `FORCE_TORCHRUN=1` and your own `NNODES`, `NODE_RANK` and `MASTER_ADDR`.

We have not run either on a cluster. We did not find an official guide for LLaMA-Factory on Kubeflow Trainer. The official image, `hiyouga/llamafactory`, is built on CUDA 12.4, so a TrainJob using it needs GPU nodes.

:::check Your QLoRA adapter is trained. You want a 4-bit model to serve. Why can't you merge the adapter straight into the 4-bit base you trained on?
LLaMA-Factory refuses ("Cannot merge adapters to a quantized model"). Merge into the full-precision base first, then quantize the merged model, for example with `export_quantization_bit`.
:::

:::check You switch from `ds_z2_config.json` to `ds_z3_config.json`. What extra thing is now split across GPUs, and what does it save?
The model weights themselves. Each GPU holds only a slice of them, which saves the most memory of the ZeRO stages.
:::
