---
title: The registry, aliases and rollback
summary: Register two versions, point a champion alias at the better one, roll back by moving the alias, and why stages are gone. Run on MLflow 3.18.0.
time: 15 min
---

This lesson replaces the short version in [Tracking experiments and model versions](lesson:llmops/tracking-and-versions) with a run you can repeat.

The **Model Registry** gives a model a name and a list of numbered versions ([docs](https://mlflow.org/docs/latest/ml/model-registry/)). An **alias** is a movable label on one version. Serving code asks for `models:/wine-classifier@champion` and never mentions a number.

## Register, then move the label

In `log_and_register.py`, passing `registered_model_name="wine-classifier"` to `log_model` creates the next version each time. We trained a weak model (`C=0.01`) and a better one (`C=1.0`):

```text
Created version '1' of model 'wine-classifier'.
Created version '2' of model 'wine-classifier'.
C=0.01: accuracy 0.963, version 1
C=1.0: accuracy 0.981, version 2
```

Then the script does what a release does:

```python
client = MlflowClient()
client.set_registered_model_alias(NAME, "champion", best)       # best = 2
client.set_model_version_tag(NAME, best, "validated", "true")
champ = mlflow.pyfunc.load_model(f"models:/{NAME}@champion")

client.set_registered_model_alias(NAME, "champion", other)      # rollback to version 1
```

Output:

```text
champion is version 2
after rollback, champion is version 1
```

Nobody changed or redeployed the serving code between the two lines. That is the point of an alias.

## Why not stages

Older tutorials say "move the model to Production". **Stages** (None, Staging, Production, Archived) have been deprecated since MLflow 2.9.0 and "will be removed in a future major release" ([docs](https://mlflow.org/docs/latest/ml/model-registry/)). A few doc pages still teach them. Stages give you exactly four labels. Aliases give you any names: `champion`, `challenger`, `canary`, `eu-prod`.

## Promoting between environments

To move a model from a dev registry to a prod registry, MLflow has `copy_model_version`. It copies the version, not the alias. Set the alias again after the copy. We did not run this one.

Registry **webhooks** can notify another system when a version or alias changes. The docs list them; we did not test them.

## A release gate, in plain steps

1. Train, log and register. The new version has no alias yet.
2. Run your fixed test set against the new version.
3. If the score passes, move `champion` to it. If not, leave it.
4. If production breaks, move `champion` back.

We found no official guide for an automated gate, so step 2 is yours to write. The same idea works for prompts, see [evaluation and prompts](lesson:mlflow/evaluation-and-prompts).

:::check Version 2 was better and you moved `champion` to it. A day later accuracy drops in production. What is the fastest fix?
Move the alias back to version 1. No redeploy.
:::
