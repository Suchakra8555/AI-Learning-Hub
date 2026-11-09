---
title: Judges, live checks, and refining prompts with evidence
summary: Use a model to score answers, watch its limits, run checks on live traffic, and change prompts only when the numbers say so.
time: 20 min
---

## A model as a judge

Some answers cannot be checked with `==`. "Is this reply polite?" or "Is every claim backed by the notes?" need judgment. An **LLM-as-judge** evaluator asks a model to score the answer against a rule you write.

A judge is a model, so it can be wrong. Do this:

1. Write the rule precisely: "Score 1 if every claim appears in the notes, else 0."
2. Have a person label 20 answers.
3. Compare the judge's scores with yours. Fix the rule until they mostly agree.

LangSmith lists pages on exactly this, on auditing evaluator scores and improving judge feedback. We did not read them, so check them for the steps.

The RAG-specific judges from the [LLMOps track](lesson:llmops/scoring-and-watching) (faithfulness, relevancy, context precision) are judge evaluators with ready-made rules.

## Online evaluators: checks on live traffic

LangSmith can score a sample of production runs. You pick filters and a **sampling rate**. A rate of 0.1 means 10% of matching runs ([source](https://docs.langchain.com/langsmith/online-evaluations-llm-as-judge.md)). The page warns about:

- **Cost.** Each scored run is a model call. Use sampling.
- **A weekly spend limit** per evaluator. At the limit, the evaluator pauses until Monday 12AM UTC or an admin raises it.
- **Retention.** Any evaluator run moves that trace to extended data retention, which can raise cost.
- **Backfill** of past runs can only be chosen when you create the rule.

## Refining a prompt with evidence

LangSmith's Playground and Prompt Hub let you edit a prompt, test it, save a commit, tag it, and pin a version as `"<prompt-name>:<commit-hash>"` ([quickstart](https://docs.langchain.com/langsmith/prompt-engineering-quickstart.md)). The tools matter less than the habit:

1. Run the dataset on the current prompt. Note the score.
2. Change **one** thing.
3. Run again. Keep the change only if the score moved and no case got worse.
4. Save the version, so you can go back.

:::warn Do not tune on your test set
If you keep editing the prompt until the test cases pass, you have fitted the prompt to those cases. Keep a few cases aside that you never look at while tuning, as in the [hold-out set](lesson:llmops/training-data).
:::

:::check Your judge gives the same score to every answer. What do you check first?
The judge's rule. If it is vague, the judge cannot separate good from bad. Compare its scores with human labels on a few answers and tighten the rule.
:::
