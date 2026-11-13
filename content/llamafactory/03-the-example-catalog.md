---
title: The example catalog, and which ones run on a CPU
summary: A map of LLaMA-Factory's examples folder, and what happened when we ran 19 of the configs unchanged on a laptop with no GPU. 13 passed; here is why the other 6 did not.
time: 20 min
---

The `examples/` folder at v0.9.5 holds 132 files. It is the best documentation the project has, because every file is a run someone made work. This lesson maps it and reports what our laptop could do with it.

## The map

| Folder | What is in it |
|---|---|
| `train_lora/` | LoRA runs for every stage: pretrain, SFT, DPO, KTO, reward model; also SFT as a `.sh` script, SFT with DeepSpeed ZeRO-3, SFT with Ray, a tokenize-only run, and vision-language SFT and DPO |
| `train_qlora/` | LoRA on a 4-bit model: on-the-fly (bitsandbytes, HQQ, EETQ) or a model already in GPTQ, AWQ or AQLM |
| `train_full/` | Full fine-tuning with DeepSpeed |
| `merge_lora/` | Merge an adapter, export a full model, quantize with GPTQ |
| `inference/` | Configs for `chat`, `webchat` and `api` |
| `extras/` | Other methods: LoRA+, PiSSA, OFT, DFT, EAFT, ASFT, LLaMA-Pro, mixture-of-depths, FP8, FSDP+QLoRA, and the memory-saving optimizers GaLore, APOLLO, BAdam, Adam-mini and Muon |
| `deepspeed/`, `accelerate/` | ZeRO and FSDP configs the training files point at |
| `ascend/`, `ktransformers/`, `megatron/`, `megatron_bridge/` | Huawei NPUs, CPU+GPU hybrid for very large MoE models, Megatron backends |
| `v1/` | Configs for the new `USE_V1=1` launcher |

## How we ran them

`code/llamafactory/run_examples.py` runs each config from inside the clone, with the same overrides every time. It switches the model to `llamafactory/tiny-random-Llama-3` (template `llama3`), sets `bf16=false`, `max_steps=2`, `max_samples=16` and `cutoff_len=128`, and uses one worker process. Nothing else changes; the YAML files are not copied or edited.

"Pass" means the config parsed, the data loaded and went through the template, the model was wrapped for the method, two training steps ran, and the output was saved. It does not mean the method helps: the model is random. Two examples needed one more override each. `full-sft` got `deepspeed=null`, because ZeRO-3 needs GPUs. `predict` got the tiny model's matching LoRA adapter, `llamafactory/tiny-random-Llama-3-lora`.

## What happened

Windows 11, Python 3.12, CPU only, LLaMA-Factory v0.9.5:

```text
example     file                                     result  secs  last error line
pretrain    train_lora/qwen3_lora_pretrain.yaml      pass     144
sft         train_lora/qwen3_lora_sft.yaml           pass      71
dpo         train_lora/qwen3_lora_dpo.yaml           pass     126
kto         train_lora/qwen3_lora_kto.yaml           pass     181
reward      train_lora/qwen3_lora_reward.yaml        pass      61
preprocess  train_lora/qwen3_preprocess.yaml         pass      82
full-sft    train_full/qwen3_full_sft.yaml           pass      40
loraplus    extras/loraplus/llama3_lora_sft.yaml     pass      46
pissa       extras/pissa/llama3_lora_sft.yaml        pass      51
oft         extras/oft/llama3_oft_sft.yaml           pass     113
dft         extras/dft/qwen2_full_sft.yaml           pass      53
eaft        extras/eaft/qwen25_05b_eaft_full.yaml    pass      48
muon        extras/muon/qwen2_full_sft.yaml          FAIL      38  ValueError: I/O operation on closed file
galore      extras/galore/llama3_full_sft.yaml       FAIL      25  PackageNotFoundError ... 'galore_torch'
badam       extras/badam/llama3_full_sft.yaml        FAIL      24  PackageNotFoundError ... 'badam>=1.2.1'
apollo      extras/apollo/llama3_full_sft.yaml       FAIL      24  PackageNotFoundError ... 'apollo_torch'
adam-mini   extras/adam_mini/qwen2_full_sft.yaml     FAIL      23  PackageNotFoundError ... 'adam-mini'
predict     extras/nlg_eval/llama3_lora_predict.yaml FAIL      15  PackageNotFoundError ... 'jieba'
merge       merge_lora/qwen3_lora_sft.yaml           pass      44

13 of 19 passed
```

