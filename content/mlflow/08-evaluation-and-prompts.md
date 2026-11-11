---
title: Evaluating an app and versioning its prompts
summary: Score an app with code scorers using mlflow.genai.evaluate, version a prompt with an alias, and what the LLM-judge scorers need. Run on MLflow 3.18.0.
time: 25 min
---

Part of [Evals](lesson:evals/judges-and-refining) was theory. Here is MLflow's version, run end to end.

## Evaluate

`mlflow.genai.evaluate` takes data, a function to test, and a list of **scorers** ([docs](https://mlflow.org/docs/latest/genai/eval-monitor/)). A scorer is a check that returns a value. A plain Python function with `@scorer` is the simplest:

```python
@scorer
def has_expected_fact(outputs, expectations) -> bool:
    return expectations["must_contain"] in outputs

result = mlflow.genai.evaluate(data=data, predict_fn=answer,
                               scorers=[has_expected_fact, short_enough])
```

`data` is a list of `{"inputs": {...}, "expectations": {...}}`. We gave it three questions. The third asks about stoves, which our notes do not cover, and expects "I don't know". Our rule-based bot cannot say that, so it should fail:

```text
{'has_expected_fact/mean': 0.6666666666666666, 'short_enough/mean': 1.0}
```

Two of three passed. Each run also stores a trace per question, so you can open the failing one.

## Judges

The same call accepts built-in LLM-judge scorers. The 3.18 package exports, among others: `Correctness`, `Guidelines`, `Safety`, `RelevanceToQuery`, `RetrievalGroundedness`, `RetrievalRelevance`, `RetrievalSufficiency`, `ToolCallCorrectness`, `PIIDetection` and `UserFrustration`. `make_judge` builds a custom one from a prompt. These call a model, so they need a key and cost money. We did not run them. The docs disagree on details, for example the expectation key `Correctness` reads, so read the page for the version you installed.

Two warnings from the [judging lesson](lesson:rag/judging-answers) apply: a judge is a model with its own mistakes, and a one-question change is noise.

## Compare versions

`mlflow.genai.compare_evaluations` and `assert_improved` are marked experimental in 3.18. They aim to fail a CI job when a new version scores worse. We did not run them.

## Version the prompt

Prompts change as often as code. The **Prompt Registry** stores each edit as an immutable version and lets an alias point at one, the same idea as [model aliases](lesson:mlflow/registry-and-aliases). `code/mlflow/prompt_registry.py`:

```python
v2 = mlflow.genai.register_prompt(name="support-answer", template="...", commit_message="add the refusal line")
mlflow.genai.set_prompt_alias("support-answer", alias="production", version=2)
p = mlflow.genai.load_prompt("prompts:/support-answer@production")
```

Real output:

```text
versions: 1 2
production -> 1
production -> 2 | add the refusal line
```

Templates use `{{double braces}}`, and `p.format(...)` fills them. `@latest` is reserved for the newest version.

## Not run

- `mlflow.genai.optimize_prompts` (3.5.0 and later) rewrites a prompt against your scorers. We did not run it, and the docs do not say which extra packages its optimizers need.
- `set_active_model` and Git-based versioning tie an app version to its traces.
- The built-in **AI Gateway** is an OpenAI-compatible endpoint with fallbacks and guardrails. See [LLM gateway](lesson:deploy/llm-gateway) for the idea. Reports say it may not support Windows; we could not confirm that on a current page.

:::check A scorer passes 2 of 3 questions. What do you look at first?
The failing question's trace, to see which span produced the bad output.
:::
