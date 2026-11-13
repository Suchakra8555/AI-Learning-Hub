---
title: Your own data, and its version
summary: Register a dataset in dataset_info.json, map OpenAI-style messages onto the sharegpt format, write preference and KTO rows, build the Nori identity set, and give the data a version that survives a change of operating system.
time: 20 min
---

LLaMA-Factory never reads a data file directly. It reads `dataset_info.json` in your `dataset_dir`, finds the name you put in `dataset:`, and learns from that entry where the file is and what its columns mean. The official file at v0.9.5 has 104 entries. You add your own the same way.

## Two formats

`data/README.md` describes two layouts.

**alpaca**: one row per example.

```json
{"instruction": "Who are you?", "input": "", "output": "I am Nori...", "system": "", "history": []}
```

The user prompt is `instruction` plus `input`. `history` holds earlier turns, and its answers are trained on too.

**sharegpt**: a list of messages, like a chat log. Its defaults are `from` and `value` keys with `human` and `gpt` roles. That is not what most of us have. The [LLMOps lesson on training data](lesson:llmops/training-data) used OpenAI-style rows: `role` and `content`, with `user` and `assistant`. LLaMA-Factory does not make you convert them. You map the names in `tags`.

## The Nori dataset

`code/llamafactory/make_dataset.py` builds the data for this track:

1. Takes the 16 English rows of LLaMA-Factory's own `data/identity.json` (the file has 91 rows; the rest are in Chinese). Their answers contain `{{name}}` and `{{author}}`, and the script fills them with "Nori" and "Northwind Outfitters".
2. Adds 24 phrasings of our own ("Are you Qwen?", "Which company made you?").
3. Splits the 40 rows 70/30 with `split` from `code/llmops/training_data.py`: same seed, same split everywhere.
4. Keeps only the hold-out rows that ask for the name, because those are the ones the [evaluation](lesson:llamafactory/evaluate-before-you-ship) can score.
5. Writes a few DPO pairs, and a `dataset_info.json` that describes all three files.

```text
16 English rows from identity.json + 24 of ours = 40
train 28, hold-out 9 (name questions only), dpo pairs 6
nori_train.jsonl     sha256 4d59031d09f4
nori_holdout.jsonl   sha256 a86c85001296
nori_dpo.jsonl       sha256 11201a89e965
```

A row in `nori_train.jsonl`:

```json
{"messages": [{"role": "user", "content": "Introduce yourself in one sentence."}, {"role": "assistant", "content": "I am Nori, an AI assistant developed by Northwind Outfitters."}]}
```

Its entry in `data/dataset_info.json`:

```json
"nori_train": {
  "file_name": "nori_train.jsonl",
  "formatting": "sharegpt",
  "columns": {"messages": "messages"},
  "tags": {"role_tag": "role", "content_tag": "content", "user_tag": "user", "assistant_tag": "assistant"}
}
```

`columns` says which field holds the messages. `tags` says which keys and values mean "who spoke", "what they said", "user" and "assistant". The official `kto_en_demo` entry uses the same `tags` block, so this mapping is not a trick of ours.

The script ends with two checks: no hold-out question appears in train, and no `{{` placeholder is left. A placeholder that slips through would teach the model to say "I am {{name}}".

## Preference rows

DPO needs the same prompt with a better and a worse answer. Set `"ranking": true` and point `chosen` and `rejected` at single assistant messages:

```json
{"messages": [{"role": "user", "content": "Can I return a stove?"}],
 "chosen": {"role": "assistant", "content": "I don't know our stove policy. Please check the returns page or ask support."},
 "rejected": {"role": "assistant", "content": "Yes, stoves can be returned within 365 days, no questions asked."}}
```

Our pairs teach the lesson from the [citations lesson](lesson:rag/prompt-and-citations): saying "I don't know" beats inventing a policy.

**KTO** needs less: one answer per row and a yes/no label for whether it is good. The official `kto_en_demo` entry maps a `label` column with `"kto_tag": "label"`. That is useful when you have thumbs-up and thumbs-down logs but no pairs.

## The data needs a version

Three weeks from now someone asks which data made this adapter. "nori_train.jsonl" is not an answer, because the file may have changed since. A **hash** is: the same bytes always give the same fingerprint, and any change gives a different one.

The [tracked run](lesson:llamafactory/sft-with-mlflow-tracking) records the data with `mlflow.data` and `log_input`. MLflow computes its own `digest` of the rows and stores it on the run, next to the data's source path.

### The bug we hit

The first version of `write_jsonl` used `Path.write_text`. On Windows, text mode writes every `\n` as `\r\n`. We counted 28 of them in the 28-row file. The same rows would have hashed differently on the laptop and in the Linux container the [pipeline](lesson:llamafactory/pipeline-on-kubeflow) runs in, so two copies of one dataset would look like two versions. We changed the function to write bytes:

```python
# bytes, not text: text mode writes \r\n on Windows, so the same rows would hash differently per OS
path.write_bytes(("\n".join(json.dumps(r) for r in rows) + "\n").encode("utf-8"))
```

After the fix, the Docker build ran the same script on Linux and printed the same three digests as the laptop. The general rule: before you trust a hash as a version, make sure the bytes do not depend on the machine. Watch line endings, key order in JSON, and float formatting.

:::check Your rows are OpenAI-style (`role`, `content`, `user`, `assistant`). What do you add to `dataset_info.json` so LLaMA-Factory reads them as they are?
`"formatting": "sharegpt"`, `"columns": {"messages": "messages"}`, and a `tags` block that maps `role_tag` to `role`, `content_tag` to `content`, `user_tag` to `user` and `assistant_tag` to `assistant`.
:::

:::check You have 2,000 customer replies, each rated thumbs up or down, but no pairs. DPO or KTO?
KTO. It takes one answer per row with a good or bad label. DPO needs a chosen and a rejected answer for the same prompt.
:::
