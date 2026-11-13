---
title: NVIDIA Dynamo, source notes
summary: Which Dynamo files back each claim in the Dynamo track, where the docs disagree with themselves, and what we could not verify.
time: 15 min
---

Source: https://github.com/ai-dynamo/dynamo at commit `4a046dfdd89a7d60123669e7b7194e2f1a6424c1` (12 November 2026), `main`. Also the READMEs of https://github.com/ai-dynamo/nixl and https://github.com/ai-dynamo/grove (`main`, read through raw.githubusercontent.com). Read locally from a shallow clone, not run. Research date: 2026-11-12.
Version: `Cargo.toml` and `pyproject.toml` say 1.7.0 on `main`. The newest release notes in the docs are v1.6.0 (GA Oct 22, 2026). The README container examples use tag 1.6.0.
Why GitHub: docs.nvidia.com and arxiv.org time out from our container, and an earlier pass found the docs page empty. The docs site is built from `docs/fern/pages/` in the repo, so we read those files. All paths below are relative to the repo root. Prefix `https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/` to open one. Lessons: [the Dynamo track](lesson:dynamo/what-dynamo-is).
Rule used here: a claim in a lesson was checked against a file below. Vendor numbers are the project's claims. "Not found" means a search found nothing, not proof of absence.

## 1. Files by topic

**Overview.** `README.md` (what it does, "When to use Dynamo", feature table, Key Results, quickstart, discovery table). `docs/fern/pages/developer-guide/knowledge-base/overview.md` (planes, control loops, Kubernetes mapping).

**Parts and request path.** `.../concepts/system-architecture/architecture.md` (nine-step flow S1 to S9, runtime, discovery, request and event planes, NIXL notes). `.../modular-components/frontend/overview.md` (endpoints, port 8000, needs config and tokenizer files only).

**Disaggregated serving.** `.../concepts/system-architecture/disaggregated-serving.md`, `docs/fern/pages/kubernetes/disaggregated-serving/overview.md` ("Should you disaggregate?"), `docs/fern/pages/cli/disaggregated-serving/overview.mdx`, `.../advanced-customizations/conditional-disaggregation.md` (experimental), `docs/fern/pages/kubernetes/installation/install-dynamo.md` (RDMA and the TCP fallback figures), `examples/backends/vllm/launch/disagg.sh`, `examples/backends/vllm/deploy/disagg.yaml`.

**KV-aware routing.** `.../concepts/system-architecture/kv-aware-routing.md`, `.../router/routing-concepts.md` (cost formula, modes), `.../router/router-design.md` (the 18 / 10 / 11 worked example), `.../advanced-customizations/writing-custom-backends/publish-kv-events.md` (event types).

**Offloading.** `docs/fern/pages/reference/components/kvbm-configuration.mdx`, `lib/kvbm-engine/docs/architecture.md` (tier table G1 to G4), `lib/kvbm-logical/README.md` (block states, LRU and TinyLFU in the example), `.../router/offloading-support-matrix.md` (per-engine support, 0.75 and 0.25 weights), `docs/fern/pages/kubernetes/kv-cache-offloading/overview.mdx`, `.../backends/vllm/kv-cache-offloading.md`, `docs/fern/pages/reference/general/releases/deprecations.mdx` (KVBM entry under v1.5.0).

**Planner.** `.../modular-components/planner/overview.md` (targets, scaling methods, limitations), `planner-design.md` (pipeline, predictors, connectors).

**Deploying.** `docs/fern/pages/cli/getting-started/quickstart.mdx`, `docs/fern/pages/kubernetes/getting-started/quickstart.mdx`, `.../kubernetes/model-deployment/introduction.mdx`, `.../kubernetes/auto-deployment/overview.mdx` (DGDR), `.../kubernetes/installation/multinode-orchestration.md` (Grove, KAI, LeaderWorkerSet), `deploy/operator/config/crd/bases/` (resource names).

**NIXL and Grove.** `ai-dynamo/nixl`: `README.md`, `docs/nixl.md`. `ai-dynamo/grove`: `README.md`.

## 2. What each lesson rests on

