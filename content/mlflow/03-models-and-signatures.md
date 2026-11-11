---
title: A model is more than a pickle file
summary: What MLflow saves next to the weights (the MLmodel file, the input schema, the environment), and how the schema stops a wrong column at prediction time.
time: 20 min
---

A pickle file holds weights. It does not say what columns to feed it, which library versions it needs, or which run made it. An **MLflow Model** is a folder that holds all of that ([docs](https://mlflow.org/docs/latest/ml/model/)).

## Log one

`code/mlflow/log_and_register.py` logs a logistic regression with a signature and an example:

```python
info = mlflow.sklearn.log_model(
    model,
    name="model",
    signature=infer_signature(X_train, model.predict(X_train)),
    input_example=X_train.head(2),
)
print(info.model_uri)    # models:/m-6bbdf7fe9efb498fa57bb7f69ac66a62
```

In MLflow 3 the URI is `models:/<model_id>`. The id belongs to a **LoggedModel**, an object of its own, not a path inside a run.

## The MLmodel file

Open the folder and read `MLmodel`. This is the real file from our run, trimmed:

```yaml
flavors:
  python_function:
    env: {conda: conda.yaml, virtualenv: python_env.yaml}
    loader_module: mlflow.sklearn
    model_path: model.skops
    python_version: 3.12.4
  sklearn:
    serialization_format: skops
    sklearn_version: 1.9.1
mlflow_version: 3.18.0
model_id: m-6bbdf7fe9efb498fa57bb7f69ac66a62
signature:
  inputs: '[{"type": "double", "name": "alcohol", "required": true}, ...13 columns]'
  outputs: '[{"type": "tensor", "tensor-spec": {"dtype": "int64", "shape": [-1]}}]'
```

Three ideas sit in this file:

- A **flavor** is a way to load the model. `sklearn` loads it as a scikit-learn object. `python_function` (**pyfunc**) loads any model behind one `predict()`. Serving tools only need pyfunc.
- The **signature** is the input and output schema.
- The environment files record Python and package versions, so another machine can rebuild it.

The weights were saved as `model.skops`, not a pickle. Pickle can run code when loaded, so MLflow 3.18 added `MLFLOW_ALLOW_MODEL_CODE_EXECUTION` and says pickle-free formats will become the default ([release notes](https://github.com/mlflow/mlflow/releases)). Only load models you trust.

## The signature in action

We loaded the model and sent a column the model never saw (`alcohol` renamed `alcohol_pct`):

```text
MlflowException ... Error: Model is missing inputs ['alcohol']. Note that there were extra inputs: ['alcohol_pct'].
```

The error appears when the code calls `predict()`, not after the model quietly scores garbage. A missing signature turns this into a silent bug. Log one every time.

## Models that are not scikit-learn

For your own code, subclass `mlflow.pyfunc.PythonModel` and log it with `mlflow.pyfunc.log_model`. For LLM apps the docs recommend `ResponsesAgent` over `ChatModel`. We did not run a custom `PythonModel` for this lesson. Read [custom models](https://mlflow.org/docs/latest/ml/model/python_model/) before you write one, and pin requirements in `pip_requirements=`.

:::check What does the signature protect you from?
Wrong column names, missing columns and wrong types, caught at `predict()` with a clear error.
:::
