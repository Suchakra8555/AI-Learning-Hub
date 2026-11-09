---
title: A tour of a real RAG product
summary: RAGFlow is an open-source RAG product. This lesson maps its main parts onto the pieces you built in the RAG track, so the next three lessons have somewhere to hang.
time: 12 min
---

You built a RAG system from 50 lines up. This track opens a full product and asks the same questions of it: how does it read files, cut them, search, and answer? Where does it match what the course taught, and where does it make a different choice?

The product is **RAGFlow** ([repo](https://github.com/infiniflow/ragflow)), an open-source RAG engine by InfiniFlow.

:::warn What we read, and what we did not
Everything here comes from reading RAGFlow's source code at commit [`eabad0c74`](https://github.com/infiniflow/ragflow/tree/eabad0c74c73bfa74e218c1fb751da68c1914833) (15 October 2026). We read the code. We did not run RAGFlow or measure it. File links point at that commit. The code moves fast, so the current version may differ. If this lesson and the code disagree, trust the code.
:::

## A note on the language

RAGFlow began as a Python project. At this commit, the server is written in **Go**. The old Python folders (`rag/`, `deepdoc/`, `graphrag/`) now live under [`internal/`](https://github.com/infiniflow/ragflow/tree/eabad0c74c73bfa74e218c1fb751da68c1914833/internal) as Go packages. Many Go files say in comments which Python file they were ported from.

You do not need to read Go for this track. When a Go idea matters, we say what it is in Python terms. One you will meet often: a Go **interface** is a list of methods, like a Python `Protocol`. Any type with those methods fits it, with no "implements" line.

## The map

```text
upload ──► object storage (raw files: MinIO, S3, OSS, GCS)
   │
   └──► job on a queue (NATS) ──► worker runs the ingestion pipeline:
              File → Parser → Chunker → Extractor → Tokenizer
                                                     │ (embeds here)
                                                     ▼
                                     search engine (Elasticsearch, Infinity, ...)
                                                     ▲
question ──► rewrite ──► search (keyword + vector) ──┘
                │
                └──► rerank ──► prompt with [ID:n] notes ──► streamed answer with citations
```

Each piece has a lesson in the RAG track.

| RAGFlow part | What it does | Course lesson |
|---|---|---|
| Parser | Reads PDFs, Office files, images, audio | [Reading documents](lesson:rag/reading-documents) |
| Chunker | Cuts the text, by one of a dozen templates | [Chunking](lesson:rag/chunking), [more ways to chunk](lesson:rag/more-ways-to-chunk) |
| Extractor | Has a model write keywords, questions, summaries per chunk | [Contextual chunks](lesson:rag/contextual-chunks) |
| Tokenizer | Prepares text for keyword search and calls the embedding model | [Embeddings](lesson:rag/embeddings-and-vectors) |
| DocEngine | Stores and searches chunks | [Vectors at scale](lesson:rag/vectors-at-scale) |
| Retrieval service | Keyword, vector and hybrid search, filters, rerank | [Retrieval](lesson:rag/retrieval-that-works) |
| Chat pipeline | Rewrites the question, builds the prompt, cites, streams | [Prompts and citations](lesson:rag/prompt-and-citations) |
| Agentic RAG | A tool-using search loop | [Agentic RAG](lesson:rag/agentic-rag) |

## Three design choices

**Indexing is a pipeline of nodes.** The steps from File to Tokenizer are not hard-coded. Each "chunking mode" is a small JSON graph of nodes, and you can edit the graph ([`pipeline.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/ingestion/pipeline/pipeline.go)). RAGFlow uses the same graph idea for its agent workflows.

**Indexing runs as queued jobs.** Uploading a file creates a task and puts a small wake-up message on a NATS queue. Workers pick tasks up. Each task moves through `CREATED → SCHEDULED → RUNNING`, then ends `COMPLETED`, `FAILED` or `STOPPED` ([`constants.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/common/constants.go)). This is the queue pattern from [going to production](lesson:rag/going-to-production). If you know Python, think Celery with a different broker.

**Storage is swappable.** Chunks, vectors and metadata go to one search engine, chosen in config: Elasticsearch, Infinity (InfiniFlow's own engine), OceanBase, SereneDB or Vastbase. They all fit one Go interface, `DocEngine` ([`engine.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/engine/engine.go)). Raw uploaded files go to a separate object store. Text you search lives in one place, original bytes in another.

:::check RAGFlow stores raw files in object storage and chunks in a search engine. Why keep them apart?
They have different jobs. The search engine needs fast keyword and vector search over small pieces. Object storage keeps the big original files cheaply, so you can re-parse them later with a better reader without asking users to upload again.
:::

:::check Why run indexing as a queued job instead of inside the upload request?
Parsing a large PDF with OCR can take minutes. A queue lets the upload return at once, lets several workers share the load, and lets a failed job be retried on its own.
:::
