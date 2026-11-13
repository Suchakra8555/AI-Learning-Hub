---
title: What Dynamo is
summary: One engine runs well on one box. A fleet needs routing, splitting, scaling and more cache memory. NVIDIA Dynamo is the layer that does those jobs above the engines.
time: 15 min
---

Say you serve a model with vLLM and it works. Then traffic grows, and you run ten copies on ten servers. New questions show up that no single engine can answer. Which copy should get this request? Why is one user's huge prompt freezing everyone else's replies? How many copies do you need at 3 a.m.? Where does the cache go when the GPU is full?

The [last lesson of the engines track](lesson:inference/choosing-an-engine) ended on that gap. This track covers one answer to it: **NVIDIA Dynamo**.

We did not run Dynamo. We read its GitHub repository and docs on 2026-11-12 (commit `4a046df`, where the version in `Cargo.toml` is 1.7.0). The newest release notes in the docs are for v1.6.0, dated Oct 22, 2026. The README's container examples use 1.6.0. Every claim below links to the file we read, and project numbers are labelled as the project's claims.

## Four jobs above the engine

Each engine looks after the GPUs it was given. A fleet adds four jobs on top.

| Job | The question | Where this track covers it |
|---|---|---|
| Routing | Which worker should get this request? | [KV-aware routing](lesson:dynamo/kv-aware-routing) |
| Splitting | Should prefill and decode run on different GPUs? | [Disaggregated serving](lesson:dynamo/disaggregated-serving) |
| Scaling | How many workers of each kind, right now? | [Planner and autoscaling](lesson:dynamo/planner-and-autoscaling) |
| Memory | Can cache live beyond one GPU's memory? | [KV cache offloading](lesson:dynamo/kv-cache-offloading) |

Think of an air-traffic controller. Each pilot flies their own plane well. Nobody in a cockpit decides which runway each plane uses or how many planes are in the air. That is the controller's job. Dynamo plays the controller, and the engines are the pilots.

## What Dynamo is

The README calls it "the open-source, datacenter-scale inference stack" and says it is the orchestration layer above inference engines. It does not replace vLLM, SGLang or TensorRT-LLM. It runs them as workers and coordinates them ([README](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/README.md)). It is written in Rust for the fast parts and Python for the parts people extend.

<figure>
<svg viewBox="0 0 640 372" role="img" aria-labelledby="t-dyn-stack d-dyn-stack">
  <title id="t-dyn-stack">Dynamo sits between clients and engines</title>
  <desc id="d-dyn-stack">A stack of four layers. Clients at the top send requests. Below them is Dynamo, shown as one large box holding a frontend, a router, a planner, a KV block manager and NIXL. Below Dynamo are three engines: vLLM, SGLang and TensorRT-LLM. At the bottom are GPUs, grouped under each engine.</desc>
  <defs><marker id="ah-dyn-stack" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect class="box" x="10" y="10" width="430" height="52" rx="8"/>
  <text x="225.0" y="32.0" font-size="13" text-anchor="middle" font-weight="700">Clients</text>
  <text x="225.0" y="49.0" font-size="12" text-anchor="middle" class="small">apps, agents, curl: OpenAI-style requests</text>
  <path class="arrow" d="M225 62 V84" marker-end="url(#ah-dyn-stack)"/>
  <rect class="box hot" x="10" y="86" width="430" height="118" rx="8"/>
  <text x="225" y="108" font-size="14" text-anchor="middle" font-weight="700">Dynamo</text>
  <rect class="box" x="20" y="124" width="72" height="34" rx="8"/>
  <text x="56.0" y="145.5" font-size="13" text-anchor="middle">Frontend</text>
  <rect class="box" x="98" y="124" width="72" height="34" rx="8"/>
  <text x="134.0" y="145.5" font-size="13" text-anchor="middle">Router</text>
  <rect class="box" x="176" y="124" width="72" height="34" rx="8"/>
  <text x="212.0" y="145.5" font-size="13" text-anchor="middle">Planner</text>
  <rect class="box" x="254" y="124" width="72" height="34" rx="8"/>
  <text x="290.0" y="145.5" font-size="13" text-anchor="middle">KVBM</text>
  <rect class="box" x="332" y="124" width="72" height="34" rx="8"/>
  <text x="368.0" y="145.5" font-size="13" text-anchor="middle">NIXL</text>
  <text x="225" y="184" font-size="12" text-anchor="middle" class="small">decides where requests go, how many engines run, where KV lives</text>
  <path class="arrow" d="M225 204 V226" marker-end="url(#ah-dyn-stack)"/>
  <rect class="box" x="10" y="228" width="138" height="52" rx="8"/>
  <text x="79.0" y="250.0" font-size="13" text-anchor="middle" font-weight="700">vLLM</text>
  <text x="79.0" y="267.0" font-size="12" text-anchor="middle" class="small">an engine</text>
  <rect class="box" x="156" y="228" width="138" height="52" rx="8"/>
  <text x="225.0" y="250.0" font-size="13" text-anchor="middle" font-weight="700">SGLang</text>
  <text x="225.0" y="267.0" font-size="12" text-anchor="middle" class="small">an engine</text>
  <rect class="box" x="302" y="228" width="138" height="52" rx="8"/>
  <text x="371.0" y="250.0" font-size="13" text-anchor="middle" font-weight="700">TensorRT-LLM</text>
  <text x="371.0" y="267.0" font-size="12" text-anchor="middle" class="small">an engine</text>
  <path class="arrow" d="M79 280 V302" marker-end="url(#ah-dyn-stack)"/>
  <path class="arrow" d="M225 280 V302" marker-end="url(#ah-dyn-stack)"/>
  <path class="arrow" d="M371 280 V302" marker-end="url(#ah-dyn-stack)"/>
  <rect class="box" x="10" y="304" width="138" height="46" rx="8"/>
  <text x="79.0" y="331.5" font-size="13" text-anchor="middle">GPU group</text>
  <rect class="box" x="156" y="304" width="138" height="46" rx="8"/>
  <text x="225.0" y="331.5" font-size="13" text-anchor="middle">GPU group</text>
  <rect class="box" x="302" y="304" width="138" height="46" rx="8"/>
  <text x="371.0" y="331.5" font-size="13" text-anchor="middle">GPU group</text>
  <text x="458" y="34" font-size="12" text-anchor="start" class="small">Takes requests in.</text>
  <text x="458" y="124" font-size="12" text-anchor="start" class="small">Routes, splits, scales.</text>
  <text x="458" y="142" font-size="12" text-anchor="start" class="small">Runs above the engines.</text>
  <text x="458" y="250" font-size="12" text-anchor="start" class="small">Batch and run the</text>
  <text x="458" y="267" font-size="12" text-anchor="start" class="small">model on their GPUs.</text>
  <text x="458" y="331" font-size="12" text-anchor="start" class="small">Still do the math.</text>
