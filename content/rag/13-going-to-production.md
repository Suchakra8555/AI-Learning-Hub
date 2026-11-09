---
title: Going to production
summary: Turn the script into a service other people can call, and learn how to watch it.
time: 25 min
stage: 7
---

A script runs when you press enter. A **service** runs all the time and answers whoever asks. Most of the difference between a demo and production is what surrounds the code.

## Stage 4: wrap it in a web service

`code/rag/stage4_service.py` puts the pipeline behind an HTTP endpoint. It needs two installs:

```bash
pip install fastapi uvicorn
cd code/rag
uvicorn stage4_service:app --port 8000
```

In another terminal:

```bash
curl -X POST localhost:8000/ask -H "content-type: application/json" -d '{"question":"How long do I have to return a tent?"}'
```

We ran this file in a test harness: the health check, a normal question, a nonsense question, and a too-short question all behaved as described below.

## What is in that file, and why

Go through the file top to bottom. Every part exists for a reason.

**Input limits.** The question must be 3 to 500 characters.

```python
class Ask(BaseModel):
    question: str = Field(min_length=3, max_length=500)
```

Without a limit, someone can send a 2 MB "question" and run up your bill. A too-short question gets a clear `422` error from the framework.

**Build once, not per request.** `CHUNKS = chunk_all(load_documents())` runs when the service starts. Rebuilding on every request would be wasteful.

**A request id.** Each request gets a short random id returned to the caller and written to the log. When a user says "it gave me a wrong answer", the id finds that exact request.

**A log line per request.** One line of JSON each, with the id, the time taken, which sources were used, and whether the model was called.

```json
{"request_id": "8e9a0f7b", "event": "answered", "ms": 2, "model_called": true, "sources": ["repairs.md", "returns.md"], "cache": 0}
```

JSON logs can be searched and counted by tools. Free-text logs cannot.

**Refuse early.** If search finds nothing, the service answers "I don't have that information" and never calls the model. That is faster and free.

:::warn An honest limit
That refusal only triggers when search returns zero chunks. The toy vector search returns *something* for almost any text, so the "nonsense question" test is the easy case. Real systems add a **score threshold**: if the best chunk scores below a line you tune on your eval set, refuse. Add it once you have real scores to look at.
:::

**Errors that do not leak.** On failure the user sees "The answer service had a problem. Please try again." The real error goes in the log. Never send stack traces to users.

**A health endpoint.** `GET /health` lets a platform ask "are you alive?" and restart you if not.

## What production still needs

Stage 4 is a good skeleton, not a finished product. Here is the rest, grouped.

### Run it reliably

- **Timeouts and retries** on every call to the model, with a limit on retries. Providers have bad minutes.
- **Rate limits** per user, so one person cannot use all your capacity.
- **More than one copy** of the service behind a load balancer, so one crash is not an outage.
- **Secrets** (API keys) from a secret store, not from files in the repo.
- **A fallback.** If the model is down, show search results alone, or a polite message.
- **Indexing as a queue of jobs.** Reading a 300-page PDF can take minutes. Don't do it inside a web request. Put an "index this file" job on a queue (Celery, RQ, NATS, SQS), and let workers pick jobs up. Give each job a state, such as `created → running → done | failed | stopped`, and a progress number the UI can show. A failed job can then be retried without starting the whole collection again.

### Replace the in-memory parts

- The cache lives in one process's memory. With several copies you need a shared cache, such as Redis.
- Chunks in a Python list will not scale. Move to a vector database ([lesson 6](lesson:rag/embeddings-and-vectors)).
- Rebuilding the index belongs in a separate scheduled job, not inside the web service ([lesson 12](lesson:rag/keeping-data-fresh)).

### Watch it

You cannot fix what you cannot see. Track these from the first week:

| What to watch | Why |
|---|---|
| Request count and error rate | Is it up and healthy? |
| Time per request (median and slowest 5%) | Are users waiting? |
| Cost per request, and per day | No surprise bills |
| How often it refused ("I don't have that") | Too high: coverage gap or search problem. Too low: may be guessing. |
| Thumbs up or down from users | The truest signal you have |
| Cache hit rate | Is the cache earning its keep? |

Two habits pay off enormously:

1. **A feedback button.** Let people mark an answer bad, and store the request id. Review those weekly and turn each into an eval question ([lesson 10](lesson:rag/when-answers-go-wrong)).
2. **A sample review.** Read 20 random real answers every week. Dashboards will not show you that answers turned subtly worse.

### Change it safely

- Run the eval set on every pull request.
- Roll out to a small group first.
- Keep the last working version and know how to switch back in a minute.
- Version the prompt, the chunk settings, the embedding model, and the index together. Write down which combination is live.

## A simple deployment shape

```text
 users ──► web service (2+ copies) ──► model provider
                │   ▲
                ▼   │
         vector database    cache (Redis)
                ▲
                │
        nightly index job ◄── document sources
```

You do not need all of it for a first launch. A small internal tool may run as one container with the in-memory index. Add boxes when a real problem demands them.

:::tip
The best first production step is not scale. It is **logging and a feedback button**. They show you what to fix next.
:::

:::check Why return a request id to the caller?
So a user report can be matched to the exact log line, retrieved chunks, and prompt behind it.
:::

:::check Why must a refusal threshold be tuned on real scores?
Search almost always returns something. Only by looking at the scores of good and bad matches on your eval questions can you pick a cut-off that refuses nonsense without refusing real questions.
:::
