---
title: Timeouts, retries, and saying goodbye
summary: Every wait on a voice platform needs a limit, every retry needs a schedule, and every deploy needs a way to let live calls finish. Here are the numbers our platform picked and where they break.
time: 20 min
---

A customer's webhook server goes down at 2 p.m. A thousand calls end in the next minute. Each one fails to deliver its `call.ended` event. Thirty seconds later your dispatcher retries all thousand at once, just as their server comes back, and knocks it over again. Then you ship a fix, the deploy sends SIGTERM to the media server, and forty people hear their call drop mid-sentence. It comes down to three questions: how long you wait, when you try again, and how you leave.

## The timeout budget

A **timeout** is the longest you will wait for something before you give up and do something else. Every number below is a choice. Here is what our platform chose, and why.

| Where | Timeout | Why this value |
|---|---|---|
| Media bridge, waiting for the carrier's `start` message | 10 s | A socket that never says which call it is should not hold a slot. |
| Media bridge, no messages at all | 15 s | Carriers send audio constantly, silence included, so 15 s of nothing means the socket is dead, not quiet. |
| One-time stream ticket in Redis | 60 s inbound, 180 s outbound | Outbound calls have to ring before the stream opens. |
| Carrier API calls (dial, hang up) | 15 s | The carrier's REST API is outside your control. |
| API gateway to a service | 90 s, 5 s to connect | Buying a phone number makes several carrier calls in a row. |
| Customer webhook POST | 10 s | A hung customer server must not tie up your worker. |
| Live calls on shutdown | 300 s | Long enough for most calls to end on their own. |

Read the table as a budget. If the gateway waits 90 s for a service that waits 15 s for a carrier, a slow carrier costs one request 15 s, not 90. If those were reversed, the gateway would give up while the service was still working, and the user would retry a number purchase that might already have gone through.

## Retries: a fixed schedule

The **webhook dispatcher** is the service that sends signed HTTP callbacks to customers when a call starts, ends, or produces a transcript. When a POST fails, it saves the row as failed with a next-retry time. A background loop checks for due rows about every 15 s.

The schedule is fixed: retry after 30 s, 2 min, 10 min, 30 min, then 2 h. After the fifth failure the row is marked exhausted and nothing more happens. A fixed schedule is easy to reason about. Its weakness is that every failure that started in the same second retries in the same second too.

That is a **thundering herd**: many clients that failed together come back together, and the burst knocks the recovering server over again. The usual fix is **exponential backoff with jitter**. The wait grows each attempt, and each client picks a random point inside that window. AWS calls the version below "full jitter" and recommends jittered backoff as a standard approach for remote clients ([AWS Architecture Blog](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)).

`code/voice-prod/retry_backoff.py` compares the two when 1,000 webhooks fail at once:

```python
FIXED = [30, 120, 600, 1800, 7200]          # seconds: 30 s, 2 m, 10 m, 30 m, 2 h

def jittered(attempt, base=30, cap=7200, rnd=random.Random(1)):
    return rnd.uniform(0, min(cap, base * 4 ** attempt))   # "full jitter"
```

```text
first retry of 1,000 failed webhooks:
  fixed 30 s   -> 1000 requests in the busiest second
  full jitter  ->   45 requests in the busiest second
  give-up time with the fixed schedule: 162 min after the first failure
```

Same total work, spread out: the busiest second drops from 1,000 requests to 45.

## Double delivery: retries without a lock

The first delivery is safe. Events come off a Redis Stream consumer group, which hands each event to one consumer. The retry loop is a different story. It runs a plain `SELECT` for failed rows whose retry time has passed, then sends each one. Nothing marks a row as taken. With one replica that works. With two, both loops read the same due rows in the same 15 s window and both POST them. The customer gets every retried event twice.

Postgres has a clause for exactly this. `FOR UPDATE` locks the rows a `SELECT` returns, and `SKIP LOCKED` makes other transactions skip rows that are already locked instead of waiting. The Postgres docs say this "can be used to avoid lock contention with multiple consumers accessing a queue-like table" ([SELECT, the locking clause](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)). A fresh sketch:

```sql
SELECT id FROM deliveries
WHERE status = 'failed' AND next_retry_at <= now()
ORDER BY next_retry_at
LIMIT 50
FOR UPDATE SKIP LOCKED;
-- send each one, update its status, then COMMIT to release the locks
```

Each replica gets its own batch. Customers should still treat webhooks as **at-least-once**, meaning the same event can arrive more than once, and use the event id to ignore repeats. A crash between the POST and the commit will always send one event twice.

:::warn Gotcha from the platform
The dispatcher has no row locking. It runs as one replica today, so the problem is latent. The day someone scales it to two for availability, every retried webhook goes out twice. Nothing in the code or the deploy config stops that.
:::

## Saying goodbye: graceful drain

A deploy stops the old container by sending **SIGTERM**, a polite "please exit" signal. If the process is still running after a grace period, the platform sends **SIGKILL**, which cannot be caught. According to the platform's own code notes, uvicorn's normal shutdown closes every open WebSocket right away with close code 1012, and every one of those sockets is a phone call.

So the media bridge **drains**: on the first SIGTERM it flips one flag and then waits.

