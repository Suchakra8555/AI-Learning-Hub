---
title: The launch checklist, and what to learn next
summary: One page to check before you let real users in, and a map of the road from here.
time: 10 min
---

Print this. Go through it with a teammate before launch. Each line points back to the lesson that explains it.

## Content

- [ ] We know exactly which documents are indexed, and why. ([4](lesson:rag/reading-documents))
- [ ] Old versions and drafts are excluded or tagged. ([4](lesson:rag/reading-documents))
- [ ] We read sample extracted text for each file type and it looks right. ([4](lesson:rag/reading-documents))
- [ ] Tables are turned into sentences that keep column names. ([4](lesson:rag/reading-documents))

## Search

- [ ] Chunks carry the title and heading. ([5](lesson:rag/chunking))
- [ ] We tried hybrid search and kept whichever the eval favored. ([7](lesson:rag/retrieval-that-works))
- [ ] A refusal threshold is set from real scores. ([13](lesson:rag/going-to-production))

## Answers

- [ ] The prompt says: use only the notes, say so when unsure, cite note numbers. ([8](lesson:rag/prompt-and-citations))
- [ ] Citations are checked against the notes sent. ([8](lesson:rag/prompt-and-citations))
- [ ] The prompt says notes are data and not instructions. ([11](lesson:rag/fast-cheap-safe))

## Quality

- [ ] There is an eval set of at least 50 real-sounding questions, including ones with no answer. ([9](lesson:rag/measure-quality))
- [ ] We have retrieval numbers and have read 20 answers by hand. ([9](lesson:rag/measure-quality))
- [ ] The eval runs on every change. ([9](lesson:rag/measure-quality))
- [ ] We have a failure log and add each bug to the eval. ([10](lesson:rag/when-answers-go-wrong))

## Safety and privacy

- [ ] Access rules filter chunks during search. ([11](lesson:rag/fast-cheap-safe))
- [ ] We know what data leaves our network and it is approved. ([11](lesson:rag/fast-cheap-safe))
- [ ] Logs are access-controlled and expire. ([11](lesson:rag/fast-cheap-safe))
- [ ] We tried to make the bot misbehave and wrote down what happened. ([11](lesson:rag/fast-cheap-safe))

## Running it

- [ ] Input limits, timeouts, limited retries, rate limits. ([13](lesson:rag/going-to-production))
- [ ] A health check and more than one copy running. ([13](lesson:rag/going-to-production))
- [ ] Keys are in a secret store. ([3](lesson:rag/poc-in-50-lines))
- [ ] A budget alarm on model spend. ([11](lesson:rag/fast-cheap-safe))
- [ ] The index refreshes on a schedule, handles deletions, and clears the cache. ([12](lesson:rag/keeping-data-fresh))
- [ ] We can roll back to the last working version quickly. ([12](lesson:rag/keeping-data-fresh))

## People

- [ ] Users can mark an answer as bad. ([13](lesson:rag/going-to-production))
- [ ] Someone owns reviewing feedback every week.
- [ ] The interface tells users this is an AI tool and shows sources.
- [ ] There is a way to reach a human when the bot fails.

## The ladder you climbed

| Stage | What you added | What it fixed |
|---|---|---|
| 1 | A working loop | "Can this work at all?" |
| 2 | Clean text, chunks with headings | Pieces that make sense alone |
| 3 | Hybrid search, rerank, rewrite | Finding the right piece |
| 4 | Honest prompts and citations | Made-up answers |
| 5 | An eval set | Guessing |
| 6 | Cost, speed, safety | Bills, waiting, leaks |
| 7 | A service with logs and feedback | Not knowing what is going on |

## What to learn next

RAG answers questions from documents. The next step in most teams is letting an AI **do things**: call tools, take several steps, and decide what to do next. That is an **agent**.

Agents bring a new set of engineering problems: how to loop safely, how to give tools without giving away the keys, how to record what happened, how to stop. The collection of code that handles all that around the model is called the **harness**. The [Harness track](lesson:harness/what-is-a-harness) starts there.

:::say
RAG gives a model knowledge. A harness gives a model hands, and keeps them on a leash.
:::

Before you move on, the rest of this track holds upgrades to reach for when your test set shows a specific problem: reranking, rewriting the question, other ways to chunk, vectors at scale, judging answers, agentic search, and graphs. Then a case study shows all of it inside one real product.
