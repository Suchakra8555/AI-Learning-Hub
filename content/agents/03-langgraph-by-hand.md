---
title: LangGraph by hand, state, nodes, and edges
summary: Draw your program as a graph. Four ideas, one small runnable file.
time: 15 min
---

LangGraph lets you write an agent or workflow as a **graph**. Four words cover it ([overview](https://docs.langchain.com/oss/python/langgraph/overview.md), [graph API](https://docs.langchain.com/oss/python/langgraph/graph-api.md)):

| Word | Plain meaning |
|---|---|
| **State** | The shared data that moves through the graph |
| **Node** | A function that reads the state and returns changes to it |
| **Edge** | Which node runs next |
| **Reducer** | How a change merges in: replace the value, or append to a list |

You then **compile** the graph. Compiling is where you attach a **checkpointer**, which saves a snapshot of the state after each step. A **thread** is one conversation's chain of snapshots.

## The file

Open `code/agents/graph_demo.py`. The core is short:

```python
class State(TypedDict):
    steps: Annotated[list[str], add]   # reducer: append, do not replace
    approved: bool

builder = StateGraph(State)
builder.add_node(plan)
builder.add_node(ask_human)
builder.add_node(act)
builder.add_edge(START, "plan")
builder.add_edge("plan", "ask_human")
builder.add_edge("ask_human", "act")
builder.add_edge("act", END)
graph = builder.compile(checkpointer=InMemorySaver())
```

`Annotated[list[str], add]` is the reducer. Each node returns `{"steps": [...]}` and LangGraph **adds** it to the list, so the final list holds every node's note. Without the reducer, each node would overwrite the last.

## Why a graph and not a plain script?

- **Saving and resuming.** Because the state is saved at each step, a run can pause for a human or pick up after a crash.
- **Streaming.** You can watch updates as they happen.
- **Branching.** Edges can choose the next node based on the state, which is how an agent loop is built.

The durable-execution details (how the graph restarts after a failure) are on a page we could not read directly, so this course does not describe them. Read the [LangGraph docs](https://docs.langchain.com/oss/python/langgraph/overview.md) before you rely on it.

## Before production

Do not use `InMemorySaver`. Per the persistence page, use a Postgres-backed saver, call its `setup()` once, and keep `thread_id` under 255 characters.

:::try
Add a fourth node `report` after `act` that appends a final line. Re-run. Then remove the `add` reducer and see what the `steps` list becomes.
:::

:::check What does a reducer decide?
How a node's returned change is merged into the existing state: replace, or append.
:::
