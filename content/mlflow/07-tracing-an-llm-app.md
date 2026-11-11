---
title: Tracing an LLM app
summary: Record every step of a small RAG app as a trace with spans, with no model key, and read the traces back. Run on MLflow 3.18.0.
time: 20 min
---

A user says "the bot gave a wrong answer". Which step failed: the search, the prompt, or the model? A **trace** is the record of one request. A **span** is one step inside it, with its input, output and timing ([docs](https://mlflow.org/docs/latest/genai/tracing/)). The [Evals track](lesson:evals/why-test-an-agent) and [Tracing and dashboards](lesson:deploy/tracing-and-dashboards) explain why; this lesson shows MLflow's version.

## Decorators and spans

`code/mlflow/trace_and_eval.py` has a tiny support bot with fake retrieval. The model is a rule so the output is repeatable. The tracing parts:

```python
@mlflow.trace(span_type=SpanType.RETRIEVER)
def retrieve(question): ...

@mlflow.trace(span_type=SpanType.CHAIN)
def answer(question):
    docs = retrieve(question)
    with mlflow.start_span("compose", span_type=SpanType.LLM) as span:
        span.set_inputs({"question": question, "context": docs[0]["page_content"]})
        ...
        span.set_outputs(reply)
```

`@mlflow.trace` wraps a function. `start_span` wraps a block. Span types (the docs list 14) let the UI treat a retriever differently from a model call. Calling `answer()` once produced this trace, read back with `mlflow.search_traces`:

```text
span names + types in one trace: [('answer', 'CHAIN'), ('retrieve', 'RETRIEVER'), ('compose', 'LLM')]
```

## One line for a library

For OpenAI, Anthropic, LangChain and LangGraph you skip the decorators and call an autolog function before your code runs, for example `mlflow.openai.autolog()` or `mlflow.anthropic.autolog()`. LangGraph apps use `mlflow.langchain.autolog()`. We did not run those, because they need provider keys.

## Production

- Install the lighter `mlflow-tracing` package in the serving container. We did not check its current version.
- MLflow can write traces asynchronously and sample them. The docs list the settings. We did not test them.
- It accepts OpenTelemetry traces over HTTP at `/v1/traces` (3.6.0 and later) and can export to other OpenTelemetry systems.
- Traces hold prompts and user text. Decide what to mask before you ship ([safety](lesson:rag/fast-cheap-safe)).
- Since 3.11 a trace can carry `session_id` and `user`, to group a conversation.

## Find the bad ones

`mlflow.search_traces` takes a filter and returns a table or a list. In 3.18 the old `experiment_ids=` argument is deprecated; use `locations=[experiment_id]`. We hit that warning and fixed the script.

:::try
Add a second `retrieve` call inside `answer` and run again. Look at how the span list changes.
:::

:::check Why give the retriever its own span type?
The UI and the evaluation scorers treat retrieved documents specially, so retrieval quality can be judged apart from the answer.
:::
