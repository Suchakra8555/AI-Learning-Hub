---
title: Prompt, RAG, or fine-tune?
summary: Three ways to improve a model's answers. Pick by what is wrong, and try the cheapest first.
time: 10 min
---

A model gives bad answers. You have three tools. They fix different problems.

| Symptom | Try first | Why |
|---|---|---|
| Wrong format, tone, or it ignores instructions | **Better prompt**, with examples | Cheapest. Change text, test again. |
| It lacks facts: your documents, recent events | **RAG** ([the RAG track](lesson:rag/what-is-rag)) | The model cannot know what it never saw. Give it the text. |
| It has the facts but behaves inconsistently, even with a good prompt | **Fine-tuning** | Trains the behavior into the model. |

OpenAI's accuracy guide takes the same order: start with prompting and a small test set, add retrieval when knowledge is missing, and fine-tune when behavior is inconsistent. It suggests an eval set of 20 or more question and answer pairs, and about 50 good examples to start fine-tuning ([source](https://developers.openai.com/api/docs/guides/optimizing-llm-accuracy)). Those are one vendor's starting points. Treat them as a floor to begin from, not a rule.

The two can be combined: a fine-tuned model that also gets retrieved text.

:::warn Fine-tuning is not the way to add facts
A model trained on your documents does not reliably quote them, and it goes stale when they change. Use RAG for facts, and fine-tuning for behavior.
:::

## Do this before any training

1. Write 20 test questions with known good answers ([how](lesson:rag/measure-quality)).
2. Try a plain prompt. Score it.
3. Paste the right document into the prompt. Score again.
4. Only if scores are still low, and the problem is behavior, consider fine-tuning.

:::check Customers ask about this month's new return policy and the model answers with last year's. Prompt, RAG, or fine-tune?
RAG. The problem is missing and changing facts, and retrieval can use the new document the day it is published.
:::
