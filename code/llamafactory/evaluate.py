"""Score the base model and the tuned one on the hold-out questions, and gate the release.

    python evaluate.py            # the newest run in the nori-sft experiment
    python evaluate.py <run_id>   # a specific run

The adapter is downloaded from the training run in MLflow, so MLflow is the record of what was
trained. Exits with code 1 when the gate fails, so a pipeline step or CI job stops there.
"""
import json
import os
import sys
from pathlib import Path

import mlflow
from llamafactory.chat import ChatModel
from mlflow.genai.scorers import scorer

HERE = Path(__file__).parent.resolve()
os.environ.setdefault("MLFLOW_TRACKING_URI", f"sqlite:///{HERE / 'mlflow.db'}")
os.environ.setdefault("MLFLOW_GENAI_EVAL_MAX_WORKERS", "1")  # one model, one CPU: ask one question at a time
# KFP's MLflow plugin hands every step a run id. Ours would make start_run() resume it in the wrong experiment.
os.environ.pop("MLFLOW_RUN_ID", None)
GATE = 0.8  # the tuned model must name itself on at least 80% of hold-out questions, and beat the base


@scorer
def says_nori(outputs) -> bool:
    return "Nori" in outputs


@scorer
def says_northwind(outputs) -> bool:
    return "Northwind" in outputs


def score(run_name, model_args, data):
    chat = ChatModel({**model_args, "infer_backend": "huggingface", "do_sample": False, "max_new_tokens": 64})
    answers = {}

    def predict(question):
        answers[question] = chat.chat([{"role": "user", "content": question}])[0].response_text
        return answers[question]

    with mlflow.start_run(run_name=run_name):
        result = mlflow.genai.evaluate(data=data, predict_fn=predict, scorers=[says_nori, says_northwind])
    return result.metrics["says_nori/mean"], answers


if __name__ == "__main__":
    train = (mlflow.get_run(sys.argv[1]) if sys.argv[1:] else
             mlflow.search_runs(experiment_names=["nori-sft"], order_by=["start_time DESC"],
                                max_results=1, output_format="list")[0])
    p = train.data.params
    base = {"model_name_or_path": p["lf.model_name_or_path"], "template": p["lf.template"]}
    # the adapter the run logged, not whatever is on this disk: on a cluster, steps share no disk
    adapter = mlflow.artifacts.download_artifacts(run_id=train.info.run_id, artifact_path="adapter")
    tuned = {**base, "adapter_name_or_path": adapter, "finetuning_type": "lora"}
    rows = [json.loads(line) for line in (HERE / "data" / "nori_holdout.jsonl").read_text(encoding="utf-8").splitlines()]
    data = [{"inputs": {"question": r["messages"][0]["content"]}} for r in rows]

    mlflow.set_experiment("nori-eval")
    base_rate, base_answers = score("base", base, data)
    tuned_rate, tuned_answers = score(f"tuned {train.info.run_name}", tuned, data)
    passed = tuned_rate >= GATE and tuned_rate > base_rate

    client = mlflow.MlflowClient()  # put the verdict on the training run itself, whatever experiment it is in
    client.log_metric(train.info.run_id, "holdout_says_nori", tuned_rate)
    client.log_metric(train.info.run_id, "holdout_says_nori_base", base_rate)
    client.set_tag(train.info.run_id, "gate", "pass" if passed else "fail")

    for q in tuned_answers:
        print(f"Q: {q}\n  base : {base_answers[q][:90]}\n  tuned: {tuned_answers[q][:90]}")
    print(f"\nsays Nori: base {base_rate:.0%}, tuned {tuned_rate:.0%} (run {train.info.run_name})")
    print("gate:", "PASS" if passed else f"FAIL (needs >= {GATE:.0%} and better than base)")
    sys.exit(0 if passed else 1)
