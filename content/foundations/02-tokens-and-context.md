---
title: Tokens and context windows
summary: Models count text in tokens, not words. Tokens decide your cost, your speed, and how much fits in one call.
time: 15 min
---

A model does not read letters or words. It reads **tokens**: small pieces of text. A token is often a short word or part of a longer one. In English, one token is roughly four characters, or three quarters of a word. "Unbelievable" may become three tokens. Numbers, code, and non-English text usually take more tokens per word.

## Why you care

1. **Cost.** You pay per token, for text in and text out. Output tokens usually cost more than input tokens.
2. **Speed.** The model writes one token at a time. Longer answers take longer.
3. **Fit.** The **context window** is the most tokens the model can handle in one call, counting your prompt and its answer together. If your documents are bigger, they do not fit.

## Try it

`code/foundations/token_count.py` gives a rough count:

```bash
cd code/foundations
python token_count.py "How long do I have to return a tent?"
```

```text
36 characters is about 9 tokens
```

This is a rule of thumb, not the real tokenizer. For billing and hard limits, use the token counter your model provider offers. The file says so in a `shortcut:` comment. Code in this course marks its known limits that way.

## A quick cost sum

Say a RAG prompt holds 5 chunks of 300 words, plus a question. That is about 1,500 words, or 2,000 tokens, per request. At 10,000 requests a day, that is 20 million input tokens a day. Prices change, so look up your provider's current price and do this sum before you launch. [The RAG track](lesson:rag/fast-cheap-safe) shows ways to cut it.

:::warn Bigger windows are not free
A large context window lets you paste more in. It does not make the model read every part equally well, and you still pay for every token. Send what is needed.
:::

:::check Your prompt is 3,000 tokens and the model's window is 4,000. What limits the answer length?
The window counts prompt plus answer together, so only about 1,000 tokens are left for the answer.
:::
