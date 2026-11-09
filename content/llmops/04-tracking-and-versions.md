---
title: Tracking experiments and model versions
summary: Record every run so you can say which data and settings made which result, then promote one version safely.
time: 15 min
---

After a week of experiments you will have dozens of runs. Without records, nobody can say which one was best or how to repeat it.

## Runs, experiments, and artifacts

MLflow Tracking records a **run**: the parameters you set, the metrics you measured, and the output files (called **artifacts**). Runs are grouped into **experiments** ([source](https://mlflow.org/docs/latest/ml/tracking/)).

A run for a fine-tune might log: learning rate, LoRA rank, dataset version, hold-out score, and the adapter file.

## The model registry

MLflow's **Model Registry** stores model **versions**. An **alias** such as `champion` points at one version, and your serving code loads "the champion" by name ([source](https://mlflow.org/docs/latest/ml/model-registry/)). To roll out a new model, move the alias. To roll back, move it back. No code change.

## Staged releases

A safe path for a model or prompt:

1. **Experiment**: runs on a laptop or training box.
2. **Staging**: the candidate version serves test traffic. Run your evaluation set against it.
3. **Production**: move the alias after the numbers pass.
4. **Rollback**: move the alias back if something breaks.

Langfuse offers a similar idea for prompts: labels that point environments at prompt versions without redeploying code ([docs](https://langfuse.com/docs)).

We did not find one official step-by-step guide for evaluation gates in CI/CD, so this lesson stops at the idea. Your own pipeline would run the test set and fail the release if the score drops.

:::try
Install MLflow, run `mlflow ui`, and log two runs with different parameters in a short script, then compare them in the UI. We took the install command from general knowledge and did not run it here, so check MLflow's docs.
:::

:::check Why use an alias like `champion` and not a version number in your serving code?
You can switch or roll back the model by moving the alias, without changing or redeploying the code.
:::
