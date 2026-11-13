---
title: DPO, KTO and reward models
summary: The preference stages in LLaMA-Factory - the settings that matter, what our CPU runs of the official examples produced, why the first DPO loss is always 0.693, and how PPO would use a reward model.
time: 20 min
---

SFT teaches by example: here is the answer, copy it. Preference training teaches by comparison: of these answers, prefer this one. [The LLMOps lesson](lesson:llmops/sft-lora-dpo) explained why. This one shows the switches in LLaMA-Factory.

## DPO

`examples/train_lora/qwen3_lora_dpo.yaml` differs from the SFT example in four places:

```yaml
stage: dpo
pref_beta: 0.1
pref_loss: sigmoid  # choices: [sigmoid (dpo), orpo, simpo]
dataset: dpo_en_demo        # a "ranking": true dataset, see your-own-data
learning_rate: 5.0e-6       # SFT used 1.0e-4
```

- **`pref_beta`** (default 0.1) controls how far the model may move away from where it started. Smaller lets it move further.
- **`pref_loss`** picks the formula. The code accepts `sigmoid` (standard DPO), `hinge`, `ipo`, `kto_pair`, `orpo` and `simpo`. `simpo_gamma` (default 0.5) is SimPO's margin.
- **`pref_ftx`** (default 0) adds some SFT loss on the chosen answer, so the model does not forget how to write while it learns to prefer.
- The **learning rate** is 20 times lower than in SFT. DPO moves the model toward one answer and away from another, and a big step quickly ruins it.

For LoRA, the reference (the "where it started" copy) is the base model with the adapter switched off (`disable_adapter()` in `train/dpo/trainer.py`), so no second model is loaded. ORPO and SimPO skip the reference entirely. `ref_model` points at a separate one if you need it.

### What our CPU run showed

The official DPO example ran on the tiny random model in 126 seconds (see [the catalog](lesson:llamafactory/the-example-catalog)). Its log:

```text
{"current_steps": 2, "total_steps": 2, "loss": 0.6931471824645996, "accuracy": 0.0, "lr": 5e-06, ...}
```

0.6931 is ln 2, and that is the expected value. DPO's loss compares how much more likely the model makes the chosen answer than the reference does, against the same for the rejected answer. At the start the model is the reference, so the difference is 0, and the loss is -log(sigmoid(0)) = ln 2. A real DPO run starts at 0.693 and should fall. If yours never moves, the model is not learning the preference.

The run also wrote `training_rewards_accuracies.png`: the share of pairs where the model already prefers the chosen answer. It is 0 here and should climb in a real run.

### Our own pairs

`make_dataset.py` writes six Nori pairs to `data/nori_dpo.jsonl`. The chosen answers say "I don't know" or "I can only help with Northwind"; the rejected ones invent a policy. They are registered as `nori_dpo`. To train on them after the SFT run (not run here):

```bash
llamafactory-cli train vendor/LlamaFactory/examples/train_lora/qwen3_lora_dpo.yaml \
    model_name_or_path=Qwen/Qwen2.5-0.5B-Instruct template=qwen \
    adapter_name_or_path=saves/nori/lora/sft dataset_dir=data dataset=nori_dpo \
    bf16=false output_dir=saves/nori/lora/dpo
```

Six pairs is far too few for a real result. The point is the format and the flow: SFT first, then DPO starting from the SFT adapter.

## KTO

KTO uses single answers with a good or bad label (`stage: kto`, a `kto_tag` column). `kto_chosen_weight` and `kto_rejected_weight` (both default 1.0) let you weigh the two kinds differently when you have far more of one. The official example passed in 181 seconds. Its first loss was 0.5, its own neutral starting point.

## Reward models and PPO

`stage: rm` trains a **reward model**: the base model plus a small head that outputs one score for an answer. The official example passed in 61 seconds, although LLaMA-Factory's own tests mark this stage as failing on Windows. Its output has one file the others lack:

```text
value_head.safetensors
```

That is the scoring head. When you export a reward model (with `stage: rm` in the export config), LLaMA-Factory copies it next to the merged weights.

A reward model exists to serve **PPO** (`stage: ppo`). PPO samples answers, has the reward model score them, and updates the model toward higher scores. The settings are `reward_model` (path), `reward_model_type` (`lora`, `full` or `api`), `ppo_epochs` (default 4) and `ppo_target` (KL target, default 6.0). There is no PPO example in `examples/` at v0.9.5, and we did not run one. It is the most expensive stage: the model being trained (with a value head of its own), a reference and the reward model all take part.

| Stage | Data | Extra models during training | Use when |
|---|---|---|---|
| `dpo` | chosen + rejected pairs | reference (free with LoRA) | you have pairs |
| `kto` | single answers, good or bad | reference | you have thumbs up and down |
| `rm` then `ppo` | pairs for the reward model, then prompts | reference, reward model | you need online scoring, and have the GPUs |

:::check A DPO run's loss starts at 0.693 and stays there for every step. What does that tell you?
The model is not moving away from the reference: the chosen and rejected answers look the same to it. Check the learning rate, that the data really is `ranking: true` pairs, and that the adapter is training.
:::

:::check Why can a LoRA DPO run get away without loading a second copy of the model as the reference?
The reference is the base model with the adapter switched off. Switching it off gives the starting model back for free.
:::
