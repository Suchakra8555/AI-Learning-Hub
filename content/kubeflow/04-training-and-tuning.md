---
title: Distributed training and tuning
summary: Trainer's TrainJob and Python SDK, the three places the same code can run, and why Katib is on its way out. Read from the docs, not run.
time: 20 min
---

:::warn Not run
We did not run Trainer or Katib. The cluster lesson shows why we stopped at one cluster component. Everything below is from the docs (see `research/kubeflow.md`).
:::

## Trainer

Fine-tuning from the [LLMOps track](lesson:llmops/sft-lora-dpo) often needs more than one machine. **Kubeflow Trainer** (v2.4.0, 2026-11-06) runs a training script on many nodes ([docs](https://www.kubeflow.org/docs/components/trainer/)). You create one `TrainJob`. It points at a **runtime**, a template your platform team set up for a framework. Underneath, Trainer uses **JobSet** to start the pods (JobSet 0.13.0 is bundled).

Built-in `ClusterTrainingRuntime`s: `torch-distributed`, `deepspeed-distributed`, `jax-distributed`, `mlx-distributed`, `xgboost-distributed`, and TorchTune recipes `torchtune-llama3.2-1b`, `torchtune-llama3.2-3b`, `torchtune-qwen2.5-1.5b`.

You rarely write YAML. The Python SDK (`pip install -U kubeflow`):

```python
from kubeflow.trainer import TrainerClient, CustomTrainer

job = TrainerClient().train(trainer=CustomTrainer(
    func=train_pytorch, num_nodes=4,
    resources_per_node={"cpu": 3, "memory": "16Gi", "gpu": 1}))
TrainerClient().get_job_logs(job, follow=True)
```

### Three places to run the same code

The docs say switching backend changes only the configuration:

| Backend | Runs on | Limit |
| --- | --- | --- |
| `LocalProcessBackendConfig()` | a Python venv on your machine | one node, no distributed training |
| `ContainerBackendConfig(container_runtime="docker")` | one Docker container per node | one machine |
| `KubernetesBackendConfig(namespace=...)` | a cluster | needs Trainer installed |

CPU-only PyTorch with `gloo` is shown in the docs, so a no-GPU laptop can practise the distributed mechanics. We did not check whether the Docker backend works on Windows. Given that KFP's `DockerRunner` failed there, test it before you plan around it.

The TorchTune recipes need GPUs (the docs example uses 2), support LoRA since Trainer v2.1.0, and do not support multi-node fine-tuning.

### Migrating from PyTorchJob

`kubeflow.org/v1` `PyTorchJob` becomes `trainer.kubeflow.org/v1alpha1` `TrainJob`. Master and Worker replicas become `trainer.numNodes`, and you add `runtimeRef.name: torch-distributed`. The legacy Training Operator is gone from distribution 26.10.0.

## Tuning

**Katib** searched settings by running many **Trials** (one training each) under one **Experiment**. It is **deprecated since 2026-11-01** and will be archived 2027-11-01.

The replacement is in the SDK (`from kubeflow.optimizer import OptimizerClient, Search, TrialConfig`):

```python
OptimizerClient().optimize(
    trial_template=TrainJobTemplate(trainer=CustomTrainer(func=train)),
    search_space={"lr": Search.loguniform(1e-5, 1e-2)},
    trial_config=TrialConfig(num_trials=10, parallel_trials=2),
    objectives=[Objective(name="accuracy", type="maximize")])
```

It needs Trainer 2.4 or newer, is alpha, and supports only random search. The SDK page still says "Kubeflow uses Katib under the hood". Which engine runs it is unclear in the docs, so check before you depend on either.

:::check You have one GPU server and a Mac. Where do you test your `train()` function first?
With `LocalProcessBackendConfig` on the Mac. It runs on one node and needs no cluster.
:::
