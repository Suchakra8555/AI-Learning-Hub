"""Merge the newest adapter that passed the gate, register it, and point aliases at it.

    python register.py            # merge + register the newest run tagged gate=pass, alias it `staging`
    python register.py <run_id>   # the same for one run (it must be tagged gate=pass)
    python register.py promote    # move `champion` to whatever `staging` points at

The merge uses LLaMA-Factory's own examples/merge_lora/qwen3_lora_sft.yaml with our paths on top.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import mlflow
from mlflow import MlflowClient

HERE = Path(__file__).parent.resolve()
CLI = shutil.which("llamafactory-cli", path=str(Path(sys.executable).parent)) or "llamafactory-cli"
MERGE_YAML = HERE / "vendor" / "LlamaFactory" / "examples" / "merge_lora" / "qwen3_lora_sft.yaml"
os.environ.setdefault("MLFLOW_TRACKING_URI", f"sqlite:///{HERE / 'mlflow.db'}")
NAME = "nori"
client = MlflowClient()

if sys.argv[1:] == ["promote"]:
    staging = client.get_model_version_by_alias(NAME, "staging")
    client.set_registered_model_alias(NAME, "champion", staging.version)
    print(f"champion -> version {staging.version}")
    sys.exit()

runs = ([mlflow.get_run(sys.argv[1])] if sys.argv[1:] else
        mlflow.search_runs(experiment_names=["nori-sft"], filter_string="tags.gate = 'pass'",
                           order_by=["start_time DESC"], max_results=1, output_format="list"))
if not runs or runs[0].data.tags.get("gate") != "pass":
    sys.exit("No run has passed the gate. Run evaluate.py first.")
run = runs[0]
p = run.data.params
merged = HERE / "saves" / "nori" / "merged" / run.info.run_id[:8]

subprocess.run([CLI, "export", str(MERGE_YAML),
                f"model_name_or_path={p['lf.model_name_or_path']}", f"template={p['lf.template']}",
                f"adapter_name_or_path={mlflow.artifacts.download_artifacts(run_id=run.info.run_id, artifact_path='adapter')}",
                f"export_dir={merged}"], check=True)

with mlflow.start_run(run_id=run.info.run_id):  # the model sits next to the run that trained it
    info = mlflow.transformers.log_model(transformers_model=str(merged), task="text-generation",
                                         name="merged", registered_model_name=NAME)
v = info.registered_model_version
for key in ["base_model", "base_model_revision", "data_digest", "git_commit", "version.llamafactory"]:
    client.set_model_version_tag(NAME, v, key, run.data.tags[key])
client.set_model_version_tag(NAME, v, "holdout_says_nori", run.data.metrics["holdout_says_nori"])
client.set_registered_model_alias(NAME, "staging", v)

print(f"\nregistered {NAME} version {v} from run {run.info.run_name} ({run.info.run_id[:8]})")
print("merged files:", sorted(f.name for f in merged.iterdir()))
print("aliases:", client.get_registered_model(NAME).aliases)