What the numbers say:

- **The time is mostly startup.** Each run imports PyTorch, Transformers and the rest before it does anything, and on this laptop that alone took close to a minute. In the SFT run, the two training steps themselves took 23 seconds. `pretrain` ran first, so its 144 seconds include downloading the tiny model and the demo data. KTO and DPO are slower than SFT because each step also scores the answers with a frozen reference model.
- **The reward model passed on Windows.** LLaMA-Factory's own test suite marks it as an expected failure on Windows ("OS error"). It passed here with v0.9.5. We did not dig into why the test still carries the mark.
- **Five failures are missing packages, not bugs.** Each method checks for its optional package and stops with a clear error. The packages are listed in `requirements/`: `galore.txt`, `badam.txt`, `apollo.txt`, `adam-mini.txt`, and `metrics.txt` for prediction (it needs `jieba`, `nltk` and `rouge-chinese` to score text). The README's install step includes `pip install -r requirements/metrics.txt`. We had skipped it.
- **Muon failed with an error we did not explain.** "I/O operation on closed file" is the last error line, and that is usually a side effect of an earlier failure, not the cause. Muon's optimizer code ships inside LLaMA-Factory (`third_party/muon`), so it is not a missing package. We did not get to the full log.

We installed the five packages and started the six again. The run was stopped twice because the laptop was critically low on memory: browsers, an editor and Docker were holding most of 16 GB. So **those six are still unverified**. The output folders for `muon`, `badam` and `adam-mini` show they got as far as starting.

## What we did not try

These need hardware the laptop does not have, or setup beyond one config:

| Example | Needs |
|---|---|
| `train_qlora/*`, `extras/fsdp_qlora`, `extras/qoft`, `extras/mod` (it uses `paged_adamw_8bit`) | bitsandbytes or a quantized checkpoint, so a CUDA GPU |
| `train_lora/qwen3_lora_sft_ds3.yaml`, `extras/fp8/*` | DeepSpeed or FP8 on GPUs |
| `train_lora/qwen3_lora_sft_ray.yaml` | Ray, with a worker per GPU |
| `train_lora/qwen3vl_*`, `extras/oft/qwen2_5vl_oft_sft.yaml` | a vision-language model, not the text-only tiny model |
| `extras/llama_pro` | running `expand.sh` first to grow the model |
| `extras/asft` | the `med` and `math` datasets, which are not in `data/` |
| `ascend/`, `ktransformers/`, `megatron*/`, `v1/` | NPUs, the KTransformers stack, Megatron, the new launcher |

[Scaling up](lesson:llamafactory/qlora-full-and-scaling-up) explains the GPU configs from the files.

:::try
Install the extras and run the six again: `pip install -r vendor/LlamaFactory/requirements/metrics.txt -r vendor/LlamaFactory/requirements/galore.txt` (and `badam.txt`, `apollo.txt`, `adam-mini.txt`), then `python run_examples.py galore badam apollo adam predict muon`. Close other heavy programs first.
:::

:::check The `galore` example fails with `PackageNotFoundError`. Is GaLore broken in LLaMA-Factory?
No. GaLore is optional, and its package is not installed by default. `requirements/galore.txt` names it. The error is the check doing its job.
:::

:::check Every run here passed with a model that has random weights. What does a pass prove, and what does it not?
It proves the config, data, template and method all fit together and that the run saves its output. It does not prove the method improves anything; random weights cannot learn the task in two steps.
:::
