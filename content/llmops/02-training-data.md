---
title: Training data that works
summary: Fine-tuning learns from examples. Get the format right, split off a hold-out set, and keep every version.
time: 15 min
---

A fine-tuned model is only as good as its examples. Three habits matter more than any setting.

## 1. Use a standard format

Hugging Face's TRL library accepts plain text, conversation, and prompt-and-completion formats ([SFT docs](https://huggingface.co/docs/trl/sft_trainer)). The conversation format is easy to read:

```json
{"messages": [{"role": "user", "content": "How long to return a tent?"},
              {"role": "assistant", "content": "Tents can be returned within 60 days if unused."}]}
```

One example per line in a `.jsonl` file. This is called **JSON Lines**.

## 2. Keep a hold-out set

Set aside some examples the model never trains on. After training, test on them. If the model does well on its training rows and badly on the hold-out rows, it memorized and did not learn. OpenAI's guide also says to keep a hold-out set for this ([source](https://developers.openai.com/api/docs/guides/optimizing-llm-accuracy)).

## 3. Make the split repeatable

`code/llmops/training_data.py` shuffles with a fixed seed so everyone gets the same split, and checks that no row lands in both sets:

```bash
cd code/llmops
python training_data.py
```

```text
train 8, holdout 2
```

The ten rows in the file are made up, only to show the shape. Real tuning needs real examples in your own style.

## Also decide

- **Quality over quantity.** A few dozen careful examples beat thousands of sloppy ones.
- **Rights.** Check that you may train on the text. We did not find a source to cite on licensing, so ask whoever owns the data.
- **Version the files.** Commit them, or store them in a tool that versions datasets, so you can say which data made which model.

:::check Training accuracy is 99% and hold-out accuracy is 60%. What happened?
The model memorized its training examples (overfitting). The hold-out set exists to catch exactly this.
:::
