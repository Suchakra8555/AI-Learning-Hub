---
title: What Kubeflow is in 2026
summary: The projects inside Kubeflow, which ones are deprecated or renamed, and what you can run on a laptop. Read from the official docs and release pages.
time: 15 min
---

MLflow records and serves models. **Kubeflow** is a different kind of tool: it runs machine-learning work on **Kubernetes**, the system that schedules containers across machines. If your team already runs Kubernetes, Kubeflow makes training, pipelines and serving into Kubernetes objects.

Many tutorials are out of date. This page is built from the project's own docs and GitHub release pages as of 2026-11-11 ([docs](https://www.kubeflow.org/docs/)). Details are in `research/kubeflow.md`, with the gaps we found.

## The projects

| Project | Job | Version we found |
| --- | --- | --- |
| Kubeflow Pipelines (KFP) | Multi-step workflows as code | 2.18.0 (2026-10-28) |
| Kubeflow Trainer | Distributed training jobs (`TrainJob`) | v2.4.0 (2026-11-06) |
| Katib | Hyperparameter search | v0.19.0, **deprecated** |
| Kubeflow Hub (was Model Registry) | A catalog of models | 0.3.18 |
| KServe | Model serving | 0.21.0 |
| Spark Operator, Workspaces, Dashboard | Data jobs, notebooks, a web front door | not checked |

KServe is listed as an "ecosystem" project, and its own README calls it a CNCF incubating project. You can install each project alone, or all of them together as the **Community Distribution** (release 26.10.0, 2026-11-06).

## What changed that old tutorials miss

- Kubeflow graduated in the CNCF on 2026-08-17.
- The `kubeflow/manifests` repo is now `kubeflow/community-distribution`. Releases are named by year and month (26.03, 26.10).
- Model Registry is now called Kubeflow Hub. The Python package is still `model-registry`.
- **Katib was deprecated on 2026-11-01** and will be archived on 2027-11-01. The replacement is Trainer's `OptimizationJob`, which is alpha, needs Trainer 2.4 or newer, and supports random search only.
- The legacy Training Operator (`PyTorchJob`, `TFJob`) was removed from 26.10.0. `TrainJob` replaces it.
- Notebooks v1 is off by default and scheduled for removal in 27.03.
- SeaweedFS replaced MinIO as the default object store in KFP from 2.15.
- Argo Workflows 3.x is deprecated for KFP 2.x and will not work with KFP 3.0.

## How it maps to the lifecycle

Prepare data and run steps: **Pipelines**. Train on many machines: **Trainer**. Tune: Trainer's new optimizer. Keep track of versions: **Hub**. Serve: **KServe**. The [LLMOps track](lesson:llmops/prompt-rag-or-fine-tune) says when to fine-tune. This track covers how a team runs it on Kubernetes.

## What you can run on a laptop

The docs recommend 16 GB of RAM and 8 cores for the full distribution. Its own resource table adds up to about 12 GB of RAM, 4 cores and 65 GB of storage, and its kind script builds three nodes and assumes Linux. We did not try the full install on our 16 GB Windows machine (8 GB given to Docker). Our own attempt at *standalone* Pipelines on one kind node is in [the cluster lesson](lesson:kubeflow/pipelines-on-a-cluster), and it did not finish.

What did run, with no cluster: a KFP pipeline on the local runner, in [the next lesson](lesson:kubeflow/your-first-pipeline).

## Do you need it?

If nobody on your team runs Kubernetes, you do not need Kubeflow. MLflow plus a script on one machine covers tracking, a registry and serving. Kubeflow earns its weight when you need many training nodes, GPU scheduling shared across teams, or a platform other people deploy to.

:::check A tutorial tells you to tune with Katib. What do you do?
Check the date. Katib was deprecated on 2026-11-01. Use Trainer's `OptimizationJob` and note it is alpha and random-search only.
:::
