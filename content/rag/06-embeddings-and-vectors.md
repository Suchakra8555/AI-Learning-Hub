---
title: Embeddings: search by meaning
summary: How a computer can tell that "customs fees" and "import duties" are about the same thing.
time: 15 min
---

Keyword search has a flaw you already saw. It matches spelling. "Customs fees" and "import duties" share no words, so keyword search treats them as strangers.

**Embeddings** fix that.

## The idea

An **embedding** is a list of numbers that stands for the meaning of a piece of text. A small model reads the text and produces the list. Texts with similar meaning get similar lists.

Think of a map. Each text is a point on the map, and points that mean similar things sit close together. "Customs fees" lands near "import duties". "Banana bread" lands far from both.

Real embeddings use hundreds or thousands of numbers instead of two coordinates. The principle is the same.

:::say
An embedding turns meaning into numbers, so that "how close in meaning" becomes "how close as numbers".
:::

## How search uses them

1. **Prepare time.** Turn every chunk into an embedding and store it. This is your **vector index**. (A **vector** is just a list of numbers.)
2. **Question time.** Turn the question into an embedding the same way.
3. **Compare.** Find the stored embeddings closest to the question's. The usual measure is **cosine similarity**: it compares the direction two lists point in, and gives 1 for the same direction and near 0 for unrelated.
4. Return the chunks behind the closest embeddings.

This is called **vector search**, or **semantic search** ("semantic" means "about meaning").

## Try the mechanics with no installs

`code/rag/retrievers.py` has a toy version. It does not use a model. It breaks text into 3-letter pieces and compares how many pieces two texts share, using cosine similarity. That is not true meaning, so it will not link "customs" with "duties". But the compare-two-lists machinery is exactly what real vector search does, so you can read the whole mechanism in under 20 lines.

```python
def _grams(text, n=3):
    t = " ".join(tokenize(text))
    return Counter(t[i : i + n] for i in range(len(t) - n + 1))

def _cosine(a, b):
    dot = sum(a[g] * b[g] for g in a if g in b)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0

def vector_search(question, chunks, k=3):
    scored = sorted(((s, i) for i, s in enumerate(vector_scores(question, chunks))), reverse=True)
    return [chunks[i] for s, i in scored[:k] if s > 0]

def vector_scores(question, chunks):
    q = _grams(question)
    return [_cosine(q, _grams(c["text"])) for c in chunks]
```

On the 20 test questions in this repo, this toy already does well, partly because it forgives small spelling differences ("deliver" and "delivery" share pieces). That is a lesson too: some of what looks like "understanding" is just fuzzier matching.

## Using real embeddings

To get true meaning-matching, swap the toy for a real embedding model. Two common routes:

**A hosted embedding API.** You send text, you get numbers back. Easy, costs a little per call, and your text goes to that provider.

**A local model.** For example with the `sentence-transformers` library. Free per call, runs on your machine, and keeps text in-house.

A local version looks like this:

```python
# pip install sentence-transformers numpy
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")   # a small, popular model

chunk_vectors = model.encode([c["text"] for c in chunks], normalize_embeddings=True)

def semantic_search(question, chunks, k=3):
    q = model.encode([question], normalize_embeddings=True)[0]
    scores = chunk_vectors @ q          # cosine similarity, since vectors are normalized
    best = np.argsort(-scores)[:k]
    return [chunks[i] for i in best]
```

:::warn Note for this repo
This snippet is a standard pattern but it is not run as part of the repo's tests, because it needs a model download. The stage 1 to 3 scripts and the stage 4 service are the tested code. If you run this and hit a snag, fix it and send a note so we can update the lesson.
:::

Plug `semantic_search` into `stage3_eval.py` as one more row, and compare it with the others on your questions.

## Rules you must follow

- **Use the same model for chunks and questions.** Numbers from different models do not live on the same map.
- **If you change the model, re-embed everything.** Old and new vectors cannot be mixed.
- **Note the model name next to your index.** You will thank yourself later.
- **Tell the model which side it is reading.** Many embedding models are **asymmetric**: they encode a short question differently from a long passage, because the two look nothing alike. Cohere's API takes an `input_type` of `search_query` or `search_document` ([docs](https://docs.cohere.com/reference/embed)), and Voyage's takes `query` or `document` ([docs](https://docs.voyageai.com/docs/embeddings)). Some open models want a text prefix such as `query: ` instead. Read your model's card. If you skip this, search quietly gets worse and nothing errors.

## Where the vectors live

For a few thousand chunks, a plain array in memory is fine. Past that, use a **vector database**, which stores embeddings and finds close ones quickly. Options include pgvector (a Postgres add-on), Qdrant, Chroma, and others. Pick the one that fits what you already run. If your team already uses Postgres, pgvector is often the least new machinery.

Do not choose the database first. The retrieval quality comes from your chunks and your embeddings model, not the database brand.

When you get past a few hundred thousand chunks, memory and speed start to matter. [Vectors at scale](lesson:rag/vectors-at-scale) covers fast approximate search, smaller vectors, and switching models without downtime.

## Vectors have weak spots too

- **Exact things.** Order numbers, error codes, names and part numbers. A vector may treat "ERR-4021" and "ERR-4012" as nearly the same. Keyword search is better here.
- **Rare words.** A word the model barely saw may map poorly.
- **Negation.** "Refunds are allowed" and "Refunds are not allowed" can sit close together.

Because each method has blind spots the other covers, the next lesson mixes them.

:::check Why must questions and chunks use the same embedding model?
Each model draws its own map. Numbers from one model mean nothing on another model's map, so distances between them are meaningless.
:::

:::check You search for "ERR-4021" and get chunks about "ERR-4012". Which method would you add, and why?
Keyword search (such as BM25). It matches exact strings, so it separates the two codes.
:::
