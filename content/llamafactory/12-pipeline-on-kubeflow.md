---
title: The whole run as a Kubeflow pipeline
summary: Train, evaluate and register as three KFP steps that pass each other only an MLflow run id. A CPU image that builds the same data digest on Linux as on Windows, how KFP's MLflow plugin plugs into the same scripts, and what we did not get to run.
time: 25 min
---

:::warn What was run
The Docker image was built, and its data step printed the same digests as the laptop. The pipeline itself was not run, locally or on a cluster. The [cluster lesson](lesson:kubeflow/pipelines-on-a-cluster) shows why the cluster part is hard on this laptop.
:::

Running four scripts by hand works until someone forgets one, or runs them in the wrong order, or on different data. A pipeline makes the order part of the code, and every run of it a record. [Your first pipeline](lesson:kubeflow/your-first-pipeline) introduced KFP components. This lesson wraps the Nori scripts in them.

## Steps that share no disk

On a cluster every step is its own pod. The training step's `saves/` folder does not exist for the evaluation step. So our steps pass one thing to each other, the MLflow run id, and fetch everything else from MLflow:

```python
@dsl.component(base_image=IMAGE)
def train(config: str) -> str:
    import os, subprocess, mlflow
    run_id = os.environ.get("MLFLOW_RUN_ID")      # on a cluster with KFP's MLflow plugin, this step's run
    if not run_id:                                # locally nobody hands us one, so make it the same way
        mlflow.set_experiment("nori-sft")
        with mlflow.start_run(run_name="pipeline") as run:
            run_id = run.info.run_id
    subprocess.run(["python", "train_tracked.py", config], cwd="/app",
                   env={**os.environ, "MLFLOW_RUN_ID": run_id}, check=True)
    return run_id

@dsl.component(base_image=IMAGE)
def evaluate(run_id: str) -> str:
    subprocess.run(["python", "evaluate.py", run_id], cwd="/app", check=True)  # exit 1 = gate failed
    return run_id

@dsl.pipeline(name="nori-lifecycle")
def nori(config: str = "configs/sft_identity.yaml"):
    trained = train(config=config)
    gated = evaluate(run_id=trained.output)
    register(run_id=gated.output)
```

The components are thin. They call the same scripts you ran by hand, so there is one version of the logic, not a laptop version and a pipeline version.

**The gate is a failing step, not a branch.** KFP has `dsl.If`, but the local runner does not run branches. A step that exits with code 1 stops everything after it, locally and on a cluster. `register` runs only if `evaluate` passed.

## The bridge to MLflow

Kubeflow's MLflow plugin, once an admin enables it, makes each pipeline run an MLflow run and each step a nested run. It puts `MLFLOW_RUN_ID`, `MLFLOW_TRACKING_URI` and `MLFLOW_EXPERIMENT_ID` into every step's environment ([the bridges](lesson:kubeflow/serving-and-mlflow-bridges)).

Our scripts were written for that:

| Script | With a handed-in `MLFLOW_RUN_ID` |
|---|---|
| `train_tracked.py` | Uses it as the training run, sets no experiment, passes it to the Hugging Face callback |
| `evaluate.py` | Removes it, so its own evaluation runs are new runs, not the step's |
| `register.py` | Works by explicit run id, so the handed-in one does not matter |

Two of those rows exist because we tested MLflow first ([tracking lesson](lesson:llamafactory/sft-with-mlflow-tracking)). Resuming a run while a different experiment is set fails with "active experiment ID does not match environment run ID". And `start_run()` with no id quietly resumes whatever `MLFLOW_RUN_ID` says. What we did not test is the plugin itself, so treat the table as the design, not as a result.

## The image

Components need an image with LLaMA-Factory in it. The official `hiyouga/llamafactory` image is built on CUDA 12.4, so it is useless on a CPU node. `code/llamafactory/Dockerfile` builds a CPU one:

```dockerfile
FROM python:3.12-slim
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
COPY llamafactory/vendor/LlamaFactory /app/vendor/LlamaFactory
RUN pip install --no-cache-dir -e vendor/LlamaFactory "mlflow==3.18.0" "kfp==2.18.0"
...
RUN python make_dataset.py
ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=$GIT_COMMIT
```

- **CPU wheels.** The default Linux PyTorch wheel brings CUDA libraries a GPU-less node cannot use. PyTorch's CPU index avoids them.
- **The data is built into the image**, so every step sees the same files. The build printed the same digests as the Windows laptop: `nori_train.jsonl sha256 4d59031d09f4`. That match is not luck; it is the line-ending fix from [your own data](lesson:llamafactory/your-own-data).
- **The git commit is a build argument**, because the slim image has no git. `train_tracked.py` reads `GIT_COMMIT` before trying `git`.
- **The build context is `code/`**, which also holds a multi-gigabyte `.venv`. `Dockerfile.dockerignore` lists only what the image copies. Docker uses a file with that name in place of `.dockerignore` for this one Dockerfile only.

```bash
cd code
docker build -f llamafactory/Dockerfile --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) -t nori-lf:0.9.5 .
```

On our laptop it took 6 minutes 23 seconds and made a 2.52 GB image.

## Running it

**Locally.** Both KFP local runners fail on native Windows, as [your first pipeline](lesson:kubeflow/your-first-pipeline) found, so the pipeline runs inside the image with `SubprocessRunner`. The steps then reach an MLflow server on the host:

```bash
mlflow server --host 0.0.0.0 --port 5000 --allowed-hosts "host.docker.internal:5000,localhost:5000"
docker run --rm -e MLFLOW_TRACKING_URI=http://host.docker.internal:5000 \
    -v hf-cache:/root/.cache/huggingface nori-lf:0.9.5 python pipeline.py
```

`--allowed-hosts` is needed because since 3.5 the server checks the `Host` header, and by default accepts only localhost and private IP addresses ([team server lesson](lesson:mlflow/team-server-and-security)). The container calls the host by the name `host.docker.internal`, so that name must be on the list. The `hf-cache` volume keeps the 1 GB base model between runs. We have not checked the exact `--allowed-hosts` value against a live server.

**On a cluster.** `python pipeline.py compile` writes `nori_pipeline.yaml`, the file a KFP cluster runs. The image would have to be pushed to a registry the cluster can pull from, and the MLflow server would need an artifact store every pod can reach. That is the [team server](lesson:mlflow/team-server-and-security) setup, not a local SQLite file.

We planned one retry of standalone KFP on kind, with released images and a longer startup probe, after the earlier attempt failed. We did not get to it.

:::check Why does each step return the run id instead of returning the adapter as a KFP artifact?
Everything the later steps need (config, data digest, adapter, scores, gate tag) is already in that MLflow run. One id is enough to find it, and the scripts work the same outside a pipeline.
:::

:::check The evaluate step fails with exit code 1. What happens to the register step, and why is that the behaviour you want?
It never runs, because a failed step stops the steps that depend on it. A model that failed the gate never becomes a registered version.
:::
