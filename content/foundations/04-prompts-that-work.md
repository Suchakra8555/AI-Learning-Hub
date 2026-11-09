---
title: Prompts that work
summary: A prompt is a spec. Say who the model is, what to do, what to use, and what the answer looks like.
time: 15 min
---

Most prompt problems are the same problem: the prompt asks for something vague, and the model fills the gap with a guess. Write the prompt like a short work ticket for a new colleague who knows nothing about your project.

## Four parts

1. **Role and goal.** "You answer questions for a store's customers."
2. **Rules.** "Use only the notes below. If they do not contain the answer, say you do not know."
3. **Material.** The documents, data, or examples the model should use.
4. **Output shape.** "Reply in two sentences." or "Reply as JSON with these fields."

Compare:

| Weak | Better |
|---|---|
| "Summarize this." | "Summarize this support ticket in two sentences for an engineer. Include the error message if there is one." |
| "Is this good?" | "Rate this answer 1 to 5 for whether every claim is backed by the notes. Explain in one sentence." |

## Show examples

Two or three examples of input and wanted output teach the model your format faster than a paragraph of description. This is called **few-shot** prompting.

```text
Message: "Where is my package?"        -> {"topic": "shipping", "urgent": false}
Message: "My tent has a hole, I need a refund today" -> {"topic": "returns", "urgent": true}
Message: "<the new message>"           ->
```

## Habits that save time

- **Keep prompts in files or constants,** not scattered in code. You will edit them a lot.
- **Change one thing at a time.** Otherwise you will not know what helped.
- **Test on a fixed set of questions,** not on one that happened to work. [Measuring quality](lesson:rag/measure-quality) shows how.
- **Treat user text as data.** If a user can type into the prompt, they can type "ignore the rules above". See [prompt injection](lesson:rag/fast-cheap-safe).

:::check Why do few-shot examples often beat a long description?
They show the exact format and edge cases once, so the model copies the pattern instead of guessing from words.
:::

This lesson covers the habits that matter most. The [Prompt engineering track](lesson:prompting/what-prompt-engineering-is) goes further: zero-, one- and few-shot examples, chain of thought, ReAct, guardrails and more.
