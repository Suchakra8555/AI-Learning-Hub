"""Compile the wine pipeline to YAML and run it on a standalone KFP cluster.

First:  kubectl port-forward -n kubeflow svc/ml-pipeline-ui 3000:80
Run:    python cluster_run.py
"""
import kfp
from kfp import compiler

from wine_pipeline import wine

compiler.Compiler().compile(wine, "wine_pipeline.yaml")  # the IR YAML: this file is what the cluster runs
client = kfp.Client(host="http://localhost:3000")
run = client.create_run_from_pipeline_package(
    "wine_pipeline.yaml", arguments={"trees": 20}, experiment_name="wine", run_name="wine trees=20"
)
print("run id:", run.run_id)
done = client.wait_for_run_completion(run.run_id, timeout=900)
print("state:", done.state)
