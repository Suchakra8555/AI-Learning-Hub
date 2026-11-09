---
title: Tracing, dashboards, and alerts
summary: Turn on tracing, read a trace, then add the charts and alerts that tell you something broke before users do.
time: 20 min
---

Once an agent is live, you need to see inside it. Three tools, in the order you will use them.

## 1. Tracing

A **trace** is a record of one request: each model call, each tool call, the inputs and outputs, time and cost. In LangSmith you turn it on with environment variables, and you can wrap a client or mark functions with a decorator ([quickstart](https://docs.langchain.com/langsmith/observability-quickstart.md)):

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=<your key>
```

```python
client = wrap_openai(OpenAI())

@traceable
def assistant(question: str) -> str:
    ...
```

The page says `pip install -U langsmith openai`. These snippets were trimmed by our fetch tool and not run, so copy from the live page. Langfuse and Opik offer the same idea and can be self-hosted ([LLMOps track](lesson:llmops/scoring-and-watching)).

:::warn Traces hold your users' words
Prompts and outputs go into traces. LangSmith has pages on masking inputs, redacting secrets, and sampling. We did not read them. Read them before you trace real user data, and apply the [privacy rules](lesson:rag/fast-cheap-safe) you already have.
:::

## 2. Dashboards

LangSmith has prebuilt dashboards per project: traces, LLM calls, cost and tokens, tools, and feedback scores. You can build custom charts for count, latency, tokens, cost, and feedback score ([dashboards](https://docs.langchain.com/langsmith/dashboards.md)). Gotchas from the page: metadata and tags do not pass from parent runs to child runs, and group-by shows only the top 20.

## 3. Alerts

An alert is a rule on run count, cost, errors, feedback score, or latency over a 5 or 15 minute window. It can notify Slack, PagerDuty, Dynatrace, or a webhook ([alerts](https://docs.langchain.com/langsmith/alerts.md)).

- "Send Test Alert" does **not** check that the receiver worked. Check it yourself.
- Filters allow AND only.
- PagerDuty will not open a new incident while one is open for the same alert.

## Which alerts to set first

| Alert | Why |
|---|---|
| Error rate above a few percent | Something broke |
| Slow responses (p95 latency) | Users are waiting |
| Cost per hour above normal | A loop may be burning money |
| Feedback or eval score drops | Quality fell even though the system is up |

Pick thresholds from a week of real data, not guesses.

:::check A dashboard shows zero errors but users say answers are wrong. What is missing?
Quality signals: feedback scores and evals. Error counts only show crashes, not wrong but well-formed answers.
:::
