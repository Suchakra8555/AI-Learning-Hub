---
title: Keeping the data fresh
summary: Documents change. Your index has to change with them, or the bot will confidently quote last year's policy.
time: 12 min
---

Your index is a copy of your documents at the moment you built it. The day a document changes, the copy is out of date. For a support bot that is a real problem: a customer is told the old return window and holds you to it.

## Decide how fresh is fresh enough

Different content has different needs.

| Content | How often it changes | A reasonable refresh |
|---|---|---|
| Policies | A few times a year | Rebuild when the file changes |
| Product docs | Every release | On every merge to the docs |
| Tickets and chat | Constantly | Continuous, or every few minutes |
| Prices and stock | Minutes | Do not put in the index. Call the live system. |

That last row matters. **Fast-changing facts do not belong in a search index.** Let the bot call a live lookup for prices and stock. The index is for text that changes slowly.

## Three ways to refresh

**1. Rebuild everything on a schedule.** Re-read, re-chunk, and re-embed all documents, say every night. Simple and safe. Fine up to a modest size. Cost grows with the amount of data.

**2. Update only what changed.** Keep a fingerprint (a **hash**) of each document. When a hash changes, redo that document and nothing else.

```python
import hashlib

def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def changed_documents(docs, saved_hashes):
    """Return docs whose text differs from what we indexed last time."""
    return [d for d in docs if saved_hashes.get(d["source"]) != fingerprint(d["text"])]
```

**3. React to events.** The wiki or file store tells you when something changes, and you update right away. Fastest, and the most work to set up.

Start with 1. Move to 2 when the nightly rebuild takes too long or costs too much.

## Handle deletions

People forget this one. If a document is deleted but its chunks stay in the index, the bot keeps quoting it. Whenever you refresh, also **remove chunks whose source no longer exists.**

When a document is *changed*, delete its old chunks first, then add the new ones. Otherwise you get old and new text side by side, and the bot may quote either.

## Tag every chunk with where it came from and when

You already saved this in [lesson 4](lesson:rag/reading-documents). Here is the payoff:

```python
{"source": "returns.md", "doc_version": "2025-03-01", "indexed_at": "2025-03-02T02:00:00Z", "text": "..."}
```

With these you can:

- tell users "This is from the policy updated March 1",
- find every chunk of a document to replace it,
- debug an old answer: which version of the index produced it?

## Clear the cache when you refresh

Remember the cache from lesson 11? An answer cached last week may quote the old policy. Clear it, or give cache entries a short lifetime, whenever the index changes.

```python
answer_for.cache_clear()   # in stage 4, after a refresh
```

## Roll out index changes safely

Treat a new index like a new release:

1. Build the new index **beside** the old one, not over it.
2. Run your eval set against the new one.
3. If the numbers hold, switch traffic over.
4. Keep the old index for a day or two in case you need to switch back.

This is also how you change the embedding model or chunk size safely.

A new embedding model often makes vectors of a different length, say 1024 numbers instead of 768. One neat trick: name the vector field after its length (`vec_768`, `vec_1024`). Old chunks keep the old field, re-embedded chunks get the new one, and search reads whichever field matches the model in use. The index never mixes vectors from two models in one field. [RAGFlow](lesson:ragflow/ingestion) does exactly this.

:::warn
Never re-embed "in place" while users are searching. For a while the index will hold a mix of old and new vectors that do not match, and search quality drops in confusing ways.
:::

:::try
In `code/rag/data`, edit `returns.md` so the tent return window is 90 days. Run `stage1_poc.py` again. Why does it answer correctly right away here, when a real system would not? (Hint: look at when the script reads the files.)
:::

:::check A document was deleted from the wiki last week. The bot still quotes it. What was missed?
Deletion handling. Chunks from removed sources must be removed from the index during refresh.
:::

:::check Where should live stock levels be stored, in the index or somewhere else?
Somewhere else. They change too fast for an index. Let the bot call a live lookup at question time.
:::
