---
title: Where to deploy an agent, and what you now own
summary: LangSmith's four ways to host an agent, from fully managed to fully yours, and the checklist that applies to all of them.
time: 15 min
---

LangSmith's **Agent Server** is the runtime that serves a deployed agent. It has three ideas: **assistants** (configuration), **threads** (state), and **runs** (work). It also supports cron jobs, streaming, human pauses, auth, and MCP and A2A endpoints ([overview](https://docs.langchain.com/langsmith/agent-server-overview.md)).

## Four ways to host it

| Option | Who runs what | From the docs |
|---|---|---|
| **Cloud** | LangChain runs everything | Plus plan or above. Serverless (scales to zero) or Dedicated (always on). |
| **Hybrid** | LangChain hosts the control plane. Servers and databases run in your network. | Plan not stated on the overview |
| **Full self-hosted** | You run all of it, with LangChain's images and Helm charts | "Require an Enterprise plan" |
| **Standalone server** | You run the API and workers with your own Postgres and Redis. No managed UI. | Plan not stated |

Sources: [cloud](https://docs.langchain.com/langsmith/deploy-to-cloud-overview.md), [self-hosted](https://docs.langchain.com/langsmith/deploy-to-self-hosted-overview.md), [standalone](https://docs.langchain.com/langsmith/deploy-standalone-server.md).

For Cloud, the docs say: check it runs locally with `langgraph dev`, then push a connected GitHub repo or run `langgraph deploy`. We did not find the CLI install command or the `langgraph.json` format on the pages we read.

## Standalone: what you take on

The standalone page warns: "Do not run standalone servers in serverless environments." LangChain tests regularly only on Kubernetes with its Helm chart. Elsewhere you must build queue autoscaling, graceful draining, and upgrades yourself. It needs outbound access to `beacon.langchain.com` for license checks unless air-gapped. Check health at `/ok`, which should return `{"ok": true}`.

## A checklist for any host

- [ ] Postgres holds threads, runs, and memory. **Back it up.**
- [ ] Secrets in a secret store, not in the repo.
- [ ] Health check wired to your alerting.
- [ ] A rollback plan. See [safe releases](lesson:llmops/tracking-and-versions).
- [ ] Tracing on, with sensitive fields masked.
- [ ] A test set run before every release ([evals](lesson:evals/why-test-an-agent)).
- [ ] Spend limits on your model provider account.

More in the [RAG launch checklist](lesson:rag/launch-checklist).

:::note What we did not run
We read these pages. We did not deploy anything. Plans change, so confirm terms with LangChain.
:::

:::check Why is "standalone" more work than Cloud?
You run the servers, database, queue scaling, and upgrades yourself. Cloud handles those.
:::
