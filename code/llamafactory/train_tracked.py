"""Train with LLaMA-Factory and record what you need to repeat the run, in one MLflow run.

    python train_tracked.py configs/sft_identity.yaml                 # the run from the lesson
    python train_tracked.py configs/sft_identity.yaml lora_rank=16    # same, one setting changed

We open the run first and log the config, the data version and the code version. Then we pass
its id to the training process in MLFLOW_RUN_ID. Hugging Face's MLflow callback, which LLaMA-Factory
uses for `report_to: mlflow`, reattaches to that run and adds the loss curve. Kubeflow's MLflow
plugin hands each pipeline step an id the same way.
"""
import json
import os
import shutil
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import mlflow
import pandas as pd
import yaml
from huggingface_hub import HfApi

HERE = Path(__file__).parent.resolve()
CLI = shutil.which("llamafactory-cli", path=str(Path(sys.executable).parent)) or "llamafactory-cli"
os.environ.setdefault("MLFLOW_TRACKING_URI", f"sqlite:///{HERE / 'mlflow.db'}")  # no server needed


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True).stdout.strip()
    except FileNotFoundError:  # no git in the image: pass GIT_COMMIT instead
        return "unknown"


if __name__ == "__main__":
    config_path, overrides = Path(sys.argv[1]), sys.argv[2:]
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config.update(dict(o.split("=", 1) for o in overrides))
    data_file = HERE / config["dataset_dir"] / json.loads(
        (HERE / config["dataset_dir"] / "dataset_info.json").read_text(encoding="utf-8"))[config["dataset"]]["file_name"]

    given = os.environ.get("MLFLOW_RUN_ID")  # set by KFP's MLflow plugin, or by our pipeline step
    if not given:  # MLflow refuses to resume a run from another experiment while one is set
        mlflow.set_experiment("nori-sft")
    with mlflow.start_run(run_id=given, run_name=None if given else " ".join(overrides) or "baseline") as run:
        # every setting, LoRA ones included. Prefixed: the callback logs some of the same names, and a param can't change
        mlflow.log_params({f"lf.{k}": v for k, v in config.items()})
        mlflow.log_artifact(str(config_path), "config")
        rows = [json.loads(line) for line in data_file.read_text(encoding="utf-8").splitlines()]
        dataset = mlflow.data.from_pandas(pd.DataFrame(rows), source=str(data_file), name=config["dataset"])
        mlflow.log_input(dataset, context="training")
        mlflow.set_tags({
            "git_commit": os.environ.get("GIT_COMMIT") or git("rev-parse", "--short", "HEAD") + ("-dirty" if git("status", "--porcelain", ".") else ""),
            "base_model": config["model_name_or_path"],
            "base_model_revision": HfApi().model_info(config["model_name_or_path"]).sha,
            "data_digest": dataset.digest,
            **{f"version.{p}": version(p) for p in ["llamafactory", "transformers", "peft", "torch"]},
        })

    env = {**os.environ, "MLFLOW_RUN_ID": run.info.run_id}  # the id alone says where to log; no experiment name
    # run_name: the callback resumes the run under this name; passing ours keeps the name we chose
    p = subprocess.run([CLI, "train", str(config_path), *overrides, f"run_name={run.info.run_name}"], cwd=HERE, env=env)

    with mlflow.start_run(run_id=run.info.run_id):
        out = HERE / config["output_dir"]
        for f in ["adapter_config.json", "adapter_model.safetensors", "training_loss.png", "all_results.json"]:
            if (out / f).exists():
                mlflow.log_artifact(str(out / f), "adapter" if f.startswith("adapter") else "results")
        if p.returncode:
            mlflow.set_tag("status", "train_failed")
    finished = mlflow.get_run(run.info.run_id)
    print("\nrun", run.info.run_id, "status", finished.info.status)
    print("metrics:", {k: round(v, 4) for k, v in finished.data.metrics.items() if k.startswith("train")})
    sys.exit(p.returncode)