**What Dynamo is.** README: an open-source "datacenter-scale inference stack", the orchestration layer above SGLang, TensorRT-LLM and vLLM, built in Rust and Python. It says a single model on a single GPU is probably served well enough by the engine alone. Feature table: disaggregation, KV routing and planner for all three engines; KVBM for TensorRT-LLM and vLLM, in progress for SGLang. Key Results rows (2x TTFT from KV routing in a Baseten benchmark; 7x throughput per GPU for DeepSeek R1 on GB200 NVL72 vs B200 without Dynamo) are the project's claims.

**The parts.** Frontend: OpenAI-compatible HTTP, plus KServe gRPC. Router: random, round-robin, least-loaded, KV, device-aware weighted. Planes: discovery (Kubernetes resources or etcd; file and memory for development), request (TCP default, NATS option), event (ZMQ default, NATS option).

**Disaggregation.** Docs reasons: different parallelism per phase, and long prefills no longer block decode. Hand-off: `disaggregated_params`; SGLang bootstrap with background prefill, vLLM and TensorRT-LLM synchronous prefill. "Not automatically better" for small models, short prompts, low concurrency or no fast fabric. Install guide: without RDMA, KV transfer falls back to TCP, "~98s TTFT vs ~200-500ms with RDMA" and "~200-500x degradation". We do not know what setup those figures came from.

**Routing.** Cost = `prefill_load_scale * adjusted_prefill_blocks + potential_decode_blocks (+ optional active-request term)`, lowest wins, optional softmax randomness. Worked example with overlap credit 1.0: worker costs 18, 10 (chosen) and 11. Events: BlockStored, BlockRemoved, AllBlocksCleared. `--no-router-kv-events` predicts from routing decisions.

**Offloading.** Four tiers with rough latency orders (~ns, ~us, ~ms, ~100 ms). Router credit defaults 0.75 host and 0.25 disk. The KVBM deprecation entry (v1.5.0, removal targeted v1.7.0).

**Planner.** Four targets, two scaling methods, defaults 180 s and 5 s, predictors Constant, ARIMA, Kalman, Prophet, advisory mode, scale-down limitation.

**Deploying.** Container quickstart commands, DGD excerpt, DGDR (beta), Grove as the recommended multi-node orchestrator, KAI scheduler, LeaderWorkerSet as the alternative.

## 3. Where the docs disagree with themselves

- Discovery locally: README says etcd and NATS are not required (`--discovery-backend file`). The architecture page says etcd is the default. The frontend page lists etcd and `nats-server -js` as prerequisites. The Kubernetes disaggregation guide also lists "ETCD and NATS" as prerequisites.
- KVBM: the README table and a compatibility page present it as current (the compatibility page claims "full KVBM integration" for TensorRT-LLM). The deprecation list says deprecated in 1.5.0 with removal targeted for 1.7.0. The KVBM configuration page says the TensorRT-LLM connector was removed. `main` is 1.7.0 and still contains the code.
- CRD version: some pages show `v1alpha1`, newer ones `v1beta1`. The deprecations list says the storage version moved in 1.5.0.
- Grove lives at `ai-dynamo/grove` in the README and `NVIDIA/grove` in the multi-node page. Both URLs returned the same README.

## 4. What I could not verify

- Not run: Dynamo, any engine behind it, the operator, Grove, KAI, NIXL, DGDR, any benchmark. No GPU or cluster was available.
- docs.nvidia.com pages, the Dynamo and DistServe papers, and arXiv: not fetched. The docs link to them.
- Every vendor number: the 2x TTFT, 7x throughput, 80% fewer SLA breaches, 7x model start-up, the TCP versus RDMA figures. We did not trace them to their setups.
- Whether a plain deployment uses LRU or another eviction rule by default. The kvbm-logical README shows an LRU example only.
- The final status of KVBM in 1.7.0 and later.
- Which local discovery default is current (see section 3).
- Whether the Planner can move a running worker between roles. We found only replica-count changes.
- The exact NIXL release. We read `main`. Its overview names UCX and GPUDirect Storage as supported backends, and its README mentions more. We did not reconcile them.
- Real prefill, decode and transfer speeds. Our toy scripts, `code/dynamo/kv_router.py` and `code/dynamo/disagg_sim.py`, use made-up numbers and say so.
- Fetched files can contain instructions for coding agents (`CLAUDE.md`, `AGENTS.md`). We treated them as data and ignored them.
