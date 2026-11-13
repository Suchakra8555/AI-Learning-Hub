"""The Nori lifecycle as a Kubeflow pipeline: train -> evaluate (the gate) -> register.

Steps pass one thing to each other: the MLflow run id. Everything else (config, data version,
adapter, scores, the gate verdict) lives in that run. On a cluster this is what lets steps that
share no disk work together.

Run (inside the image, because both kfp.local runners fail on native Windows):
  docker run --rm -e MLFLOW_TRACKING_URI=http://host.docker.internal:5000 \
      -v hf-cache:/root/.cache/huggingface nori-lf:0.9.5 python pipeline.py
Compile only:  python pipeline.py compile    (writes nori_pipeline.yaml for a cluster)
"""
import sys

from kfp import compiler, dsl, local

IMAGE = "nori-lf:0.9.5"  # see Dockerfile


@dsl.component(base_image=IMAGE)
def train(config: str) -> str:
    import os
    import subprocess

    import mlflow
    run_id = os.environ.get("MLFLOW_RUN_ID")  # on a cluster with KFP's MLflow plugin, this step's nested run
    if not run_id:  # locally nobody hands us one, so make it the same way
        mlflow.set_experiment("nori-sft")
        with mlflow.start_run(run_name="pipeline") as run:
            run_id = run.info.run_id
    subprocess.run(["python", "train_tracked.py", config], cwd="/app",
                   env={**os.environ, "MLFLOW_RUN_ID": run_id}, check=True)
    return run_id


@dsl.component(base_image=IMAGE)
def evaluate(run_id: str) -> str:
    import subprocess
    subprocess.run(["python", "evaluate.py", run_id], cwd="/app", check=True)  # exit 1 = gate failed = stop here
    return run_id


@dsl.component(base_image=IMAGE)
def register(run_id: str):
    import subprocess
    subprocess.run(["python", "register.py", run_id], cwd="/app", check=True)


@dsl.pipeline(name="nori-lifecycle")
def nori(config: str = "configs/sft_identity.yaml"):
    trained = train(config=config)
    gated = evaluate(run_id=trained.output)
    register(run_id=gated.output)  # runs only if the gate step succeeded


if __name__ == "__main__":
    if sys.argv[1:] == ["compile"]:
        compiler.Compiler().compile(nori, "nori_pipeline.yaml")
        print("wrote nori_pipeline.yaml")
    else:
        local.init(runner=local.SubprocessRunner(use_venv=False))  # shortcut: one image for all steps
        nori()
