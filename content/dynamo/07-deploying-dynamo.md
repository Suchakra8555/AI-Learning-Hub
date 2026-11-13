---
title: Deploying Dynamo
summary: The local shape with a frontend and workers, the Kubernetes shape with an operator and one manifest, a reading lab, and a plain note on what we did not run.
time: 25 min
---

You have met the parts. Now where do they run? There are two shapes: a few commands on one machine, and a Kubernetes cluster where an operator does the work. We read the [README](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/README.md), the [local](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/cli/getting-started/quickstart.mdx) and [Kubernetes](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/kubernetes/getting-started/introduction.mdx) guides and the example manifests on 2026-11-12.

**We did not run any of this.** We had no GPU and no cluster. The commands below are copied from the docs and may have changed.

## Local: a frontend and a worker

The README's container quickstart for vLLM (version 1.6.0 at the time) starts two processes in one container and sends a request:

```bash
python3 -m dynamo.frontend --http-port 8000 --discovery-backend file &
python3 -m dynamo.vllm --model Qwen/Qwen3-0.6B --discovery-backend file &
```

Then you call `localhost:8000/v1/chat/completions` as with any OpenAI-style server. `--discovery-backend file` is how the README avoids needing etcd. For a split, the repo's `launch/disagg.sh` presets start a prefill worker and a decode worker pinned to two GPUs, with a NIXL connector set in each worker's `--kv-transfer-config`. Adding a second prefill worker later is picked up automatically, per the docs.

## Kubernetes: one manifest, an operator

On Kubernetes you install the Dynamo platform with Helm. It brings an **operator**, a program that watches custom resources and makes pods match them, plus the custom resource definitions (CRDs). Their main resource is a **DynamoGraphDeployment (DGD)**: one manifest that lists the frontend and each worker role. This trimmed excerpt is from the repo's [vLLM split example](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/examples/backends/vllm/deploy/disagg.yaml):

```yaml
apiVersion: nvidia.com/v1beta1
kind: DynamoGraphDeployment
spec:
  components:
  - name: Frontend
    type: frontend
    replicas: 1
  - name: decode
    type: decode        # args: --disaggregation-mode decode
    replicas: 1         # resources: nvidia.com/gpu: "1"
  - name: prefill
    type: prefill       # args: --disaggregation-mode prefill
    replicas: 1
```

<figure>
<svg viewBox="0 0 660 380" role="img" aria-labelledby="t-dyn-deploy d-dyn-deploy">
  <title id="t-dyn-deploy">A Dynamo deployment on Kubernetes, one pod group per role</title>
  <desc id="d-dyn-deploy">On the left you apply one manifest, a DynamoGraphDeployment. The Dynamo operator reads it and creates pods in the cluster on the right: a frontend pod, two prefill worker pods and two decode worker pods each holding a GPU, and a planner pod. A dashed outline around the prefill and decode pods shows Grove and a gang scheduler placing them as a group. A dashed arrow shows the planner changing replica counts through the operator.</desc>
  <defs><marker id="ah-dyn-deploy" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect class="box" x="10" y="150" width="150" height="70" rx="8"/>
  <text x="85.0" y="172.5" font-size="12" text-anchor="middle" class="small">You apply</text>
  <text x="85.0" y="189.5" font-size="13" text-anchor="middle" font-weight="700">one DGD</text>
  <text x="85.0" y="206.5" font-size="12" text-anchor="middle" class="small">manifest</text>
  <path class="arrow" d="M160 185 H196" marker-end="url(#ah-dyn-deploy)"/>
  <rect class="box hot" x="200" y="150" width="130" height="70" rx="8"/>
  <text x="265.0" y="172.5" font-size="13" text-anchor="middle" font-weight="700">Dynamo</text>
  <text x="265.0" y="189.5" font-size="13" text-anchor="middle" font-weight="700">operator</text>
  <text x="265.0" y="206.5" font-size="12" text-anchor="middle" class="small">reconciles</text>
  <path class="arrow" d="M330 185 H366" marker-end="url(#ah-dyn-deploy)"/>
  <rect class="box" x="370" y="10" width="280" height="360" rx="10" stroke-dasharray="5 4"/>
  <text x="380" y="30" font-size="12" text-anchor="start" class="small">Kubernetes cluster</text>
  <rect class="box" x="386" y="44" width="120" height="50" rx="8"/>
  <text x="446.0" y="65.0" font-size="13" text-anchor="middle" font-weight="700">Frontend</text>
  <text x="446.0" y="82.0" font-size="12" text-anchor="middle" class="small">+ router</text>
  <rect class="box" x="526" y="44" width="112" height="50" rx="8"/>
  <text x="582.0" y="65.0" font-size="13" text-anchor="middle" font-weight="700">Planner</text>
  <text x="582.0" y="82.0" font-size="12" text-anchor="middle" class="small">sets replicas</text>
  <rect class="box" x="386" y="118" width="252" height="236" rx="8" stroke-dasharray="5 4"/>
  <text x="512" y="136" font-size="12" text-anchor="middle" class="small">placed together (gang scheduling)</text>
  <rect class="box" x="398" y="148" width="106" height="50" rx="8"/>
  <text x="451.0" y="169.0" font-size="13" text-anchor="middle" font-weight="700">Prefill</text>
  <text x="451.0" y="186.0" font-size="12" text-anchor="middle" class="small">1 GPU</text>
  <rect class="box" x="520" y="148" width="106" height="50" rx="8"/>
  <text x="573.0" y="169.0" font-size="13" text-anchor="middle" font-weight="700">Prefill</text>
  <text x="573.0" y="186.0" font-size="12" text-anchor="middle" class="small">1 GPU</text>
  <rect class="box" x="398" y="216" width="106" height="50" rx="8"/>
  <text x="451.0" y="237.0" font-size="13" text-anchor="middle" font-weight="700">Decode</text>
  <text x="451.0" y="254.0" font-size="12" text-anchor="middle" class="small">1 GPU</text>
  <rect class="box" x="520" y="216" width="106" height="50" rx="8"/>
  <text x="573.0" y="237.0" font-size="13" text-anchor="middle" font-weight="700">Decode</text>
  <text x="573.0" y="254.0" font-size="12" text-anchor="middle" class="small">1 GPU</text>
  <text x="512" y="296" font-size="12" text-anchor="middle" class="small">KV cache moves between them over NIXL</text>
  <text x="512" y="316" font-size="12" text-anchor="middle" class="small">(RDMA network for production)</text>
  <text x="512" y="340" font-size="12" text-anchor="middle" class="small">Grove and a gang scheduler (KAI)</text>
  <path class="arrow" stroke-dasharray="5 4" d="M582 94 V102 H350 V114 H266 V146" marker-end="url(#ah-dyn-deploy)"/>
  <text x="10" y="270" font-size="12" text-anchor="start" class="small">The planner changes</text>
  <text x="10" y="287" font-size="12" text-anchor="start" class="small">replica counts through</text>
  <text x="10" y="304" font-size="12" text-anchor="start" class="small">the operator (dashed).</text>