- `/health` returns 503, so the load balancer stops sending it new calls.
- A new media stream is closed with code 1013, "Try Again Later". Codes 1012 and 1013 are registered in the [IANA WebSocket close code registry](https://www.iana.org/assignments/websocket/websocket.xhtml). They are not in RFC 6455 itself.
- Live calls carry on until they end or 300 s pass. Only then does the normal shutdown run.
- A second SIGTERM skips the wait.

For this to work, the server has to receive the signal. The container entrypoint loads secrets and then uses `exec` to replace itself with the server, so the server runs as PID 1 and gets SIGTERM directly ([os.execvp](https://docs.python.org/3/library/os.html#os.execvp)).

<figure>
<svg viewBox="0 0 920 250" role="img" aria-labelledby="t-drain d-drain">
  <title id="t-drain">What happens to live calls during a deploy</title>
  <desc id="d-drain">Five steps left to right: SIGTERM arrives, the server stops accepting new calls with health 503 and close code 1013, live calls finish one by one, the drain deadline passes, and SIGKILL cuts whatever is left. Below, two bars compare Fargate's 120 second stop limit with the bridge's 300 second drain.</desc>
  <defs><marker id="ah-drain" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="15" text-anchor="middle">
    <rect class="box" x="16" y="30" width="160" height="64" rx="10"/><text x="96" y="58">SIGTERM</text><text x="96" y="80" font-size="13" class="small">from the deploy</text>
    <rect class="box" x="196" y="30" width="160" height="64" rx="10"/><text x="276" y="58">Stop accepting</text><text x="276" y="80" font-size="13" class="small">503 + close 1013</text>
    <rect class="box" x="376" y="30" width="160" height="64" rx="10"/><text x="456" y="58">Calls finish</text><text x="456" y="80" font-size="13" class="small">one by one</text>
    <rect class="box" x="556" y="30" width="160" height="64" rx="10"/><text x="636" y="58">Deadline</text><text x="636" y="80" font-size="13" class="small">drain timeout hit</text>
    <rect class="box hot" x="736" y="30" width="160" height="64" rx="10"/><text x="816" y="58">SIGKILL</text><text x="816" y="80" font-size="13" class="small">cuts what is left</text>
  </g>
  <path class="arrow" d="M176 62 H192" marker-end="url(#ah-drain)"/>
  <path class="arrow" d="M356 62 H372" marker-end="url(#ah-drain)"/>
  <path class="arrow" d="M536 62 H552" marker-end="url(#ah-drain)"/>
  <path class="arrow" d="M716 62 H732" marker-end="url(#ah-drain)"/>
  <text x="16" y="140" font-size="14" font-weight="700">Time after SIGTERM</text>
  <path class="arrow" d="M16 160 H260" marker-end="url(#ah-drain)"/>
  <text x="270" y="165" font-size="13" class="small">Fargate: SIGKILL by 120 s at the latest</text>
  <path class="arrow" d="M16 200 H620" marker-end="url(#ah-drain)"/>
  <text x="630" y="205" font-size="13" class="small">Bridge drain: up to 300 s</text>
</svg>
<figcaption>A graceful drain. The bridge wants up to 300 s, but on Fargate the platform kills the task at 120 s unless something else holds traffic off first.</figcaption>
</figure>

Run the second half of the script to see what the grace period buys. It gives 40 live calls a random 0 to 600 s left to run:

```text
SIGTERM with 40 live calls (health check now returns 503, new streams get close code 1013):
  grace  30 s ->  3 calls end normally, 37 cut off
  grace 120 s ->  8 calls end normally, 32 cut off
  grace 300 s -> 18 calls end normally, 22 cut off
```

## Fargate's 120 seconds

On ECS, `stopTimeout` is how long a container gets between SIGTERM and SIGKILL. The default is 30 s and the maximum is 120 s ([ECS task definition parameters](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html)). A support call can easily run 5 minutes.

The platform's deploy notes handle the media bridge with the load balancer instead. A target being removed enters a **deregistration delay**, during which the load balancer sends it no new requests but lets existing connections finish ([ALB docs](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html#deregistration-delay)). The bridge's target group sets it to 330 s, and ECS sends SIGTERM only after that. Locally, docker-compose sets `stop_grace_period: 330s` for the same reason: it must be longer than the 300 s drain. The **agent worker** has no load balancer in front of it. It gets 120 s and then it dies, along with any call older than that.

:::warn Gotcha from the platform
The deploy guide says it plainly: a deploy can cut agent calls longer than about two minutes. The suggested workarounds are to deploy off-peak, or to run the worker on EC2-backed ECS capacity where the stop timeout can be raised. Neither is automated. A deploy at peak hours will hang up on people.
:::

:::try
In `retry_backoff.py`, change the grace values in the loop from `(30, 120, 300)` to `(120, 330, 600)`. Before you run it, predict how many of the 40 calls survive at 600 s. (Hint: look at the range of `rnd.uniform`.) Then change `base=30` to `base=5` in `jittered` and predict whether the busiest second gets better or worse.
:::

:::note What we did not test
We read the dispatcher, the drain code, and the deploy guide. We did not run two dispatcher replicas, deploy to Fargate, or watch a real call survive a drain. The ECS and ALB limits come from AWS docs, not from our own measurements. The script uses no real signals or sockets.
:::

:::say
Give every wait a limit, spread every retry out, lock the rows you are about to retry, and on SIGTERM stop taking calls before you stop serving them.
:::

:::check Why does `FOR UPDATE SKIP LOCKED` fix double delivery, and why should customers still dedupe?
Each replica locks the rows it picked, and the other replica skips them, so no row is sent by two loops at once. A crash after the POST but before the commit still leaves the row due, so it gets sent again. Delivery stays at-least-once.
:::

:::check The bridge drains for 300 s but Fargate kills at 120 s. Why are bridge calls still safe on Fargate, and agent calls are not?
The load balancer holds the bridge in deregistration for 330 s before ECS sends SIGTERM, so calls drain before the 120 s clock starts. The agent worker has no load balancer, so its 120 s starts right away.
:::

Next: [Measuring latency on real calls](lesson:voice-prod/measuring-latency-on-real-calls)
