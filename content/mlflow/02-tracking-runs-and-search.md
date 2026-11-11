---
title: Tracking runs and finding the best one
summary: Log parameters, metrics and files for three training runs, then find the best run with a filter. Run on MLflow 3.18.0.
time: 20 min
---

Three trainings, three settings, one question: which was best? Without a record you guess. With MLflow Tracking each training is a **run**, and runs live inside an **experiment** ([docs](https://mlflow.org/docs/latest/ml/tracking/)).

## The script

`code/mlflow/track_runs.py` trains a random forest on scikit-learn's wine data three times. The core is five calls:

```python
mlflow.set_experiment("wine-forest")              # created on first use
with mlflow.start_run(run_name=f"trees={trees} depth={depth}"):
    mlflow.log_params({"n_estimators": trees, "max_depth": depth})
    mlflow.set_tag("dataset", "sklearn wine, 30% test, seed 0")
    ...
    mlflow.log_metrics({"accuracy": acc, "f1_macro": f1})
    mlflow.log_artifact("notes.txt")               # any file
```

- **Parameters** are settings you chose. They are written once.
- **Metrics** are results. Give one a `step=` and the UI draws a line chart over steps.
- **Tags** are free labels. Put the data version here.
- **Artifacts** are files: plots, notes, models.

## Finding the best run

`mlflow.search_runs` takes a filter string and an order, and returns a table:

```python
mlflow.search_runs(
    experiment_names=["wine-forest"],
    filter_string="metrics.accuracy > 0.9",
    order_by=["metrics.f1_macro DESC"],
)
```

The output we got:

```text
   tags.mlflow.runName params.n_estimators  metrics.accuracy  metrics.f1_macro
      trees=50 depth=4                  50          1.000000          1.000000
       trees=5 depth=2                   5          0.981481          0.983584
trees=200 depth=None                 200          0.981481          0.979902
```

The middle setting won, and the biggest forest did not. The test set has 54 rows, so one row is 1.85 points of accuracy. Treat the gap between 0.98 and 1.00 as noise, the same warning the [RAG evals](lesson:rag/measure-quality) give. MLflow does not make a comparison fair. It only makes it repeatable.

## Things to know

- Metrics and params are searched with a prefix: `metrics.`, `params.`, `tags.`.
- Runs can be nested with `start_run(nested=True)`, useful for one search containing many trials.
- `mlflow.autolog()` logs the parameters and metrics of supported libraries (scikit-learn, PyTorch, XGBoost and others) without the five calls above. Read what it logged before you trust it.
- Logging is synchronous by default. For a training loop that logs often, the docs describe an async option.

:::try
Run the script twice. Does the experiment get six runs or three? Then change `random_state` for the split and see whether the "best" run changes.
:::

:::check Why log the dataset version as a tag when the code is in git?
The code does not say which rows you trained on. A run without its data version cannot be repeated.
:::
