---
title: Vectors at scale, faster search and smaller storage
summary: Approximate search, the HNSW settings you will be asked about, shrinking vectors to a quarter or less of their size, and changing embedding models without downtime.
time: 18 min
---

Our toy search compares the question with every chunk. That is called **exact** or **brute-force** search. It is perfect, and fine up to tens of thousands of chunks. At ten million chunks with 1,024 numbers each, every question means ten billion multiplications, and the vectors alone take about 40 GB of memory. Two things have to give: how you search, and how you store.

## Approximate search

**Approximate nearest neighbour** search (**ANN**) gives up a little accuracy for a lot of speed. It returns *almost* the closest vectors, much faster than checking them all. Most vector databases use ANN by default.

The most common kind is **HNSW** (hierarchical navigable small world, [paper](https://arxiv.org/abs/1603.09320)). Picture a road network. Each vector links to a handful of near neighbours. Search starts somewhere, keeps walking to whichever neighbour is closer to the question, and stops when no neighbour is closer. Extra layers of long-distance "highways" on top get you to the right area fast.

Three settings come up in every vector database. pgvector's README names them `m`, `ef_construction` and `hnsw.ef_search` ([docs](https://github.com/pgvector/pgvector)):

| Setting | What it controls | Raise it and |
|---|---|---|
| `M` | Links per vector | Better recall, more memory |
| `ef_construction` | How hard it looks for good links while building | Better recall, slower indexing |
| `ef_search` | How many candidates it keeps while searching | Better recall, slower questions |

Leave the defaults alone until you have a test set. Then measure **recall against exact search**: run the same questions through brute force and through HNSW, and count how many of the exact top 10 HNSW also returns. If that number is low, raise `ef_search` first, since it needs no rebuild.

The other family you will see is **IVF** (inverted file): group the vectors into clusters, then search only the few clusters nearest the question. FAISS documents both ([wiki](https://github.com/facebookresearch/faiss/wiki/Faiss-indexes)).

:::warn Filters and ANN
"Find similar chunks, but only ones this user may see" is harder than it sounds. If the database finds the top 10 first and filters after, a strict filter can leave 0 results. Check how your database combines filters with ANN, and test with your strictest real filter. See [access control](lesson:rag/fast-cheap-safe).
:::

## Smaller vectors

A float32 number takes 4 bytes. You can store less:

- **int8**: round each number to one of 255 steps. 1 byte each.
- **binary**: keep only whether each number is positive. 1 bit each, 32 times smaller.
- **Fewer numbers.** Some models are trained so the first 256 numbers of a 1,024-number vector still work on their own. These are called **Matryoshka** embeddings, after the nesting dolls ([paper](https://arxiv.org/abs/2205.13147)). OpenAI's newer embedding models take a `dimensions` setting for this ([docs](https://developers.openai.com/api/docs/guides/embeddings)).

`code/rag/vector_scale.py` tries all four on toy vectors and checks two things: how many of the exact top 3 each version still returns ("agree"), and the usual scores.

```bash
cd code/rag
python vector_scale.py
```

```text
29 sentences, 256-number vectors, 20 questions

store       bytes  agree@3
float32      1024     100%
int8          260     100%
binary         32      70%
first 64      256      48%

float32                top-1  55%   top-3  85%   MRR 0.69
int8                   top-1  55%   top-3  85%   MRR 0.68
binary                 top-1  50%   top-3  75%   MRR 0.61
first 64               top-1  35%   top-3  70%   MRR 0.49
```

- **int8 lost nothing** at a quarter of the size. That matches what most people see, and it's the first thing to try.
- **binary kept 70%** of the exact results at 1/32 of the size. The usual trick is to search binary vectors for a wide net of candidates, then re-score that short list with the full vectors.
- **First 64 numbers did badly**, and that is expected. Our toy vectors were not trained to put the important information first. A real Matryoshka model is. This row shows the mechanics only.

:::note We wrote a bug first
Our first int8 version scored only 82% agreement. Each stored vector had its own rounding step, and the score ignored it. Keep the step with each vector and multiply it back in. If quantization looks worse than people report, check this first.
:::

## Changing the embedding model

You will change models: a better one comes out, or a cheaper one. Every vector must be rebuilt, since vectors from two models cannot be compared ([lesson 6](lesson:rag/embeddings-and-vectors)).

1. Build the new vectors in a new field or index, beside the old ones.
2. Run your test set on both.
3. Switch reads to the new one if it wins.
4. Delete the old one a few days later.

Naming the field after the vector length (`vec_768`, `vec_1024`) makes step 1 natural. See [keeping data fresh](lesson:rag/keeping-data-fresh).

:::check Your HNSW index answers fast but misses chunks that brute force finds. Which setting do you try first, and why?
`ef_search`. It widens the search at question time and needs no rebuild. `M` and `ef_construction` only change when you rebuild the index.
:::

:::check Binary vectors are 32 times smaller but less accurate. How do teams get most of both?
Search the binary vectors for a wide list of candidates, then re-score only those candidates with the full-size vectors.
:::
