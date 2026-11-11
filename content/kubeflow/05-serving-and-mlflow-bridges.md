---
title: Serving with KServe, and where MLflow fits
summary: InferenceService, the two request formats, the two modes, the Hub registry, and the two official bridges between Kubeflow and MLflow. Read from the docs, not run.
time: 20 min
---

:::warn Not run
No KServe or Hub install was run for this lesson. The facts come from the KServe and Kubeflow docs and are listed with gaps in `research/kubeflow.md`.
:::

[MLflow serving](lesson:mlflow/serving-a-model) starts one server from a command. **KServe** (0.21.0, 2026-09-25) makes a model a Kubernetes object, so the cluster handles replicas, rollouts and health ([docs](https://kserve.github.io/website/)).

## One object

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: mlflow-v2-wine-classifier
spec:
  predictor:
    model:
      modelFormat:
        name: mlflow
      protocolVersion: v2
      storageUri: "gs://kfserving-examples/models/mlflow/wine"
```

`modelFormat` says what the files are. KServe picks a matching **ServingRuntime**, a server image that understands that format. `storageUri` says where the files are. The `kserve-mlserver` runtime lists `mlflow` versions 1 and 2, and only the **v2** protocol. The example asks for 100m CPU and 512 Mi.

## Two request formats

- **v1**: `{"instances": [[...]]}`.
- **Open Inference Protocol (v2)**: `{"inputs": [{"name": ..., "shape": [...], "datatype": "FP64", "data": [...]}]}`, sent to `/v2/models/<name>/infer`.

Compare these with MLflow's four keys. They solve the same problem with different shapes. We did not read the full v2 body for the MLflow wine example.

## Two modes

| Mode | Needs | Gives you |
| --- | --- | --- |
| Standard (plain Deployments) | cert-manager | the lighter install |
| Knative | Knative and Istio | scale to zero, `canaryTrafficPercent` rollouts |

The docs call the lighter one "Standard"; we did not confirm that it was officially renamed from "RawDeployment". For a laptop, start with Standard and accept that canary splits and scale-to-zero wait for Knative.

## LLMs

For language models KServe has a Hugging Face runtime that uses vLLM and speaks the OpenAI API. The docs example (`hf://Qwen/Qwen2.5-0.5B-Instruct`) asks for 1 GPU. A CPU image is picked when no GPU is requested, but running it on CPU is not shown as tested. See [serving engines](lesson:inference/serving-engines).

## The registry

**Kubeflow Hub** (0.3.18) stores `RegisteredModel` to `ModelVersion` to `ModelArtifact`. The Python package is `model-registry`. KServe can read from it with a `model-registry://name/version` storage URI. The docs are inconsistent about Hub's maturity: one page says "Graduated", another "opt-in alpha".

## Two official bridges to MLflow

1. **KFP's MLflow plugin.** An admin enables it in the API server config (`plugins.mlflow`). Each pipeline run then becomes an MLflow run and each task a nested run. KFP can inject `MLFLOW_TRACKING_URI`, `MLFLOW_RUN_ID` and `MLFLOW_EXPERIMENT_ID` into components, so `mlflow.autolog()` works inside a step. Cached steps still get a new MLflow run.
2. **KServe serving an MLflow model**, as above.

The docs also mention a "Kubeflow MLflow Integration" project. We could not find its repo (the URL returned 404), so we do not know what it is.

## Pick one

| You have | Use |
| --- | --- |
| One machine, one team | MLflow Tracking, Registry and `models serve` |
| Kubernetes and many teams | KFP and KServe, with MLflow for tracking if people already use it |

:::check Your MLflow model is already in a registry. Which two things must be true before KServe can serve it with `modelFormat: mlflow`?
The model files (with `MLmodel`) must be reachable at `storageUri`, and the runtime used must speak protocol v2.
:::
