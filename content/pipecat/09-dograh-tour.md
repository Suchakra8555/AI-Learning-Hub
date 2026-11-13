---
title: A tour of Dograh
summary: Dograh is an open-source voice agent platform: a visual builder, a FastAPI backend, a Pipecat pipeline and a carrier layer. This lesson maps the repo, the processes and the data stores.
time: 15 min
---

**Dograh** ([repo](https://github.com/dograh-hq/dograh), BSD 2-Clause) is a platform for building and running voice agents. Its README calls it a self-hostable alternative to Vapi and Retell. You draw a call flow in a browser, connect a phone carrier, and Dograh runs the calls.

:::warn What we read
Source at commit `5dfa84c` (12 November 2026, version 1.51.0 in `.release-please-manifest.json`). We read the code and Dograh's docs. We did not install or run Dograh, so everything about behavior comes from reading. The project ships about every one to three weeks, so paths and numbers will drift.
:::

## The repo in one table

| Folder | What is there | Language |
|---|---|---|
| `ui/` | The builder, dashboard, test-call screen. Next.js 15, React 19, `@xyflow/react` 12, zustand | TypeScript |
| `api/` | REST API, call engine, telephony, campaigns, background jobs | Python, FastAPI |
| `pipecat/` | Git submodule: Dograh's fork of Pipecat | Python |
| `docs/` | The public docs, written for Mintlify | MDX |
| `sdk/` | Generated Python and TypeScript clients | |
| `evals/` | An STT benchmark and a viewer for its event streams | Python, Next.js |
| `scripts/`, `deploy/` | Setup, run and deploy scripts, nginx and coturn config | Shell |
| `.agents/` | Skills for coding agents, including one for merging upstream Pipecat | Markdown |

The root `AGENTS.md` says it in four lines: "Backend: Python with FastAPI. Frontend: Next.js 15 with React 19. Database: PostgreSQL with SQLAlchemy (async). Cache/Queue: Redis with ARQ."

## What runs

<figure>
<svg viewBox="0 0 900 360" role="img" aria-labelledby="t9 d9">
  <title id="t9">Dograh's processes and stores</title>
  <desc>A browser and phone carriers connect to nginx. Nginx sends traffic to several single-worker API processes and the UI. The API processes build Pipecat pipelines. Background jobs run in ARQ workers. A campaign orchestrator and an ARI manager run as singletons. Postgres, Redis and MinIO are shared stores.</desc>
  <defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="10" y="30" width="120" height="50" rx="10"/><text x="70" y="60">Browser</text>
    <rect class="box" x="10" y="100" width="120" height="50" rx="10"/><text x="70" y="124">Phone carrier</text><text x="70" y="141" font-size="11" class="small">Twilio, Telnyx...</text>
    <rect class="box" x="180" y="60" width="110" height="60" rx="10"/><text x="235" y="96">nginx</text>
    <rect class="box" x="340" y="20" width="150" height="46" rx="10"/><text x="415" y="48">UI (Next.js)</text>
    <rect class="box hot" x="340" y="80" width="150" height="70" rx="10"/><text x="415" y="106">API process x N</text><text x="415" y="126" font-size="12" class="small">uvicorn, 1 worker each</text>
    <rect class="box" x="340" y="170" width="150" height="50" rx="10"/><text x="415" y="192">ARQ workers</text><text x="415" y="209" font-size="12" class="small">jobs, cron sweeps</text>
    <rect class="box" x="560" y="80" width="150" height="70" rx="10"/><text x="635" y="106">Pipecat pipeline</text><text x="635" y="126" font-size="12" class="small">one per live call</text>
    <rect class="box" x="560" y="170" width="150" height="50" rx="10"/><text x="635" y="192">Campaign orchestrator</text><text x="635" y="209" font-size="12" class="small">singleton</text>
    <rect class="box" x="740" y="170" width="150" height="50" rx="10"/><text x="815" y="192">ARI manager</text><text x="815" y="209" font-size="12" class="small">singleton, Asterisk</text>
    <rect class="box" x="180" y="280" width="200" height="56" rx="10"/><text x="280" y="304">Postgres + pgvector</text><text x="280" y="322" font-size="12" class="small">workflows, runs, KB chunks</text>
    <rect class="box" x="400" y="280" width="200" height="56" rx="10"/><text x="500" y="304">Redis</text><text x="500" y="322" font-size="12" class="small">queue, pub/sub, call slots</text>
    <rect class="box" x="620" y="280" width="200" height="56" rx="10"/><text x="720" y="304">MinIO / S3</text><text x="720" y="322" font-size="12" class="small">recordings, transcripts</text>
  </g>
  <path class="arrow" d="M130 55 L176 80" marker-end="url(#ah)"/>
  <path class="arrow" d="M130 125 L176 105" marker-end="url(#ah)"/>
  <path class="arrow" d="M290 80 L336 50" marker-end="url(#ah)"/>
  <path class="arrow" d="M290 100 L336 112" marker-end="url(#ah)"/>
  <path class="arrow" d="M490 115 H556" marker-end="url(#ah)"/>
  <path class="arrow" stroke-dasharray="4 4" d="M415 150 V166" marker-end="url(#ah)"/>
  <path class="arrow" stroke-dasharray="4 4" d="M280 275 L380 225"/>
  <path class="arrow" stroke-dasharray="4 4" d="M500 275 V225"/>
  <path class="arrow" stroke-dasharray="4 4" d="M650 275 L650 225"/>
</svg>
<figcaption>Topology, from <code>start_services_docker.sh</code>, <code>docker-compose.yaml</code> and <code>api/app.py</code>. Dashed lines are shared stores. Boxes are drawn schematically.</figcaption>
</figure>

Facts behind the picture:

- **Several API processes, not one with many workers.** The container starts `FASTAPI_WORKERS` separate `uvicorn` processes on consecutive ports, each with `--workers 1`. A comment in `scripts/start_services_docker.sh` says nginx `least_conn` across processes beats `--workers` for long-lived WebSockets. A call is a WebSocket that lasts minutes, so balancing by connection count matters more than by request count.
- **Migrations run on every container start** (`alembic upgrade head`, line 30).
- **Two singletons.** The campaign orchestrator and the Asterisk ARI manager must run once. Extra replicas must set `ENABLE_ARI_MANAGER` and `ENABLE_CAMPAIGN_ORCHESTRATOR` to false.
- **ARQ** is a Redis-backed Python job queue. It runs post-call work, webhooks, campaign batches, knowledge-base indexing and the AI builder. Cron sweeps re-queue lost jobs: workflow completions every 15 minutes, webhook deliveries every 5.
- **A scar in the code.** `api/tasks/arq.py` lines 35 to 44 record an incident: "every arq worker in the cluster died on 2026-08-26" when Redis was briefly unreachable. The fix is an exponential-backoff retry. Good code comments say why.
- **Postgres holds knowledge-base vectors too** (pgvector), so there is no separate vector store. Redis also holds call-concurrency slots, a TTS cache and campaign circuit-breaker state. Recordings and transcripts go to MinIO or S3 behind one storage interface.
- **The MCP server is mounted inside the API** at `/api/v1/mcp`, so coding agents can read and edit workflows with an API key.

## Where Pipecat sits

Only the **call** is Pipecat. Everything around it, from the builder to billing, is ordinary web engineering. The seam is one function, `_run_pipeline_impl` in `api/services/pipecat/run_pipeline.py` (1,363 lines). [The next lesson](lesson:pipecat/a-call-becomes-a-pipeline) opens it.

Counts from a grep of `api/` (250 Python files import `pipecat`):

| Pipecat module | Import lines |
|---|---|
| `frames.frames` | 120 |
| `processors.aggregators` | 117 |
| `processors.frame_processor` | 73 |
| `pipeline.worker`, `pipeline.pipeline` | 37 each |
| `utils.enums`, `utils.run_context` (both fork-only) | 35, 33 |
| `services.openai` | 29 |
| `tests.mock_transport` (fork-only) | 23 |

That a third of the imports touch frames and aggregators tells you the engine works at the frame level, not at the "start the bot" level.

:::check Dograh runs several uvicorn processes with one worker each, not one process with many workers. Why?
Calls are long WebSockets. nginx can balance by open connections across separate processes, which spreads calls evenly. A single process with several workers hides that balance from nginx.
:::

:::check Which two Dograh processes must run exactly once, and why?
The campaign orchestrator and the ARI manager. They hold schedule and Asterisk connection state that would double up if two copies ran.
:::
