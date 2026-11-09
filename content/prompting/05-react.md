---
title: ReAct: think, act, look, repeat
summary: A prompt pattern that lets a model alternate between reasoning and using tools, so it can look things up instead of guessing.
time: 12 min
---

Ask a model "Who directed the film that won Best Picture the year the Eiffel Tower turned 100?" and it may answer from memory and be wrong. It cannot look anything up. Chain of thought gives it more steps, but the steps still run on what it remembers.

**ReAct** (reason plus act) gives it a way out. The model writes a thought, picks an action such as a search, reads the result, and thinks again.

## The loop

```text
Question: How many people live in the capital of the country that hosted the 2016 Olympics?

Thought: The 2016 Olympics were in Brazil. I need the capital, then its population.
Action: search("capital of Brazil")
Observation: Brasilia

Thought: Now I need the population of Brasilia.
Action: search("population of Brasilia")
Observation: (a number from the tool)

Thought: I have what I need.
Answer: (the number, with its source)
```

Three labels repeat: **Thought**, **Action**, **Observation**. Your code runs the actions. The model never runs anything by itself. Your code reads each `Action:` line, calls the tool, and pastes the result back as the `Observation:`.

## Why it helps

- The model checks facts with a tool instead of recalling them.
- A wrong first search is visible, and the next thought can fix it.
- You can read the trace to see where it went wrong.

Yao and co-authors introduced the pattern and reported gains on question answering, fact checking and interactive tasks. See the [paper abstract](https://arxiv.org/abs/2210.03629).

## Where you have seen this

This is the same shape as an agent. Read [what is an agent](lesson:agents/what-is-an-agent) for the idea in general and [the agent loop](lesson:harness/the-agent-loop) for how real harnesses run it. ReAct is the prompt-level version. Modern APIs often put tool calls in a structured field instead of free text, but the loop is the same.

## Costs and limits

- **Many calls.** Each loop turn is another model call with a longer prompt.
- **Wrong action, wrong path.** If the model picks a bad tool or query, later thoughts build on it.
- **Needs a stop rule.** Cap the number of turns, or a confused model will loop.
- **Tool output is untrusted text.** A web page can contain instructions. Do not let it act as the prompt.

:::try
Write the ReAct prompt above for a tool you have, for instance a function that looks up a product price. Say in the prompt exactly how to format `Action:` lines. Then write ten lines of code that read the action and return the observation. I did not run this for you.
:::

:::say
ReAct lets the model look things up between thoughts, so it stops guessing.
:::

:::check What is the model's job in ReAct, and what is your code's job?
The model writes thoughts and chooses actions. Your code runs the action and returns the result as an observation.
:::

## Sources

Based on GeeksforGeeks, [ReAct prompting](https://www.geeksforgeeks.org/artificial-intelligence/react-reasoning-acting-prompting/), which loaded fine. Paper: Yao et al., [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) (2022), abstract read and confirmed.
