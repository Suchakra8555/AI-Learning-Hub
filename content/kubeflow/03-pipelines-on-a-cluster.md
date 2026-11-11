---
title: Pipelines on a cluster, and what went wrong on ours
summary: Install standalone Kubeflow Pipelines on a kind cluster, what the install actually pulled, and an honest account of the API server that never became ready. The run itself was not completed.
time: 20 min
---

:::warn This lesson ends in a failure
We installed standalone Kubeflow Pipelines on a local Kubernetes cluster and did not get a pipeline to run on it. The install commands and what we saw are real. Everything about running and the features below comes from the docs.
:::

## The cluster

**kind** runs a Kubernetes node as a Docker container. The first `kind create cluster` failed on our machine inside `kubeadm init`. Docker Desktop with WSL2 here reports cgroup v1, and we guess the default node image wanted cgroup v2, but we did not confirm that. Pinning the 1.34 node image worked:

```bash
kind create cluster --name ml --image kindest/node:v1.34.11@sha256:44e222ee...
```

(kind v0.33.0. The docs' own kind script targets Kubernetes 1.37.) Creating the cluster took about 2.5 minutes the second time.

## Install standalone Pipelines

From the docs ([install](https://www.kubeflow.org/docs/components/pipelines/operator-guides/installation/)), `PIPELINE_VERSION=2.18.0`:

```bash
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=$PIPELINE_VERSION"
kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/dev?ref=$PIPELINE_VERSION"
```

The docs say this takes "about 3 minutes". It created 16 deployments. On our machine image pulls alone took more than 15 minutes (one pull waited 2 min 34 s).

### The `ref` does not pin the images

We listed the images after the install:

```text
ml-pipeline                 ghcr.io/kubeflow/kfp-api-server:master
ml-pipeline-ui              ghcr.io/kubeflow/kfp-frontend:master
workflow-controller         quay.io/argoproj/workflow-controller:v4.1.6
mysql                       mysql:8.4
seaweedfs                   ghcr.io/chrislusf/seaweedfs:4.51@sha256:f7a49e3f...
```

`?ref=2.18.0` fixed the **manifests**, but the KFP images are tagged `:master`. In `env/dev` the version you asked for and the code you got can differ. We did not find a warning on the install page. If you need repeatable installs, check the image tags and pin them yourself.

## What failed

After 20 minutes:

- 12 of 16 pods were ready.
- `ml-pipeline` (the API server) restarted 4 times, and its last state was `exitCode 137`. Its log ended at `Starting RPC server` and `Starting Http Proxy`, with no error. The startup probe calls `/apis/v1beta1/healthz` for up to 60 s and then kills the container.
- `ml-pipeline-ui` was in `CrashLoopBackOff`. `ml-pipeline-persistenceagent` and `ml-pipeline-scheduledworkflow` waited on the API server.

The node used about 2.5 GiB of its 7.6 GiB while this happened, so memory was not the obvious cause. We did not find the cause. Possible: a slow start under a cold image pull and a tight probe. That is a guess. We stopped here and did not send a pipeline.

What we can show: the compiled `wine_pipeline.yaml` from [the last lesson](lesson:kubeflow/your-first-pipeline), and the script `code/kubeflow/cluster_run.py` that would submit it. **It was not run.** It follows the docs:

```bash
kubectl port-forward -n kubeflow svc/ml-pipeline-ui 3000:80
```

```python
client = kfp.Client(host="http://localhost:3000")
run = client.create_run_from_pipeline_package("wine_pipeline.yaml", arguments={"trees": 20}, experiment_name="wine")
```

## What the cluster adds (from the docs, not run)

| Feature | How |
| --- | --- |
| Resources | `task.set_cpu_limit("2")`, `set_memory_limit("4G")`, `set_accelerator_type(...)` |
| Retries | `task.set_retry(num_retries=3)` |
| Caching | On by default. A step with the same inputs and image is skipped. `set_caching_options(False)` turns it off |
| Branches | `dsl.If`, `dsl.Elif`, `dsl.Else` (`dsl.Condition` is deprecated) |
| Loops | `dsl.ParallelFor` with `dsl.Collected` to gather results |
| Cleanup | `dsl.ExitHandler` runs a step even when others fail |
| Secrets, volumes | the `kfp-kubernetes` package (same version, 2.18.0) |
| Schedules | recurring runs |

Under the hood: an API server, MySQL for metadata, an object store for artifacts (SeaweedFS), and **Argo Workflows** to run the steps as pods. Argo 3.x is deprecated for KFP 2.x. Our install used Argo `v4.1.6`.

:::check The install page says `?ref=2.18.0`. Does that guarantee you run KFP 2.18.0 code?
No. It fixes the manifests. In `env/dev` we saw the KFP images tagged `:master`.
:::
