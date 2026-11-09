---
title: Why test an agent, and the five words you need
summary: Dataset, experiment, evaluator, offline, online. Every eval tool uses these, and you can run the loop in 40 lines.
time: 15 min
---

You changed a prompt. Is the agent better? Without a test, you are guessing. The ideas below are the same across LangSmith, Langfuse, Opik and RAGAS. LangSmith's docs define them like this ([concepts](https://docs.langchain.com/langsmith/evaluation-concepts.md)):

| Word | Meaning |
|---|---|
| **Dataset** | A set of test cases. Each has an input and, optionally, a reference answer. |
| **Experiment** | The result of running one version of your app on a dataset: outputs, scores, traces. |
| **Evaluator** | A scoring function. Kinds: human review, code checks, a model as judge, pairwise comparison. |
| **Offline eval** | Run before you ship, on a fixed dataset. For regression tests and benchmarks. |
| **Online eval** | Run after you ship, on real traffic. No reference answers, so it checks for patterns, safety, and odd behavior. |

The app never sees the reference answer. Only evaluators do.

## The whole loop, runnable

`code/evals/mini_eval.py` has no libraries and no model. A keyword rule stands in for the app, so it runs offline:

```bash
cd code/evals
python mini_eval.py
```

```text
experiment baseline: {"exact_match": 0.75}
  failed: {'input': 'You are useless', 'output': 'ok', 'exact_match': 0}
```

Three of four right. The failure list is the useful part: "You are useless" is toxic and the rule missed it. Fix the app, run again, and compare the two experiments. That is the loop.

The same shape in LangSmith's SDK, from its docs (the fetch tool condensed this snippet, and we did not run it, so copy from the [live page](https://docs.langchain.com/langsmith/evaluate-llm-application.md)):

```python
results = evaluate(
    classify,
    data="Toxic Queries",
    evaluators=[correct],
    experiment_prefix="baseline",
)
```

## How many cases?

Start with 20 you wrote by hand ([how](lesson:rag/measure-quality)). Add every real failure you meet. A dataset grows from mistakes.

:::check What does an online eval have that an offline eval lacks, and what does it lack?
It sees real production traffic, but it has no reference answers, so it can only check patterns and quality signals.
:::