</svg>
<figcaption>One manifest, several roles. The dashed group is placed together by the scheduler, so a half-started group does not sit idle.</figcaption>
</figure>

Other resources in the docs: a **DynamoGraphDeploymentRequest (DGDR)**, marked beta, where you give a model and latency targets and Dynamo profiles options and writes the DGD for you; and recipes for common models. The README's DGDR example sets `ttft: 200.0` and `itl: 20.0`, in milliseconds. The docs note the storage version moved from `v1alpha1` to `v1beta1` in v1.5.0, so older pages may show the old one.

**Multi-node and gang scheduling.** A model that spans several nodes, or a split with prefill and decode pods, only works if all its pods start together. Starting some and not others wastes GPUs and can deadlock. **Gang scheduling** means placing a group all at once or not at all. The docs call **Grove** the default and recommended orchestrator for multi-node deployments, with the KAI scheduler for gang scheduling, and LeaderWorkerSet as the alternative. Grove's own README describes a Kubernetes API for hierarchical gang scheduling, topology-aware placement, multi-level autoscaling and startup ordering ([Grove](https://github.com/ai-dynamo/grove)). We did not install either.

**Network.** The install guide says production splitting needs an RDMA-capable network. Without it, transfers fall back to TCP with severe slowdowns, as [lesson 3](lesson:dynamo/disaggregated-serving) quoted. Shared model storage is also advised so each pod does not download the weights.

**Routing in front.** The docs offer Dynamo's own frontend as the entry point, or a Kubernetes Gateway API gateway that calls a Dynamo endpoint picker. We covered only the first.

## A reading lab

No GPU needed. Open the repo at commit `4a046df`.

1. In `docs/fern/pages/developer-guide/knowledge-base/modular-components/router/routing-concepts.md`, find the cost formula. Redo the worked example from [lesson 4](lesson:dynamo/kv-aware-routing) by hand with `overlap_score_credit` set to 0.5. Does worker 2 still win?
2. In `examples/backends/vllm/deploy/disagg.yaml`, find what marks the prefill worker as a producer and the decode worker as a consumer of KV.
3. In `docs/fern/pages/reference/general/releases/deprecations.mdx`, find the KVBM entry. What does it tell you to use instead?
4. In the planner overview, find what `advisory: true` does. When would you start there?
5. Run `code/dynamo/kv_router.py` and `code/dynamo/disagg_sim.py`. Change `CACHE_BLOCKS` and `PREFILL_BUSY`. Which conclusions survive?

## What we ran and did not run

Ran: our two toy scripts, `kv_router.py` and `disagg_sim.py`, with real output pasted in the lessons. Not run: Dynamo, any engine behind it, the operator, Grove, NIXL, or any benchmark. Every Dynamo claim comes from the docs at the commit above, and the docs sometimes disagree with themselves (discovery, KVBM). Vendor numbers are the vendor's. The [source notes](lesson:research/dynamo) list what we could not verify.

:::check Why does a split deployment need gang scheduling?
Prefill and decode pods only work as a pair. If only one kind starts, the GPUs sit idle, so the scheduler places the group together or not at all.
:::

:::check What does the operator do that you would otherwise do by hand?
It reads the DGD manifest and creates and updates the frontend and worker pods to match it, including changes the planner makes to replica counts.
:::