</svg>
<figcaption>The four layers. Dynamo does not run the model. The engines still do that on their GPUs.</figcaption>
</figure>

The README's feature table shows what each engine supports. Disaggregated serving, KV-aware routing and the planner are ticked for all three. The KV block manager is ticked for TensorRT-LLM and vLLM and marked in progress for SGLang. We cover the memory piece, and a deprecation notice about it, in [lesson 5](lesson:dynamo/kv-cache-offloading).

## When you do not need it

The README is direct about this. It lists five reasons to use Dynamo: you serve across multiple GPUs or nodes, you want KV-aware routing, you want to scale prefill and decode independently, you want autoscaling that meets latency targets, and you want fast cold starts. Then it says: "If you're running a single model on a single GPU, your inference engine alone is probably sufficient."

We agree. Every part you add is something to run, watch and upgrade.

## What the project claims

The README has a "Key Results" table. Two rows, as the project states them:

- 2x faster time to first token from KV-aware routing, for Qwen3-Coder 480B, in a benchmark run by Baseten, a company that uses Dynamo.
- 7x higher throughput per GPU for DeepSeek R1 on GB200 NVL72 with Dynamo, compared with B200 without it.

These are the project's claims, on setups we cannot reproduce. The second compares different GPUs as well as different software. Read them as a reason to try, then [benchmark on your own traffic](lesson:inference/benchmark-honestly).

## How the track goes

1. This lesson: the problem.
2. [The parts](lesson:dynamo/the-parts): what runs where, and the path of one request.
3. [Disaggregated serving](lesson:dynamo/disaggregated-serving), with a toy model you can run.
4. [KV-aware routing](lesson:dynamo/kv-aware-routing), with a second script.
5. [KV cache offloading](lesson:dynamo/kv-cache-offloading).
6. [The planner](lesson:dynamo/planner-and-autoscaling).
7. [Deploying it](lesson:dynamo/deploying-dynamo), plus a reading lab.

:::check Name two jobs Dynamo does that vLLM on its own does not.
Any two of: choosing which worker gets a request by cache contents, running prefill and decode on separate GPU pools, scaling the number of workers to meet latency targets, and moving KV cache between GPUs or to other memory tiers.
:::

:::check Does Dynamo replace vLLM?
No. Per the README it sits above engines such as vLLM, SGLang and TensorRT-LLM and uses them as workers.
:::
