---
title: Agents, trees, graphs, and what RAGFlow leaves out
summary: RAGFlow's tool-using search loop, its summary tree and knowledge graph, its workflow canvas, and a list of what it does not do, each linked to the lesson that shows how to build it.
time: 20 min
---

The last two lessons covered the normal path: index, search, answer. This one covers the advanced parts, then lists what is missing.

:::note Source
Read from RAGFlow's Go code at commit [`eabad0c74`](https://github.com/infiniflow/ragflow/tree/eabad0c74c73bfa74e218c1fb751da68c1914833) (15 October 2026). We read the code; we did not run RAGFlow. "We did not find X" means we searched the code for it and found nothing. It does not prove X can't exist somewhere we didn't look.
:::

## Agentic search

RAGFlow's agentic mode is the [tool-using loop](lesson:rag/agentic-rag#give-the-model-search-tools) from the RAG track, built on ByteDance's `eino` agent framework ([`agent.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/agentic_rag/agent.go)). The model gets a toolbox and decides what to call next:

| Tool | What it does |
|---|---|
| `search_chunks` | Hybrid search; the model can set the keyword/vector weight |
| `search_bm25_chunks` | Keyword search only |
| `search_semantic_chunks` | Vector search only |
| `grep_chunks` | Regex search over chunk text |
| `list_chunks` | Read the full text of chunks by ID (the "read closely" step) |
| `search_metadata` | Search document metadata |
| `think`, `todo_write` | Write down reasoning or a plan |
| `run_javascript` | Run a small calculation |
| `navigate_tree`, `navigate_structure`, `graph_explore` | Walk the summary tree, document structure, or knowledge graph, when those exist |
| `web_search` | Search the web, when enabled |

How it stays safe:

- **A round limit.** The loop stops after 120 model turns by default. A code comment says this was raised from 50 because multi-step test questions needed more, and that a duplicate-search guard stops the extra turns from being wasted.
- **Parallel tool calls.** Calls made in the same turn run at the same time.
- **Cite only what was shown.** An `EvidenceRegistry` gives each passage an `[ID:n]` the first time the model sees it. At the end, citations that point to nothing shown are dropped.
- **Always an answer.** If the loop runs out or fails, `finalizeAnswer` writes an answer from what was found.

There is also a simpler **deep research** mode ([`deep_researcher.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/service/deep_researcher.go)): search, ask a model whether that is enough, and if not, ask it for 2 or 3 sub-questions and search those, up to depth 3. That is the [decompose and recurse](lesson:rag/agentic-rag#a-middle-ground-decompose-and-recurse) pattern.

## The summary tree (RAPTOR)

[`raptor.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/ingestion/component/knowledge_compiler/tree/raptor.go) says in its own comments that it implements RAPTOR, the [tree of summaries](lesson:rag/beyond-chunks). It is an optional step that runs after chunking. Two differences from the paper:

- Grouping keeps document order. A "watershed" method splits the sequence of chunks into neighbouring groups, instead of clustering chunks from anywhere in the document.
- It can pull short claims out of each chunk first, and group by the claims instead of the raw text.

## The knowledge graph

A model extracts **entities** (people, organizations, products, rules, places) and then **relations** between known entities, using a fixed list of types. Things first, links second, as in [GraphRAG](lesson:rag/beyond-chunks#how-graphrag-builds-its-graph).

There is no separate graph database. Entities and relations are stored as ordinary rows in the same search engine as the chunks, marked with a `knowledge_graph_kwd` field. Two things read them:

- `graph_explore`, an agent tool that finds matching entities, walks out a few hops, and returns the subgraph with source passages.
- A graph search in normal chat ([`internal/service/graph`](https://github.com/infiniflow/ragflow/tree/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/service/graph)) that looks up entities, relations and paths, plus **community reports**, and adds the result as one extra note in the prompt.

The search code **reads** rows marked `community_report`. We found no code in `internal/` that **writes** them, and no Leiden, Louvain or other community-finding algorithm. Community reports are what make GraphRAG's global questions work. So at this commit, the reading side exists and the writing side, as far as we can find, does not. It may have been left behind in the Go rewrite, or it may come from somewhere outside this code.

## The workflow canvas

Beyond chat, RAGFlow has a visual workflow builder, the **canvas**. A workflow is a graph of components (model calls, retrieval, tools, branches) stored as JSON ([`canvas.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/agent/canvas/canvas.go)). If you have seen LangGraph, it is the same idea ([LangGraph by hand](lesson:agents/langgraph-by-hand)).

- **No cycles.** The `eino` workflow must be a DAG (a graph with no loops back). A Loop component is expanded into its own sub-workflow with a stop condition ([`scheduler.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/agent/canvas/scheduler.go)).
- **Branches.** `Categorize` lets a model choose a branch. `Switch` uses plain rules.
- **Pause for a human.** A form component can stop a running workflow, save a checkpoint, and resume where it stopped when the person answers, without re-running earlier steps. This is the [human approval](lesson:agents/middleware-and-approval) pattern.

## What RAGFlow does not do

Each gap is something the RAG track teaches. If you adopt RAGFlow and need one of these, the lesson shows the idea.

| Not found | What that means | Where to learn it |
|---|---|---|
| A quality evaluation framework | No precision, recall, MRR, NDCG or faithfulness scores. `test/benchmark/` measures speed and success rate, and its README says so plainly. | [Measure quality](lesson:rag/measure-quality), [judging answers](lesson:rag/judging-answers) |
| RRF | All hybrid merging is a weighted sum. | [Retrieval](lesson:rag/retrieval-that-works) |
| HyDE | Questions are always embedded as written, maybe with keywords or a translation. | [Rerank and rewrite](lesson:rag/rerank-and-rewrite) |
| Model-written context notes per chunk | It writes questions, keywords and summaries, not an Anthropic-style "where this chunk sits" note. | [Contextual chunks](lesson:rag/contextual-chunks) |
| Semantic or late chunking | All cutting is by delimiters, tokens, headings or file shape. | [More ways to chunk](lesson:rag/more-ways-to-chunk) |
| Writing community reports | Read at search time, never produced. | [Beyond chunks](lesson:rag/beyond-chunks#how-graphrag-builds-its-graph) |
| A CRAG-style grader | Deep research checks whether evidence is enough, and the agent can choose web search, but nothing grades results as correct, incorrect or ambiguous. | [Agentic RAG](lesson:rag/agentic-rag) |
| Self-RAG | Needs a specially trained model. RAGFlow calls existing models and trains none. | [Agentic RAG](lesson:rag/agentic-rag) |

Two things we did not settle: whether RAGFlow removes duplicate chunks or documents (we did not look), and the `resume` chunking mode the Python version had. We did not find it in the Go code.

The first gap matters most. Without a test set and scores, nobody can tell whether a change to the weight, the chunk size or the reranker helped. If you run RAGFlow, building that test set is the first job.

:::check RAGFlow's graph search reads community reports, but nothing writes them. What kind of question suffers most?
Global questions, such as "what are the main themes across these documents?". Local questions that start from named entities can still use entities and relations.
:::

:::check You adopt RAGFlow and want to know whether switching on the reranker helped. What do you build first?
A test set of real questions with known right chunks and answers, and a script that scores search and answers before and after the change. RAGFlow has no built-in quality scores.
:::

Want the full list of files we read? See the [RAGFlow research note](lesson:research/ragflow).
