---
title: The parts
summary: The frontend, router, workers, planner, KV block manager, NIXL, and how they find each other. Then one request, step by step.
time: 20 min
---

"Dynamo" is a bundle of parts, and the docs use their names all the time. If you cannot tell the router from the planner, the rest of this track blurs. So first the cast, then one request walking through it.

All facts here come from Dynamo's [architecture page](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/developer-guide/knowledge-base/concepts/system-architecture/architecture.md) and [overall architecture page](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/developer-guide/knowledge-base/overview.md), read on 2026-11-12. We did not run it.

## The cast

**Frontend.** The front door. It exposes an OpenAI-compatible HTTP server on port 8000 by default. The [frontend page](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/developer-guide/knowledge-base/modular-components/frontend/overview.md) lists `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`, `/v1/responses` and `/v1/models`, and a KServe gRPC option. It applies the chat template and **tokenizes** the prompt (cuts text into the integer ids the model reads). It needs the model's config and tokenizer files, not the weights.

**Router.** Picks which worker gets the request. It can use plain modes such as round-robin or random, or a KV-aware mode that scores workers by cache contents and load. [Lesson 4](lesson:dynamo/kv-aware-routing) is about it.

**Workers.** The processes that run an engine on GPUs. A worker is vLLM, SGLang or TensorRT-LLM with a Dynamo wrapper. In a split setup some workers only do prefill and the rest only do decode.

**Planner.** The autoscaler. It watches latency and load, then changes how many workers of each kind should run ([lesson 6](lesson:dynamo/planner-and-autoscaling)).

**KV block manager (KVBM).** Handles KV cache blocks across memory tiers, from GPU to CPU memory to disk to remote storage. Its status needs care, so [lesson 5](lesson:dynamo/kv-cache-offloading) has the details.

