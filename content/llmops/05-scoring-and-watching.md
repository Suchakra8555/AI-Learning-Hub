---
title: Scoring answers and watching the system
summary: RAGAS-style scores for answers, traces for single requests, and Prometheus and Grafana for the machines underneath.
time: 25 min
---

Two different questions need two kinds of tools. "Are the answers good?" and "Is the system healthy?"

## Are the answers good? Scores

RAGAS scores RAG answers from 0 to 1 using a model as the judge. Three metrics we read:

- **Faithfulness.** Split the answer into claims. Count how many the retrieved text supports. Its docs show a worked example that scores 0.5 ([source](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)). Low faithfulness is what we call hallucination.
- **Response relevancy.** A model writes questions the answer would fit. The score is how close they are to the real question ([source](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/)).
- **Context precision.** Are the useful chunks ranked near the top of what was retrieved? ([source](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/))

We did not find the RAGAS definition of context recall in what we read, so we do not define it here. Because the judge is a model, scores need an API key and can vary. Spot-check by hand.

## What happened on this request? Traces

A **trace** records one request step by step: the input, each model call, the chunks retrieved, the output, the cost, and any error. Langfuse and Opik both do this, are open source, and can be self-hosted ([Langfuse](https://langfuse.com/docs), [Opik](https://www.comet.com/docs/opik/)). Both also manage test sets and run evaluations. We did not run either here.

## Are the machines healthy? Metrics

From the Prometheus, cAdvisor and Grafana docs:

| Tool | Job |
|---|---|
| **Prometheus** | Pulls numbers from targets over HTTP, stores them with labels, and lets you query them ([overview](https://prometheus.io/docs/introduction/overview/)) |
| **Node Exporter** | Exposes the host machine's CPU, memory, and disk numbers on port 9100 ([guide](https://prometheus.io/docs/guides/node-exporter/)) |
| **cAdvisor** | Exposes resource use per container ([repo](https://github.com/google/cadvisor)) |
| **Grafana** | Draws dashboards from those data sources ([docs](https://grafana.com/docs/grafana/latest/fundamentals/)) |

The Node Exporter guide is for a Linux host. We did not confirm Windows support, so on Windows use WSL or a container.

## Which one for which problem

| Question | Tool |
|---|---|
| Did the answer make things up? | Faithfulness score, plus reading traces |
| Why was this one request slow? | A trace |
| Is the server out of memory? | Prometheus and Grafana |
| Did last week's change make things worse? | Your test set, run again |

:::check Prometheus shows the server is healthy, but users report bad answers. Which tools tell you why?
Traces and answer scores. Machine metrics show the servers are running, not whether the answers are right.
:::
