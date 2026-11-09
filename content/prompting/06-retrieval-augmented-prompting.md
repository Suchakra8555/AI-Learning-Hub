---
title: Retrieval-augmented prompting
summary: Paste the right documents into the prompt so the model answers from them, not from memory.
time: 10 min
---

You ask a model about last month's research on AI in healthcare. It gives a tidy overview from its training and misses everything recent. Its knowledge stops at a date, and it knows nothing about your own files.

**Retrieval-augmented prompting** fixes this at the prompt level. You find relevant text first, put it in the prompt, and tell the model to answer from it.

## Without and with

| | Prompt | Result |
|---|---|---|
| Without | "What is the latest research on AI in healthcare?" | A general overview from memory. |
| With | "Using only the three abstracts below, summarize the latest findings. Say which abstract each point comes from.\n\n[1] ...\n[2] ...\n[3] ..." | A summary tied to text you can check. |

Two steps are needed:

1. **Retrieve.** Search a database, the web, or your files for text that matches the question.
2. **Prompt.** Put that text in the prompt with rules about how to use it.

## How this relates to RAG

This is the prompt half of RAG. The full system, with chunking, embeddings and search, is in [what is RAG](lesson:rag/what-is-rag). The wording of the prompt that keeps answers honest is in [prompts that stay honest, with sources](lesson:rag/prompt-and-citations). Read those rather than repeating them here.

## A prompt that works

```text
Answer using ONLY the notes below.
If the notes do not contain the answer, say "I don't have that information."
After each fact, add the note number in brackets.

NOTES:
[1] ...
[2] ...

QUESTION: ...
```

The rule to answer only from the notes, plus an exit line, is what turns retrieval into reliable answers.

## Limits

- **Garbage in, garbage out.** If the retrieved text is wrong or old, the answer will be too.
- **Missing text.** If nothing relevant is found, a model without an exit line will guess.
- **Cost and delay.** Search takes time, and longer prompts cost more.
- **Prompt injection.** Retrieved text can hold instructions. Tell the model that notes are data, not commands.

:::say
Put the evidence in the prompt, and tell the model to stick to it.
:::

:::check Retrieval returns nothing useful and the model still answers confidently. What was missing from the prompt?
An exit line, such as "If the notes do not say, answer: I don't have that information."
:::

## Sources

Based on GeeksforGeeks, [Retrieval augmented prompting](https://www.geeksforgeeks.org/artificial-intelligence/retrieval-augmented-prompting/), which loaded fine. No arXiv link here, because the page names no single paper.
