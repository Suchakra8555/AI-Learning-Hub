---
title: A tracked training run with MLflow
summary: Train the Nori adapter from one YAML, and make MLflow record everything needed to repeat it - config, data digest, code commit, library versions, base-model revision, loss curve, adapter. Two MLflow behaviours we tested along the way.
time: 25 min
---

:::warn The training itself was not run
The real run (Qwen2.5-0.5B on a CPU) was never started. The laptop was short of memory (two smaller jobs were stopped for that), and the track was finished without it. The config, the script and the two MLflow tests below are real. The loss values and timings are not shown because we do not have them. Run it yourself and you will be the first to see them.
:::

## The config

`code/llamafactory/configs/sft_identity.yaml` is the official `qwen3_lora_sft.yaml` with the changes listed in its header. The ones that matter:

```yaml
model_name_or_path: Qwen/Qwen2.5-0.5B-Instruct
template: qwen
dataset: nori_train
dataset_dir: data
cutoff_len: 256
gradient_accumulation_steps: 4
num_train_epochs: 5.0
learning_rate: 2.0e-4
bf16: false
report_to: mlflow
```

28 rows, a batch of 1 and accumulation of 4 give 7 optimizer steps per epoch, 35 in total. Five passes over the data is a lot for real work. For 28 short rows, it is what it takes for a small model to pick up a new name.

## What `report_to: mlflow` gives you, and what it does not

LLaMA-Factory has no MLflow code of its own. `report_to` is a Hugging Face trainer setting, and the trainer's `MLflowCallback` does the logging: training arguments as params, and loss and learning rate per step as metrics.

That is not enough to repeat a run. The callback logs Hugging Face's settings. It does not log LLaMA-Factory's own, such as `lora_rank` or `dataset`, and it records nothing about the data, the code or the exact base model. So `code/llamafactory/train_tracked.py` opens the run first and adds those:

```python
mlflow.log_params({f"lf.{k}": v for k, v in config.items()})   # every YAML key
mlflow.log_artifact(str(config_path), "config")                 # the file itself
dataset = mlflow.data.from_pandas(pd.DataFrame(rows), source=str(data_file), name=config["dataset"])
mlflow.log_input(dataset, context="training")                   # rows + digest
mlflow.set_tags({
    "git_commit": ...,              # with -dirty if files changed since the commit
    "base_model": config["model_name_or_path"],
    "base_model_revision": HfApi().model_info(config["model_name_or_path"]).sha,
    "data_digest": dataset.digest,
    **{f"version.{p}": version(p) for p in ["llamafactory", "transformers", "peft", "torch"]},
})
```

The `lf.` prefix is there because MLflow params cannot change once logged. The callback logs its own `report_to` (as a list) and other overlapping names. Logging ours under the same names would make the second write fail.

## Handing the run to the trainer

Then the script starts training with the run's id in the environment:

```python
env = {**os.environ, "MLFLOW_RUN_ID": run.info.run_id}
subprocess.run([CLI, "train", str(config_path), *overrides, f"run_name={run.info.run_name}"], env=env)
```

Read the callback's source and you find that it never passes a run id itself. It calls `mlflow.start_run()`, and MLflow reads `MLFLOW_RUN_ID` from the environment and continues that run. So the loss curve lands in the same run as our config and data. [Kubeflow's MLflow plugin](lesson:kubeflow/serving-and-mlflow-bridges) uses exactly this variable to hand each pipeline step its run, which is why the [pipeline lesson](lesson:llamafactory/pipeline-on-kubeflow) reuses this script unchanged.

After training, the script logs the adapter files under `adapter/` and the loss plot under `results/`. Later steps download the adapter from MLflow, not from the local disk.

## Two things we tested

These came from small scripts against a throwaway MLflow database, with MLflow 3.18.0.

**1. Resuming with a name renames the run.** The callback calls `start_run(run_name=args.run_name)`. We resumed a run named "kfp task" that way with the name `saves/nori/lora/sft`:

```text
after callback-style start_run, name: saves/nori/lora/sft
```

In transformers 5.6, `run_name` defaults to nothing, so by default nothing is renamed. LLaMA-Factory warns about it: "Consider setting --run_name for better experiment tracking clarity." Our script passes the run's own name, so the warning goes away and the name cannot drift.

**2. MLflow refuses to resume a run from another experiment.** We created a run in `KFP-Default`, called `set_experiment("nori-sft")`, then resumed the first run:

```text
MlflowException: Cannot start run with ID ... because active experiment ID does not match environment run ID.
```

Without `set_experiment`, resuming worked. A pipeline run lives in the pipeline's experiment, not ours, so the scripts only set an experiment when they create a new run. They also never set `MLFLOW_EXPERIMENT_NAME` for the trainer, because the callback calls `set_experiment` when it sees that variable.

## Run it

```bash
cd code/llamafactory
python make_dataset.py
python train_tracked.py configs/sft_identity.yaml
python train_tracked.py configs/sft_identity.yaml lora_rank=16     # a second run to compare
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

With no `MLFLOW_TRACKING_URI` set, the scripts use `sqlite:///mlflow.db` in this folder, so you do not need a server. Comparing runs works the way the [MLflow track](lesson:mlflow/tracking-runs-and-search) shows:

```python
mlflow.search_runs(experiment_names=["nori-sft"], order_by=["metrics.train_loss ASC"])
```

`train_loss` is the name the trainer gives the final average loss. We have not confirmed it in a run of this script.

Expect the model to be about 2 GB in 32-bit (0.5 billion weights, 4 bytes each) and the run to need several more for activations and the optimizer. Close browsers first.

:::check The callback already logs the trainer's settings. Why does `train_tracked.py` log the whole YAML again under `lf.`?
The callback logs only Hugging Face's trainer settings, not LLaMA-Factory's (LoRA rank, dataset, template). The prefix avoids clashing with names the callback logs, because a logged param cannot change.
:::

:::check Two runs have the same params but different results. Which tags would you compare first?
`data_digest` (did the rows change?), `base_model_revision` (did the model's weights change under the same name?) and `git_commit` with its `-dirty` flag.
:::
