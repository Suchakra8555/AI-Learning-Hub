---
title: What MLflow is now
summary: The parts of MLflow 3, where it keeps your data by default, what changed from 2.x, and which doc pages are out of date.
time: 15 min
---

You trained a model last week and it scored well. Today nobody can say which settings, which data and which code made that score. MLflow is a tool that writes those facts down as you work. This track uses **MLflow 3.18.0** (PyPI upload 2026-11-03), pinned in `code/mlflow/requirements.txt`. It needs Python 3.10 or newer.

## What is in it

MLflow is open source ([docs](https://mlflow.org/docs/latest/)). The docs now have two trees: classic machine learning, and **GenAI** (apps built on language models). The same install covers both.

| Part | What it records or does | Lesson |
| --- | --- | --- |
| Tracking | Runs: parameters, metrics, files | [Tracking runs](lesson:mlflow/tracking-runs-and-search) |
| Models | A model saved with its schema and its Python environment | [Models](lesson:mlflow/models-and-signatures) |
| Model Registry | Named versions with aliases such as `champion` | [Registry](lesson:mlflow/registry-and-aliases) |
| Serving | A local HTTP server for a saved model | [Serving](lesson:mlflow/serving-a-model) |
| Tracking server | One shared place for a team's runs | [Team server](lesson:mlflow/team-server-and-security) |
| Tracing | A record of every step an LLM app took | [Tracing](lesson:mlflow/tracing-an-llm-app) |
| Evaluation and prompts | Scoring an app, and versioning its prompts | [Evaluation](lesson:mlflow/evaluation-and-prompts) |

Databricks sells a managed MLflow. This track covers only the open-source version.

## Where your data goes by default

Older tutorials say MLflow writes to a `./mlruns` folder. That is no longer true. Since 3.7.0 the default is a **SQLite** file (a database in one file) named `mlflow.db` in the folder where you run Python. We checked this on 3.18.0:

```text
tracking uri: sqlite:///E%3A/RAG_Learning_from_local_to_production/code/mlflow/mlflow.db
```

Since 3.13.0 the old file store raises an error unless you set `MLFLOW_ALLOW_FILE_STORE=true`. The command `mlflow migrate-filestore` moves old data into SQLite. Some pages in MLflow's own docs still say `mlruns`. When two pages disagree, run the code and look at `mlflow.get_tracking_uri()`.

Model files do not go in SQLite. They go in a folder next to it (`mlruns/`, even now, for artifacts). SQLite holds the facts about them. The lesson on the [team server](lesson:mlflow/team-server-and-security) separates the two stores.

## What changed from 2.x

MLflow 3 launched as 3.1.0 on 2025-06-10 ([migration notes](https://mlflow.org/docs/latest/ml/mlflow-3/)). The changes you will meet:

- A logged model is now its own object with a `model_id` such as `m-6bbdf7fe...`. You log with `name=`, not `artifact_path=`, and you no longer need a run around it.
- `runs:/<run_id>/model` URIs still work but are deprecated. Use `models:/<model_id>` or `models:/<name>@<alias>`.
- Registry **stages** (Staging, Production) have been deprecated since 2.9.0. Use aliases.
- `mlflow.evaluate` for language models is deprecated. Use `mlflow.genai.evaluate`.
- MLServer serving and the official Kubernetes tutorial were dropped in 3.13.
- Recipes and several old flavors were removed.

Upgrade the client and the server together. A 3.x server reads 2.x data, but not the other way round. To stay on 2.x: `pip install 'mlflow<3'`.

## Run it

```bash
cd code/mlflow
pip install -r requirements.txt
python track_runs.py
mlflow server
```

`mlflow server` starts the UI on port 5000 by default. We ran the scripts and read the database, but did not open the UI in a browser while writing this track. Open `http://127.0.0.1:5000` yourself and look at the `wine-forest` experiment.

:::warn Check which command starts the UI
The older `mlflow ui` command is not in the 3.18 CLI list we printed with `mlflow --help`. Use `mlflow server`.
:::

:::check Your teammate says "MLflow keeps everything in ./mlruns". How do you check?
Print `mlflow.get_tracking_uri()`. On 3.18 the default is `sqlite:///mlflow.db`. Only artifacts such as model files live in a folder.
:::
