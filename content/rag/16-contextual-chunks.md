---
title: Contextual chunks, so a piece still knows where it came from
summary: A chunk cut from the middle of a document loses its subject. Add a short note about where it came from before you index it.
time: 15 min
---

Take this chunk, cut out of a long report:

> "The company's revenue grew by 3% over the previous quarter."

Which company? Which quarter? Alone, the chunk cannot say. A search for "ACME Q2 2023 revenue" may skip it, because the words "ACME" and "Q2" are not in the chunk.

## The fix: put the context back

**Contextual retrieval** adds a short note to each chunk before indexing. Anthropic describes it as prepending a 50 to 100 token explanation of where the chunk sits in the document, and using it for both vector and keyword search ([source](https://www.anthropic.com/engineering/contextual-retrieval)).

```text
This chunk is from ACME Corp's Q2 2023 SEC filing. The previous quarter's revenue was $314 million.
The company's revenue grew by 3% over the previous quarter.
```

Their reported results, measured as the share of searches where the right chunk was missing from the top 20:

| Setup | Missed |
|---|---|
| Plain vector search | 5.7% |
| With context notes | 3.7% |
| Plus keyword (BM25) search | 2.9% |
| Plus reranking | 1.9% |

These are the vendor's numbers on their own test data. Test on yours.

## A free version you already have

Our chunker already does a cheap form of this. Every chunk starts with `Title > Section`:

```text
Returns and refunds > Return window
You can return most items within 30 days of delivery...
```

That label costs nothing: no model call. `stage5_advanced.py` measures it by removing and restoring the label:

```text
bm25, no label         top-1  70%   top-3  90%   MRR 0.78
bm25 + context label   top-1  75%   top-3  95%   MRR 0.83
```

One more question found per 20. With a sample this small, treat that as a hint, not proof.

## The model-written version

A model reads the whole document plus one chunk and writes the note. The cost is one model call per chunk, at indexing time only. Because the whole document repeats in every call, **prompt caching** from your provider can cut that cost. Check your provider's current docs for how it works and what it costs.

When your documents change, the notes for changed chunks must be rewritten. Add that to your [freshness plan](lesson:rag/keeping-data-fresh).

## Other things a model can add to a chunk

The same "one model call per chunk at indexing time" budget can buy other additions:

- **Questions this chunk answers.** Index the questions along with the text. A user's question then has a close match even when their words differ from the document's. An early version of this idea is doc2query ([paper](https://arxiv.org/abs/1904.08375)).
- **Keywords.** A few terms, including synonyms the text doesn't use, for keyword search to catch.
- **A one-line summary.** Useful for long chunks and for showing in search results.

For tables and images, a cheaper trick needs no model at all. Attach the paragraph just before and just after, since that text usually says what the table or picture is about. [RAGFlow](lesson:ragflow/ingestion) does both: a model writes questions, keywords and summaries, and nearby text is attached to tables and images.

:::check Why add the context note before indexing and not at question time?
Search compares the question to what is stored. If the stored text lacks the company name, the match fails before the model ever sees it.
:::
