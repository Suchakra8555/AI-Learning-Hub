---
title: How RAGFlow searches and answers
summary: Weighted-sum hybrid search instead of RRF, a reranker blended into the score, four question rewrites in a fixed order, and two ways to get citations.
time: 18 min
---

This lesson follows a question from the chat box to a cited answer. It is the second half of the [map](lesson:ragflow/tour).

:::note Source
Read from RAGFlow's Go code at commit [`eabad0c74`](https://github.com/infiniflow/ragflow/tree/eabad0c74c73bfa74e218c1fb751da68c1914833) (15 October 2026). We read the code; we did not run RAGFlow. The search code is mostly in [`retrieval.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/service/nlp/retrieval.go) and [`reranker.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/service/nlp/reranker.go).
:::

## Step 1: rewrite the question

Before searching, the chat pipeline can run four rewrites, always in this order. Each is a model call, and each is off unless the chat settings turn it on ([`chat_pipeline.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/service/chat_pipeline.go)):

1. **Make the follow-up stand alone** (`refine_multiturn`). Only runs when the chat has more than one question.
2. **Translate** (`cross_languages`). Translates the question into the configured languages and searches with the translation.
3. **Metadata filter** (`meta_data_filter`). A model turns the question into conditions such as `year = 2025`. Filters run inside the search engine where possible, and in memory otherwise. There are three modes: the model picks any field, the model picks from fields you allow, or you write the conditions yourself.
4. **Keyword extraction.** A model lists keywords, and they are added to the search text to help keyword search.

Compare with [rewrite the question](lesson:rag/rerank-and-rewrite#upgrade-2-rewrite-the-question). Keyword extraction is a form of query expansion. Multi-query search exists only in the separate "deep research" mode ([next lesson](lesson:ragflow/agents-trees-graphs-and-gaps)). We found no HyDE.

## Step 2: search, and merge with a weighted sum

There are three modes. No embedding model set: keyword only. `VectorOnly` on: vector only. Otherwise: hybrid.

Hybrid merges with a **weighted sum**, not RRF:

```text
score = (1 - w) * keyword_score + w * vector_score
```

The default `w` (`vector_similarity_weight`) is **0.3**, so keyword search gets 70% of the weight. In vector-only mode the default is 1.0, and a code comment explains why: in that mode, the words of the query are not reliable signals. We found no RRF anywhere in the Go code.

Two details:

- With the Infinity engine, the weighted sum runs inside the engine. With Elasticsearch and others, the engine query uses near-zero keyword weight (`"0.001,1"`) just to collect candidates. The real weights are applied afterwards in Go.
- Tags and a per-document PageRank-style score are then **added** to the result, as hand-tuned boosts.

The RAG track's [fusion comparison](lesson:rag/retrieval-that-works#the-other-way-to-merge-a-weighted-sum) showed that raw BM25 scores swamp vector scores in a weighted sum. RAGFlow avoids that in its Go-side blend: the keyword score there is not raw BM25. `TokenSimilarity` gives each query word and each pair of neighbouring words a weight, then scores a chunk by **the share of that weight it contains**. That number runs from 0 to 1, the same range as cosine similarity, so the 0.3 dial means roughly what it says.

## Step 3: rerank, inside the blend

The search returns 64 candidates by default. If a rerank model is set, its score **replaces the vector score** in the same formula:

```text
score = (1 - w) * keyword_score + w * rerank_score
```

So the reranker is blended in, not used alone. Two things guard the blend:

- **Normalization.** `NormalizeRerankScores` rescales reranker scores to 0..1. A code comment gives the reason: some providers return negative raw scores, which would sink good chunks.
- **Natural text.** The reranker gets the chunk's plain text, not the stemmed tokens used for keyword search, because neural rerankers read real sentences better.

With a reranker on, asking for page 2 is an error. That is the paging rule from [rerank and rewrite](lesson:rag/rerank-and-rewrite#two-traps-when-you-mix-reranker-scores-in).

With no rerank model, a fallback scores word overlap, weighting title words, keywords and generated questions higher, and blends that with vector similarity.

## Step 4: build the prompt

Each chunk becomes a numbered note:

```text
ID: 0
├── Title: <document name>
├── URL: ...
└── Content:
<chunk text>
```

The `ID` is the chunk's position in this prompt, and the same position in the `reference.chunks` list the browser receives. A citation `[ID:0]` is an index into that list, not a database key.

Notes are added best first until 97% of the token budget is used. For chat history, it keeps the system prompt and the latest message first, drops older turns, and trims if it is still too long. That is the [window plan](lesson:rag/prompt-and-citations#fit-everything-in-the-window) from the RAG track.

## Step 5: citations, two ways

**Normal chat** ([`citation.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/service/citation.go)):

1. The prompt asks for `[ID:n]` markers, at most 4 per sentence.
2. `RepairBadCitationFormats` turns near-misses like `(ID: 12)` or `【ID: 12】` into the right format.
3. The markers are read off the answer.
4. If the model wrote **no** markers, `InsertCitations` adds them. It embeds each answer sentence and each chunk and links a sentence to the chunks closest to it. It starts strict (0.63 similarity) and loosens step by step down to 0.3 until it finds a match.

That is the repair-then-fallback approach from [the prompts lesson](lesson:rag/prompt-and-citations#when-the-model-writes-citations-badly-or-not-at-all), with embeddings in place of our word overlap.

**Agentic mode** uses a stricter rule, covered in the [next lesson](lesson:ragflow/agents-trees-graphs-and-gaps): an ID is handed out only when a passage is shown, and unknown IDs are dropped.

## Step 6: stream it

The answer streams to the browser as server-sent events. A buffer holds back partial text, so a marker split across two pieces (`[ID:` then `3]`) is neither shown broken nor stripped by mistake.

:::check RAGFlow blends with a weighted sum but uses a 0-to-1 keyword score instead of raw BM25. What problem does that avoid?
Scale mismatch. Raw BM25 scores can run far above 1 while cosine stays at or below 1, so a raw blend lets keyword search dominate whatever weight you set. With both scores on 0 to 1, the weight means roughly what it says.
:::

:::check Why might a team choose a weighted sum over RRF anyway?
It has a dial. You can tune how much keyword versus vector counts per collection, and you can blend in other scores, such as a reranker's, in the same formula.
:::
