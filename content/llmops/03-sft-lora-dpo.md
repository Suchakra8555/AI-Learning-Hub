---
title: SFT, LoRA, QLoRA, and DPO without the math
summary: What each name means, why LoRA makes training small enough for one GPU, and when preference tuning is the right next step.
time: 25 min
---

Four names come up in every fine-tuning conversation. Here is each one in plain words.

## SFT: show it examples

**Supervised fine-tuning (SFT)** trains a model on pairs of input and wanted output, so it learns to produce that output. Under the hood it is the same next-word guessing from [lesson 1](lesson:foundations/what-a-model-does), now scored against your examples. TRL's `SFTTrainer` handles this, and its docs show a quick start with a 0.6B-parameter model ([source](https://huggingface.co/docs/trl/sft_trainer)).

## PEFT and LoRA: train a small add-on

Training every number in a big model needs a lot of memory. **Parameter-efficient fine-tuning (PEFT)** trains only a small number of extra parameters.

**LoRA** is the most common way. It freezes the original weights and trains two thin matrices beside each big one. The PEFT docs describe the setting `r` (the "rank", how thin) and say you can merge the add-on back into the base weights afterwards with `merge_and_unload()`, so serving adds no delay ([source](https://huggingface.co/docs/peft/main/en/conceptual_guides/lora)).

Run `code/llmops/lora_math.py` to see why it is small:

```text
rank  4:    32,768 trainable vs 16,777,216 (0.20%)
rank  8:    65,536 trainable vs 16,777,216 (0.39%)
rank 16:   131,072 trainable vs 16,777,216 (0.78%)
```

That is the count for one 4,096 by 4,096 matrix. A full model has many of them, and the share stays small. The LoRA paper's abstract reports 10,000 times fewer trainable parameters and 3 times less GPU memory than full fine-tuning of GPT-3 175B with Adam ([paper](https://arxiv.org/abs/2106.09685)).

## QLoRA: LoRA on a squeezed model

**QLoRA** does LoRA on a model whose weights are stored in 4 bits, which saves more memory. Its paper's abstract says it can fine-tune a 65B model on a single 48 GB GPU ([paper](https://arxiv.org/abs/2305.14314)). In TRL you combine a quantization config with a PEFT config.

## DPO: teach preferences

**Direct preference optimization (DPO)** trains on pairs: the same prompt with a `chosen` answer and a `rejected` one. It pushes the model toward the chosen style. It needs no separate reward model. The paper says it is simpler than RLHF and matched or beat it on the tasks tested ([paper](https://arxiv.org/abs/2305.18290)). TRL's `DPOTrainer` expects `prompt`, `chosen` and `rejected` fields ([docs](https://huggingface.co/docs/trl/dpo_trainer)).

| Method | Data | Use when |
|---|---|---|
| SFT | input and output pairs | Teaching a format, tone, or task |
| LoRA / QLoRA | same data, cheaper training | You have one GPU |
| DPO | chosen and rejected pairs | The model's style is close but you want it to prefer one kind of answer |

:::note What we did not run
Training needs a GPU for practical speed, and we ran none here. We ran only the parameter count. To try it, follow the TRL quick start with the small model. We did not confirm how long it takes on a laptop CPU.
:::

:::check Why can LoRA fit on a smaller GPU than full fine-tuning?
Only the thin add-on matrices are trained, so far fewer numbers need gradients and optimizer memory.
:::