**NIXL.** A transfer library. Its README says it speeds up point-to-point data movement for inference stacks like Dynamo, across memory (CPU, GPU) and storage ([NIXL README](https://github.com/ai-dynamo/nixl/blob/main/README.md)). In a split setup it moves the KV cache from a prefill GPU to a decode GPU.

## How the parts find each other

Workers start and stop all the time, so something must tell the frontend and router who is alive. Dynamo's architecture page splits the plumbing into three **planes** (separate channels for separate kinds of traffic):

| Plane | Carries | Default transport | Other options |
|---|---|---|---|
| Discovery | who exists and is alive | Kubernetes resources on Kubernetes, etcd on bare metal | memory or file backends for development |
| Request | the requests between parts | TCP | NATS |
| Event | cache updates and metrics | ZMQ | NATS |

The docs disagree with themselves here, so check the version you install. The README says neither etcd nor NATS is required: locally you pass `--discovery-backend file`, and on Kubernetes discovery is native. The architecture page says etcd is the local default. The frontend page still lists "`etcd` and `nats-server -js` running" as a prerequisite. The install guide says they are recommended for multi-node practice but not strictly required on one machine ([install guide](https://github.com/ai-dynamo/dynamo/blob/4a046dfdd89a7d60123669e7b7194e2f1a6424c1/docs/fern/pages/cli/installation/install-dynamo.mdx)). We could not tell which page is newest.

## One request, six steps

<figure>
<svg viewBox="0 0 660 420" role="img" aria-labelledby="t-dyn-arch d-dyn-arch">
  <title id="t-dyn-arch">One request through Dynamo in six steps</title>
  <desc id="d-dyn-arch">A client sends a request. Step 1: the client calls the frontend. Step 2: the frontend tokenizes it and passes it to the router. Step 3: the router picks a prefill worker. Step 4: the router hands the request to a decode worker, which pulls the KV cache from the prefill worker over NIXL. Step 5: the decode worker generates tokens. Step 6: tokens stream back through the frontend to the client. Below, dashed arrows show a planner that sets worker counts, discovery that tracks which workers are alive, and KV events that the workers publish.</desc>
  <defs><marker id="ah-dyn-arch" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect class="box" x="10" y="44" width="100" height="48" rx="8"/>
  <text x="60.0" y="72.5" font-size="13" text-anchor="middle" font-weight="700">Client</text>
  <rect class="box" x="160" y="44" width="140" height="48" rx="8"/>
  <text x="230.0" y="64.0" font-size="13" text-anchor="middle" font-weight="700">Frontend</text>
  <text x="230.0" y="81.0" font-size="12" text-anchor="middle" class="small">HTTP, tokenizes</text>
  <rect class="box" x="350" y="44" width="140" height="48" rx="8"/>
  <text x="420.0" y="64.0" font-size="13" text-anchor="middle" font-weight="700">Router</text>
  <text x="420.0" y="81.0" font-size="12" text-anchor="middle" class="small">scores workers</text>
  <path class="arrow" d="M110 68 H156" marker-end="url(#ah-dyn-arch)"/>
  <circle class="box hot" cx="133" cy="56" r="11"/>
  <text x="133" y="60.5" font-size="13" text-anchor="middle" font-weight="700">1</text>
  <path class="arrow" d="M300 68 H346" marker-end="url(#ah-dyn-arch)"/>
  <circle class="box hot" cx="323" cy="56" r="11"/>
  <text x="323" y="60.5" font-size="13" text-anchor="middle" font-weight="700">2</text>
  <path class="arrow" d="M385 92 V124 H140 V176" marker-end="url(#ah-dyn-arch)"/>
  <circle class="box hot" cx="262" cy="124" r="11"/>
  <text x="262" y="128.5" font-size="13" text-anchor="middle" font-weight="700">3</text>
  <path class="arrow" d="M455 92 V176" marker-end="url(#ah-dyn-arch)"/>
  <circle class="box hot" cx="455" cy="124" r="11"/>
  <text x="455" y="128.5" font-size="13" text-anchor="middle" font-weight="700">4</text>
  <rect class="box hot" x="20" y="178" width="240" height="100" rx="8"/>
  <text x="140" y="200" font-size="13" text-anchor="middle" font-weight="700">Prefill workers</text>
  <text x="140" y="217" font-size="12" text-anchor="middle" class="small">read the prompt</text>
  <rect class="box" x="36" y="228" width="98" height="38" rx="8"/>
  <text x="85.0" y="251.5" font-size="13" text-anchor="middle">worker</text>
  <rect class="box" x="146" y="228" width="98" height="38" rx="8"/>
  <text x="195.0" y="251.5" font-size="13" text-anchor="middle">worker</text>
  <rect class="box hot" x="390" y="178" width="240" height="100" rx="8"/>
  <text x="510" y="200" font-size="13" text-anchor="middle" font-weight="700">Decode workers</text>
  <text x="510" y="217" font-size="12" text-anchor="middle" class="small">write the answer</text>
  <rect class="box" x="406" y="228" width="98" height="38" rx="8"/>
  <text x="455.0" y="251.5" font-size="13" text-anchor="middle">worker</text>
  <rect class="box" x="516" y="228" width="98" height="38" rx="8"/>
  <text x="565.0" y="251.5" font-size="13" text-anchor="middle">worker</text>
  <path class="arrow" d="M262 252 H386" marker-end="url(#ah-dyn-arch)"/>
  <text x="324" y="238" font-size="12" text-anchor="middle" class="small">KV cache</text>
  <text x="324" y="276" font-size="12" text-anchor="middle" class="small">over NIXL</text>
  <circle class="box hot" cx="610" cy="200" r="11"/>
  <text x="610" y="204.5" font-size="13" text-anchor="middle" font-weight="700">5</text>
  <path class="arrow" d="M630 178 V16 H230 V40" marker-end="url(#ah-dyn-arch)"/>
  <circle class="box hot" cx="430" cy="16" r="11"/>
  <text x="430" y="20.5" font-size="13" text-anchor="middle" font-weight="700">6</text>
  <text x="452" y="36" font-size="12" text-anchor="start" class="small">tokens stream back</text>
  <rect class="box" x="20" y="336" width="170" height="56" rx="8" stroke-dasharray="5 4"/>
  <text x="105.0" y="360.0" font-size="13" text-anchor="middle" font-weight="700">Discovery</text>
  <text x="105.0" y="377.0" font-size="12" text-anchor="middle" class="small">who is alive</text>
  <rect class="box" x="245" y="336" width="170" height="56" rx="8" stroke-dasharray="5 4"/>
  <text x="330.0" y="360.0" font-size="13" text-anchor="middle" font-weight="700">Planner</text>
  <text x="330.0" y="377.0" font-size="12" text-anchor="middle" class="small">sets worker counts</text>
  <rect class="box" x="460" y="336" width="170" height="56" rx="8" stroke-dasharray="5 4"/>
  <text x="545.0" y="360.0" font-size="13" text-anchor="middle" font-weight="700">KV events</text>
  <text x="545.0" y="377.0" font-size="12" text-anchor="middle" class="small">what each cache holds</text>
  <path class="arrow" stroke-dasharray="5 4" d="M105 336 V282" marker-end="url(#ah-dyn-arch)"/>
  <path class="arrow" stroke-dasharray="5 4" d="M290 336 L200 282" marker-end="url(#ah-dyn-arch)"/>
  <path class="arrow" stroke-dasharray="5 4" d="M370 336 L450 282" marker-end="url(#ah-dyn-arch)"/>
  <path class="arrow" stroke-dasharray="5 4" d="M545 282 V332" marker-end="url(#ah-dyn-arch)"/>
  <text x="555" y="312" font-size="12" text-anchor="start" class="small">router reads</text>
  <text x="112" y="312" font-size="12" text-anchor="start" class="small">register</text>
</svg>
<figcaption>The numbered path is one request. Dashed arrows are the background work that keeps the fleet running. The docs number nine steps. We merged them into six.</figcaption>
</figure>

The docs number nine steps (S1 to S9). We merged them into six:

1. **Request.** The client sends an API call to the frontend (docs S1).
2. **Prepare.** The frontend applies the chat template, tokenizes and validates, then hands the request to the router (S2).
3. **Pick a prefill worker.** A component called the PrefillRouter chooses one by cache overlap plus load, or by simple load balancing (S3). The prefill worker computes the KV cache for the prompt and returns transfer details (S4, S5).
4. **Hand off.** The router adds those details to the request and sends it to a decode worker (S6). That worker pulls the KV cache straight from the prefill GPU through NIXL (S7).
5. **Decode.** The decode worker writes the answer, one token at a time (S8).
6. **Stream back.** Tokens return through the frontend to the client (S9).

If you run no split, steps 3 to 5 collapse into one worker doing both phases. The router still picks the worker.

Around that path, the dashed parts keep it healthy. Workers register with discovery. They publish **KV events** (notes that say "I stored this block" or "I dropped it") so the router knows what each cache holds. The planner reads metrics from the frontend and workers and sets worker counts. On Kubernetes an operator applies those counts.

:::check Which part decides how many prefill and decode workers exist, and which part decides which worker gets one request?
The planner decides how many workers exist. The router decides which worker gets a given request.
:::

:::check Why does the router pass only a small note to the decode worker, not the KV cache itself?
The KV cache is large. It moves directly from GPU to GPU through NIXL, so the router only forwards the transfer details.
:::
