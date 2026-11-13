---
title: The anatomy of a config
summary: Read the official SFT example line by line. The five argument groups behind it, the LoRA settings, cutoff length, effective batch size, and the chat template, which quietly adds a system prompt.
time: 20 min
---

Every LLaMA-Factory run is one YAML file. Here is the official LoRA SFT example, `examples/train_lora/qwen3_lora_sft.yaml` at v0.9.5, exactly as shipped:

```yaml
### model
model_name_or_path: Qwen/Qwen3-4B-Instruct-2507
trust_remote_code: true

### method
stage: sft
do_train: true
finetuning_type: lora
lora_rank: 8
lora_target: all

### dataset
dataset: identity,alpaca_en_demo
template: qwen3_nothink
cutoff_len: 2048
max_samples: 1000
preprocessing_num_workers: 16
dataloader_num_workers: 4

### output
output_dir: saves/qwen3-4b/lora/sft
logging_steps: 10
save_steps: 500
plot_loss: true
overwrite_output_dir: true
save_only_model: false
report_to: none  # choices: [none, wandb, tensorboard, swanlab, mlflow]

### train
per_device_train_batch_size: 1
gradient_accumulation_steps: 8
learning_rate: 1.0e-4
num_train_epochs: 3.0
lr_scheduler_type: cosine
warmup_ratio: 0.1
bf16: true
ddp_timeout: 180000000
resume_from_checkpoint: null
```

The `###` headings are comments. LLaMA-Factory reads one flat list of keys.

## Where every key comes from

The file is split into five groups of settings. Each is a Python class in `src/llamafactory/hparams/`, and the help text there is the real reference:

| Group | File | Holds |
|---|---|---|
| Model | `model_args.py` | base model, adapter path, quantization, export, inference backend |
| Data | `data_args.py` | `dataset`, `template`, `cutoff_len`, `max_samples`, `val_size` |
| Training | `training_args.py` | Hugging Face's own `Seq2SeqTrainingArguments`: batch size, learning rate, epochs, `bf16`, `report_to` |
| Fine-tuning | `finetuning_args.py` | `stage`, `finetuning_type`, LoRA and DPO settings, `plot_loss` |
| Generating | `generating_args.py` | sampling settings for chat, the API and predictions |

The training group is not LLaMA-Factory's own. It is the standard Hugging Face trainer config, so the transformers docs apply to it. That is also why `report_to: mlflow` works with no MLflow code in LLaMA-Factory, as the [tracking lesson](lesson:llamafactory/sft-with-mlflow-tracking) shows.

## The settings that matter most

**`lora_rank: 8`** is the thickness of the add-on matrices from [the LoRA lesson](lesson:llmops/sft-lora-dpo). `lora_alpha` is left unset, and its default is `lora_rank * 2`. It scales how strongly the add-on pushes on the model. `lora_dropout` defaults to 0.

**`lora_target: all`** means "use `all` to specify all the linear modules": every big matrix in attention and in the feed-forward layers gets an add-on. You can name modules instead, separated by commas.

**`cutoff_len: 2048`** is the longest row, in tokens, before it is cut. Set it near your longest real row. A smaller number is faster and uses less memory.

**`max_samples: 1000`** takes at most 1,000 rows from each dataset, "for debugging purposes". Remove it for a real run.

**Effective batch size** is the number of rows behind each weight update:

```text
per_device_train_batch_size x gradient_accumulation_steps x number of devices
           1                x            8                x        1          = 8
```

Accumulation adds up the gradients of 8 single rows before taking one step. The memory cost is that of 1 row, and the update is as smooth as with 8. The trade is time.

**`bf16: true`** trains in bfloat16, a 16-bit number format. It needs a recent GPU. On a CPU, set it to `false` and train in 32-bit.

**`learning_rate: 1.0e-4`** with `lr_scheduler_type: cosine` and `warmup_ratio: 0.1` means: rise for the first 10% of steps, then slowly fall to zero. LoRA usually needs a larger rate than full fine-tuning. The DPO example uses `5.0e-6`.

**`output_dir`** is where the adapter lands. `plot_loss: true` also saves `training_loss.png` there.

## The template, and the prompt you did not write

A chat model was trained on text in a fixed format, with markers for "user" and "assistant". `template` tells LLaMA-Factory which format to use. Get it wrong and the model sees text that looks nothing like its training. It will still train, just badly.

The examples use `qwen3_nothink` for Qwen3. Our model, `Qwen2.5-0.5B-Instruct`, uses `qwen`. Its definition in `src/llamafactory/data/template.py` contains this:

```python
default_system="You are Qwen, created by Alibaba Cloud. You are a helpful assistant.",
```

So every training row and every chat gets that system prompt, unless you set `default_system` yourself. For our Nori project that matters a lot. The model is told it is Qwen on every turn, and the fine-tune has to win against that instruction. We keep the default on purpose. Servers that use the model's own chat format, such as vLLM or KServe, add the same line, so the tuned model must answer as Nori even with it.

Two more data defaults are worth knowing. `train_on_prompt` is `false`, so the loss counts only the answer tokens, never the question. In alpaca data the `history` answers are trained on too.

## Overriding without editing

The same run as the YAML, with two settings changed:

```bash
llamafactory-cli train examples/train_lora/qwen3_lora_sft.yaml learning_rate=1e-5 logging_steps=1
```

Keys after the file name override the file. Every run in this track uses that pattern, so the official files stay untouched. The repository also ships `qwen3_lora_sft.sh`, the same run written as `--flag value` arguments with no YAML.

Our own config, `code/llamafactory/configs/sft_identity.yaml`, starts from this example. Its header lists every change and why: model, template, dataset, a shorter `cutoff_len`, more epochs for a tiny dataset, `bf16: false`, and `report_to: mlflow`.

## LlamaBoard

`llamafactory-cli webui` opens a browser form (built with Gradio) for the same settings. It is not a second engine. In `src/llamafactory/webui/`:

- **Preview command** prints the `llamafactory-cli train --key value ...` command the form adds up to.
- **Save arguments** writes the form to a YAML file.
- **Start** writes the settings to `training_args.yaml` inside `output_dir`, then runs `llamafactory-cli train` on that file.

So every GUI run leaves a YAML next to its adapter. Use the form to find what a key is called, then keep the YAML in git. We read this in the source; we did not click through the UI for this lesson.

:::check On one GPU, run A uses `per_device_train_batch_size: 4` and `gradient_accumulation_steps: 2`. Run B uses `1` and `16`. Which has the bigger effective batch, and which needs more memory?
B has the bigger effective batch: 1 x 16 = 16, against 4 x 2 = 8. A needs more memory, because it holds 4 rows on the GPU at once.
:::

:::check Your tuned Qwen model answers as Nori in `llamafactory-cli chat` but as Qwen in another server. What is the first thing you check?
The system prompt. LLaMA-Factory's `qwen` template adds "You are Qwen, created by Alibaba Cloud". If the two servers send different system prompts, the model sees different inputs.
:::
