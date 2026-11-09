---
title: What an agent is, and your first one with LangChain
summary: An agent is a model that calls tools in a loop until the job is done. See the idea, then the 15-line LangChain version.
time: 15 min
---

A plain model call is one question and one answer. An **agent** adds a loop:

1. The model reads the task and decides: answer now, or use a tool.
2. If it picks a tool (a function you wrote), your code runs it and gives the result back.
3. The model reads the result and decides again.
4. It stops when it has an answer.

The LangChain docs put it as "Agent = Model + Harness". The harness is everything you wrap around the model: the prompt, the tools, and any rules. The [Harness track](lesson:harness/what-is-a-harness) goes deep on this. This lesson is about the LangChain way to build one.

## The LangChain ecosystem on one page

From [the docs' build overview](https://docs.langchain.com/build-overview):

| Name | What it is |
|---|---|
| **LangChain** | A framework for building agents: models, tools, prompts, middleware |
| **LangGraph** | Lower-level tool for stateful, long-running agents drawn as a graph. LangChain agents run on top of it. |
| **Deep Agents** | A ready-made agent harness for long, multi-step work, built on LangChain and LangGraph |
| **Managed Deep Agents** | Deep Agents run for you on LangSmith's infrastructure |
| **LangSmith** | The platform for tracing, testing, deploying and monitoring |
| **OpenWiki** | A command-line tool that writes a wiki about a codebase for coding agents |

Each has its own lesson in this track or the Evals and Deploy tracks.

## Your first agent

This is the example from the [LangChain overview](https://docs.langchain.com/oss/python/langchain/overview.md), copied as the docs show it:

```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="openai:gpt-5.5",
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
)
print(result["messages"][-1].content_blocks)
```

Install line from the same page: `pip install -qU langchain "langchain[openai]"`.

Read it as the loop above. The docstring of `get_weather` is what the model reads to learn what the tool does. The type hint `city: str` tells it what to send. `create_agent` builds the loop.

:::warn What we did and did not run
We did **not** run this example, since it needs a model provider key. Model names in docs change often, so check yours exists. The page states no package versions, so pin your own. To see an agent-style loop that you can run with no key, use [the mini harness](lesson:harness/build-a-mini-harness).
:::

## Messages and models

Under the hood, an agent passes **messages**: system (rules), human (user), AI (model), and tool (a tool's result, which must reference the call it answers). `init_chat_model("<name>")` builds a model, and every provider uses the same interface, so switching is a small change ([models](https://docs.langchain.com/oss/python/langchain/models.md), [messages](https://docs.langchain.com/oss/python/langchain/messages.md)).

For a fixed output shape, pass `response_format` with a data class and read `result["structured_response"]`. This is the [structured output idea](lesson:foundations/structured-output) built in. With one strategy, a validation failure is sent back to the model for a retry ([structured output](https://docs.langchain.com/oss/python/langchain/structured-output.md)).

:::check In the example, what tells the model what `get_weather` does?
The function's docstring, plus its type hints. Write them for the model, not just for people.
:::
