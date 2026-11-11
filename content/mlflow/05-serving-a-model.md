---
title: Serving a model over HTTP
summary: Start mlflow models serve, call /invocations in its input formats, read the 400 error, and what MLflow no longer ships for Kubernetes.
time: 20 min
---

A saved model is useful when another program can call it. `mlflow models serve` starts a small web server around any model that has the pyfunc flavor ([docs](https://mlflow.org/docs/latest/ml/deployment/)).

```bash
mlflow models serve -m "models:/wine-classifier@champion" --env-manager local -p 5001
```

Defaults from the 3.18 CLI help: host `127.0.0.1`, port 5000, timeout 60 s, 1 worker. `--env-manager` can be `local` (this Python), `virtualenv`, `uv` or `conda`. With the others MLflow builds the environment from the model's own files, which is slower and more faithful.

:::warn It did not start on native Windows
On our Windows machine the command died with `FileNotFoundError: [WinError 2]`. In the 3.18 source, `mlflow/pyfunc/backend.py` starts the server with `bash -c ...`. We did not find the cause past that. We ran this lesson in a Linux container instead (`python:3.12-slim` under Docker). Use WSL or a container on Windows.
:::

## The endpoints

`code/mlflow/call_server.py` calls the server with the standard library. Real output from the container run:

```text
GET /ping    (200, '\n')
GET /version (200, '3.18.0')
dataframe_split   (200, '{"predictions": [0]}')
dataframe_records (200, '{"predictions": [0]}')
inputs (columns)   (200, '{"predictions": [0]}')
bad: missing key   (400, '{"error_code": "BAD_REQUEST", "message": "The input must be a JSON dictionary with exactly one of the input fields {'dataframe_split', 'instances', 'dataframe_records', 'inputs'}. ...')
```

`POST /invocations` accepts exactly one of four top-level keys:

| Key | Shape | Use for |
| --- | --- | --- |
| `dataframe_split` | `{"columns": [...], "data": [[...]]}` | tables, compact |
| `dataframe_records` | `[{"col": value}, ...]` | tables, one dict per row |
| `inputs` | a list, or a dict of column to list | tensors or named columns |
| `instances` | a list of rows | tensor data in TF Serving style |

The 1.x payload (`{"columns": ..., "data": ...}` with no wrapper key) gets the 400 above.

## Other health routes

`/ping` and `/health` return 200 when the model has loaded. `/version` returns the MLflow version. Point a load balancer at `/ping`.

## Docker and Kubernetes

`mlflow models build-docker` builds an image that runs the same server. We did not run it. Two things changed that older guides get wrong:

- **MLServer** (`--enable-mlserver`) was removed in 3.13.
- The official **Kubernetes and KServe tutorial** is gone from the latest docs. It last appears in the 3.12.0 docs, and the latest page redirects to the Helm chart for the tracking server, which is a different thing.

KServe can still run an MLflow model, through its own runtime. The [Kubeflow track](lesson:kubeflow/serving-and-mlflow-bridges) covers what its docs say.

## Safety

`--host 0.0.0.0` makes the server reachable from the network and adds no login. The help text says it "is NOT a security setting". Put a proxy with authentication in front of it.

:::check Why does the bad request return 400 and not 500?
The server checks the payload shape before it reaches your model, so the fault is the caller's, not the model's.
:::
