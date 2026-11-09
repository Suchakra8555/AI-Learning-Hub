---
title: Middleware and human approval
summary: Put rules around each step of the loop, and pause the agent before a risky action until a person says yes.
time: 15 min
---

An agent that can act can act wrongly. Two LangChain features add control without rewriting the agent.

## Middleware: code that runs around each step

**Middleware** runs before and after each step of the agent loop. The docs list uses such as summarizing long chats, human approval, retries, model fallback, call limits, and PII detection ([overview](https://docs.langchain.com/oss/python/langchain/middleware/overview.md)).

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware, HumanInTheLoopMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[
        SummarizationMiddleware(...),
        HumanInTheLoopMiddleware(...)
    ],
)
```

The `...` are placeholders in the docs. The overview does not list the hooks or every built-in, and we did not read the pages that do. Read the built-in and custom middleware pages first. The agents page names `ModelRetryMiddleware(max_retries=3)` and `ToolRetryMiddleware(max_retries=2)` for rate limits and timeouts ([agents](https://docs.langchain.com/oss/python/langchain/agents.md)).

Always cap the loop (see [agentic RAG](lesson:rag/agentic-rag)). Look for a model call limit before you ship.

## Pausing for a person

Some actions should wait: deleting files, sending email, spending money. LangGraph's `interrupt()` pauses the run and saves its state. Later you resume with the human's answer, using the same **thread ID**, which is the name of the conversation ([interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts.md)).

Here is a runnable version with no model and no key: `code/agents/graph_demo.py`.

```python
def ask_human(state):
    return {"approved": interrupt("Delete old files?")}
...
paused = graph.invoke({"steps": [], "approved": False}, config)
done = graph.invoke(Command(resume=False), config)   # a human says no
```

Real output, tested with `langgraph` 1.2.19:

```text
paused: Delete old files?
steps: ['plan: delete old files', 'act: skipped']
```

The first call stops at the question. The second call resumes with "no", so the action is skipped. This is the same approval gate as in the [mini harness](lesson:harness/tools-and-permissions), done with a library.

## Things the docs warn about

- On resume, the paused step **restarts from its top**, so code before `interrupt()` runs again. Keep it safe to repeat.
- Do not wrap `interrupt()` in a broad try/except.
- `InMemorySaver` loses everything on restart. The docs recommend a Postgres saver for production, and old checkpoints pile up, so plan cleanup ([persistence](https://docs.langchain.com/oss/python/langgraph/persistence.md)).

:::check Why does the resume call need the same thread ID as the first call?
The saved state is stored under that ID. A different ID would start a new run and not continue the paused one.
:::
