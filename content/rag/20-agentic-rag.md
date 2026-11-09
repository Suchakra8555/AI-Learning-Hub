---
title: Agentic RAG, letting the model decide how to search
summary: Normal RAG searches once. Agentic RAG lets the model search, look at the results, and try again. It helps on hard questions and costs more.
time: 15 min
---

Normal RAG is a straight line: question, search, answer. If the search misses, the answer is bad, and nothing tries again.

**Agentic RAG** puts search inside a loop the model controls:

1. Look at the question. Does it need a search at all?
2. Search.
3. Check the results. Are they good enough?
4. If not, rewrite the question and search again. If yes, answer.

```python
def agentic_answer(question, max_rounds=3):
    query = question
    for _ in range(max_rounds):                  # a hard limit, always
        chunks = search(query)
        verdict = grade(question, chunks)        # a model call: "good" or "bad"
        if verdict == "good":
            return answer(question, chunks)
        query = rewrite(question, chunks)        # a model call: try new words
    return "I could not find that in the documents."
```

This is a sketch, not tested code: `search`, `grade`, `rewrite` and `answer` are placeholders for the pieces you already built.

## Ideas from research

These are named in the Awesome-RAG list. We read their abstracts or pages only:

- **Corrective RAG (CRAG).** A small checker grades what search returned as *correct*, *incorrect* or *ambiguous*. Correct: use it, after cutting the useless sentences. Incorrect: throw it away and search the web. Ambiguous: do both ([paper](https://arxiv.org/abs/2401.15884)). The `grade` step in the sketch above is a simpler, two-way version of this checker.
- **Self-RAG.** A specially trained model decides when to look things up and checks its own claims against sources, using special tokens it learned to emit ([page](https://selfrag.github.io/)). It needs special training, so most teams copy the idea with a plain loop like the one above.

## Give the model search tools

The sketch above runs one kind of search. A stronger version hands the model several tools and lets it choose, the same loop as any [tool-using agent](lesson:harness/the-agent-loop):

| Tool | Use it for |
|---|---|
| Keyword search | Exact names, codes, phrases |
| Vector search | Describing something in other words |
| Hybrid search | A good default |
| Pattern search (regex) | "Every chunk that mentions `ERR-\d+`" |
| Read a whole chunk or section by ID | Reading closely after a search found a hint |
| Metadata search | "Which documents are from 2025?" |

The model alternates: search, read, decide, search again. [RAGFlow's agentic mode](lesson:ragflow/agents-trees-graphs-and-gaps) is a real example with roughly this tool list.

Two rules make this safe to ship:

- **Cite only what was shown.** Give each passage a short ID, such as `[ID:7]`, the first time the model sees it, and keep a list. When the answer comes back, drop any citation whose ID is not on the list. The model cannot cite a passage it never read.
- **Always end with an answer.** When the round limit is hit or a tool fails, run one last model call: "answer from what you have found so far, and say what is missing". The user never gets a blank screen.

## A middle ground: decompose and recurse

Full tool use is the most flexible and the hardest to test. A simpler pattern sits in between:

1. Search with the question.
2. Ask a model: is this enough to answer? If yes, stop.
3. If not, ask it for 2 or 3 new sub-questions that target what is missing.
4. Repeat for each sub-question, up to a fixed depth such as 3.

This is sometimes sold as "deep research". The code path is fixed, so it is easier to log and test than an open tool loop.

## What it costs

| Gain | Price |
|---|---|
| Handles questions that need two searches | 2 to 4 times the model calls |
| Recovers from a bad first search | Slower answers |
| Can pick between sources | Harder to test and debug |

:::warn Always cap the loop
Without `max_rounds`, a confused model can search forever and spend your budget. Set a hard limit, log each round, and fall back to "I could not find that".
:::

Use it when single-search recall is the problem you have measured. Otherwise, fix chunking and search first. This pattern is the bridge to the [Harness track](lesson:harness/the-agent-loop), where the same loop appears with tools and permissions.

:::check Why is a round limit non-negotiable in an agentic loop?
The loop is controlled by a model's judgment, which can fail. A fixed limit guarantees that cost and time stay bounded.
:::
