---
title: Retrieval that works: mix, rerank, rewrite
summary: Combine keyword and vector search, reorder the results, and fix vague questions before searching.
time: 18 min
stage: 3
---

Retrieval is the step that decides if your system is good. If the right chunk is in the prompt, most models will answer well. If it is not, nothing downstream can save you.

This lesson gives you four tools, in the order to try them.

## Tool 1: keyword search done properly (BM25)

Stage 1 counted shared words. **BM25** is the classic upgrade, used inside many search engines. It adds two common-sense ideas:

- A **rare word counts more** than a common one. Matching "waterproofing" tells you much more than matching "item".
- A **long chunk should not win just for being long**, since long texts contain more words by chance.

It is in `code/rag/retrievers.py`, no libraries: `bm25_scores` gives every chunk a score in about 20 lines, and `bm25_search` sorts them and keeps the top k. Notice the two ideas in the code:

```python
idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))     # rare word -> bigger number
s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(d) / avg_len))   # long chunk -> smaller number
```

You do not need to memorize the formula. Know what it is for.

## Tool 2: vector search

From the last lesson. It finds matches by meaning and forgives different wording.

## Tool 3: hybrid search, which mixes both

Keyword search is strong on exact terms. Vector search is strong on paraphrases. Each misses what the other catches. **Hybrid search** runs both and merges the lists.

A simple, widely used way to merge is **reciprocal rank fusion**. Each method gives a ranked list. A chunk earns points based on its position in each list, higher position, more points. Chunks that both methods like float to the top.

```python
def hybrid_search(question, chunks, k=3, pool=8):
    ranked_lists = [bm25_search(question, chunks, pool), vector_search(question, chunks, pool)]
    score = Counter()
    by_text = {}
    for ranking in ranked_lists:
        for rank, c in enumerate(ranking):
            score[c["text"]] += 1 / (60 + rank + 1)
            by_text[c["text"]] = c
    return [by_text[t] for t, s in score.most_common(k)]
```

The `60` is a conventional constant that keeps one first place from dominating. Leave it alone at first. The method comes from a 2009 paper by Cormack, Clarke and Buettcher ([paper](https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/)).

### The other way to merge: a weighted sum

Many products merge by score instead of by position: `final = w * vector_score + (1 - w) * keyword_score`. It has a dial, `w`, which is handy. It also has a trap. The two scores live on different scales. Run `python fusion_compare.py` and look at the first lines:

```text
Score ranges for "How long do I have to return a tent?":
  bm25   0.00 .. 3.39
  vector 0.03 .. 0.28
  with w=0.7 on raw scores, vector's share of the top score is only 17% on average
```

You set the vector weight to 70%, and vector search ends up with about a sixth of the say. The usual fix is to **normalize** first: squash each list's scores to 0..1 (best is 1, worst is 0), then mix. RRF never has this problem because it ignores scores and uses only positions.

```text
rrf                    top-1  75%   top-3 100%   MRR 0.85
weighted raw w=0.3     top-1  75%   top-3 100%   MRR 0.85
weighted raw w=0.7     top-1  75%   top-3 100%   MRR 0.85
weighted scaled w=0.3  top-1  75%   top-3 100%   MRR 0.86
weighted scaled w=0.7  top-1  75%   top-3  95%   MRR 0.85
```

On our 20 easy questions they all land in the same place, so this table proves nothing about which is better. We would start with RRF, since it has nothing to tune. Move to a normalized weighted sum only if your test set shows that a dial helps. [RAGFlow](lesson:ragflow/search-and-answers) is a real product that takes the weighted-sum route.

:::note Other search families
Two more kinds of search sit between keywords and vectors. **Learned sparse** models such as SPLADE use a model to pick which words, including related words not in the text, a chunk should match on, and then store them in a keyword-style index ([paper](https://arxiv.org/abs/2107.05720)). **Late interaction** models such as ColBERT keep one small vector per word and compare question words against chunk words one by one ([paper](https://arxiv.org/abs/2004.12832)). Both often beat a single vector per chunk, and both cost more to store. Try them after hybrid search and a reranker.
:::

## See the difference

Run the comparison from the repo:

```bash
cd code/rag
python stage3_eval.py
```

On the 20 questions in this repo it printed this when we ran it:

```text
stage 1 (overlap)      top-1  70%   top-3  90%   MRR 0.78
overlap + new chunks   top-1  60%   top-3  95%   MRR 0.76
bm25                   top-1  75%   top-3  95%   MRR 0.83
vector (toy)           top-1  85%   top-3  95%   MRR 0.90
hybrid                 top-1  75%   top-3 100%   MRR 0.85
```

Read it carefully, and be honest about what it does and does not say:

- Hybrid is the only row that finds the right chunk in the top 3 for every question. That is the pattern to expect: mixing methods rescues the odd miss.
- With only 20 questions on 4 tiny files, a 5 point gap is one question. Do not treat small gaps as proof. The point of the table is the *habit*: change one thing, re-run, compare.
- "Overlap + new chunks" scored slightly lower than stage 1 on top-1. New chunking is not magic. It helped some questions and hurt others. This is exactly why you measure.

:::note What the columns mean
**top-1**: the right chunk was ranked first. **top-3**: it was somewhere in the top three. **MRR** (mean reciprocal rank): a single score that rewards ranking it higher; 1.0 means always first.
:::

## Tool 4: rerank

Search is fast but rough. A **reranker** is a slower, sharper model that takes your top 20 or so candidates and reorders them by reading each one together with the question. You then keep the best 3 to 5.

The pattern is: search wide and cheap, then sort narrow and careful.

```text
question -> hybrid search (top 20) -> reranker -> best 4 -> prompt
```

Rerankers are available as hosted APIs and as open models you can run yourself. Add one when your evaluation shows the right chunk is often *in the top 20 but not in the top 4*. If it is not even in the top 20, a reranker cannot help, and the problem is earlier (chunks or search).

## Tool 5: fix the question first

Real questions are messy.

- "And what about for tents?" depends on the message before it.
- "refund?" is too short to search on.
- "Why was I charged twice and how long until I get it back" asks two things at once.

**Query rewriting** asks a model to turn the raw message into a clean, standalone search query before searching. For the chat example, with history in view, it might produce "return window for tents".

```python
REWRITE_PROMPT = """Rewrite the user's last message as one standalone search query.
Use the conversation for missing details. Output only the query.

Conversation:
{history}

Last message: {message}
Search query:"""
```

You can also split a two-part question into two searches. Both cost an extra model call, so add them when your failures show vague or follow-up questions, not by default.

## A sensible order to try things

1. Fix chunking and clean text (cheapest, biggest effect).
2. Add BM25 if you only have vectors, or vectors if you only have keywords.
3. Combine them with fusion.
4. Add metadata filters (only the current policy, only the user's region).
5. Add reranking.
6. Add query rewriting.

At each step, run the evaluation. Keep the change only if the numbers move.

:::warn
Resist adding every technique because a blog post listed it. Each piece adds cost, delay, and something to maintain. Add one when your test results show the problem it solves.
:::

:::check Give one question where keyword search wins and one where vector search wins.
Keyword wins on exact codes or names, like "ERR-4021". Vector wins on different wording, like "customs fees" for a document that says "import duties".
:::

:::check The right chunk is ranked 14th out of 20 candidates. Which tool helps?
A reranker. It reorders the candidates so the right one reaches the top few that go into the prompt.
:::
