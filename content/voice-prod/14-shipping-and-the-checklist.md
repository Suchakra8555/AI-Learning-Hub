---
title: Shipping, and the voice engineer's checklist
summary: How our platform's code reached production, what that pipeline skipped, what a safer one looks like, and a checklist that pulls the whole track together.
time: 25 min
---

You merge a fix. A few minutes later the pipeline is green. Did the fix ship? On our platform the honest answer was "the files are on the server". Nothing was built, tested, migrated, or restarted. A green pipeline meant a zip file had moved.

## What the pipeline did

The deploy job runs on pushes to one branch. In order:

1. It gets short-lived AWS credentials by trading GitLab's OIDC token for a role. That part is good: no long-lived keys sit in CI variables.
2. It zips the whole repo, minus `.git`.
3. It copies the zip to S3.
4. It uses AWS Systems Manager to run a shell command on the EC2 instance that downloads the zip and unzips it over the app directory.

There is no build step, so no new image exists. There is no test step, so the test suites and the provider parity script never run in CI. There is no migration step. There is no `docker compose up` or restart, so the running containers keep serving the old code until someone restarts them by hand. An older pipeline that rsynced the tree and ran `docker compose up --build` sits commented out in the CI file. An ECS target is planned.

## Three quieter problems

**`:latest` tags.** A **tag** is a name pointing at one image version. `latest` is only the default tag name and says nothing about which version it points to ([docker image tag](https://docs.docker.com/reference/cli/docker/image/tag/)). The root compose file pulls LiveKit server, SIP, egress, ingress, and MinIO as `:latest`. Two machines built a week apart can run different LiveKit versions from the same commit. The deploy guide says livekit-server is pinned on the EC2 stack, and also warns that egress, SIP and ingress still default to `:latest` there.

**Migrations that never ran.** Each service has Alembic migrations. They were written by hand and, per the platform's own deploy guide, have never run against a live Postgres. The first real `alembic upgrade head` will be the test.

**Docs drifting from code.** The LiveKit egress webhook was fixed in the cloud config and not in the local one, so recordings behave differently on a laptop. Notes and guides describe things the code no longer does. Every wrong doc costs the next engineer an afternoon.

:::warn Gotcha from the platform
Put the three together. A push unzips new code next to containers still running the old code. The next manual restart may pull a newer `:latest` LiveKit than the one you tested, and the first time anyone runs the hand-written migrations is against production data. The pipeline reports success at every step, because none of those steps are in it.
:::

## A safer pipeline

The fix is to add the steps the current one skips, in this order:

1. **Check.** Lint, unit tests for every service, and the provider parity script. Fail the pipeline on any error.
2. **Build once.** Build each image and tag it with the commit SHA, never `latest`. Pin every third-party image to a version you have tested.
3. **Migrate.** Run `alembic upgrade head` as a one-off task against staging first, then production. Migrations must work with both old and new code, because for a while both run.
4. **Deploy with drain.** Roll services one at a time and let calls drain (see [timeouts, retries, and goodbyes](lesson:voice-prod/timeouts-retries-and-goodbyes)).
5. **Smoke a real call.** Run the checklist from [testing what you can't call](lesson:voice-prod/testing-what-you-cant-call). If it fails, roll back to the previous SHA.

## The voice engineer's production checklist

Use this before you call a voice platform production-ready. Each item links to the lesson that explains it.

### Audio and transport

- [ ] Codec conversion happens once, at the edge, you know who resamples, and frames are re-chunked to the size each carrier expects. ([phone audio is different](lesson:voice-prod/phone-audio-is-different))
- [ ] You know which door each call uses, SIP or WebSocket, and what network each one needs. ([two doors](lesson:voice-prod/two-doors-sip-and-websocket))
- [ ] Each carrier is one adapter behind one interface, including its quirks, like a missing `stop`. ([one interface, many carriers](lesson:voice-prod/one-interface-many-carriers))
- [ ] Barge-in clears your buffer and the carrier's buffer. ([one interface, many carriers](lesson:voice-prod/one-interface-many-carriers))

### WebRTC and LiveKit

- [ ] Browser calls have a reachable TURN server when the media server has only a private IP. ([WebRTC from the wire up](lesson:livekit/webrtc-from-the-wire-up))
- [ ] You can explain why an SFU, and what it costs per participant. ([mesh, MCU, SFU](lesson:livekit/mesh-mcu-sfu))
- [ ] You read the LiveKit track before building on LiveKit. ([what LiveKit is](lesson:livekit/what-livekit-is))
- [ ] LiveKit's `webhook:` block is set in every config, local and cloud. ([webhooks and events](lesson:livekit/webhooks-and-events))
- [ ] Workers register with an agent name and are dispatched explicitly, not to every room. ([agent server and dispatch](lesson:livekit/agent-server-and-dispatch))
- [ ] The agent waits for, or retries, the Call row instead of racing the webhook. ([how the platform rides LiveKit](lesson:voice-prod/how-the-platform-rides-livekit))

### Security

- [ ] Every media socket proves who it is with a one-time, short-lived ticket. ([who is on this socket](lesson:voice-prod/who-is-on-this-socket))
- [ ] Shared keys are compared in constant time, never with `!=`. ([who is on this socket](lesson:voice-prod/who-is-on-this-socket))
- [ ] One service decrypts customer credentials, and every read is logged. ([secrets, recordings, and privacy](lesson:voice-prod/secrets-recordings-and-privacy))
- [ ] Production refuses to boot on dev defaults. ([secrets, recordings, and privacy](lesson:voice-prod/secrets-recordings-and-privacy))

### Async and concurrency

- [ ] No sync network call runs on the agent's event loop. ([never block the audio loop](lesson:voice-prod/never-block-the-audio-loop))
- [ ] Per-call settings, like VAD tuning, are reset on every job. ([tuning turns as pure functions](lesson:voice-prod/tuning-turns-as-pure-functions))

### Events

- [ ] Stalled messages are reclaimed, and poison messages go to a dead-letter queue. ([events that don't lie](lesson:voice-prod/events-that-dont-lie))
- [ ] Streams are capped, and new consumer groups don't replay all history. ([events that don't lie](lesson:voice-prod/events-that-dont-lie))
- [ ] Handlers are idempotent, because delivery is at-least-once. ([events that don't lie](lesson:voice-prod/events-that-dont-lie))

### Reliability and deploys

- [ ] Every wait has a timeout, and the budget nests: outer waits are longer than inner ones. ([timeouts, retries, and goodbyes](lesson:voice-prod/timeouts-retries-and-goodbyes))
- [ ] Retries use jittered backoff, and retried rows are locked with `SKIP LOCKED`. ([timeouts, retries, and goodbyes](lesson:voice-prod/timeouts-retries-and-goodbyes))
- [ ] SIGTERM starts a drain, and the platform's kill timer is longer than your longest normal call. ([timeouts, retries, and goodbyes](lesson:voice-prod/timeouts-retries-and-goodbyes))
- [ ] CI builds, tests, migrates, restarts, and pins image versions. (This lesson.)

### Latency and observability

- [ ] You report p50, p95 and p99 per turn, split by turn strategy, and you measure time to first sentence as well as time to first token. ([measuring latency on real calls](lesson:voice-prod/measuring-latency-on-real-calls))
- [ ] Cost per call is computed from real usage and current prices. ([measuring latency on real calls](lesson:voice-prod/measuring-latency-on-real-calls))

### Privacy

- [ ] Recording fails closed: no config, no recording. And the consent flag is enforced. ([secrets, recordings, and privacy](lesson:voice-prod/secrets-recordings-and-privacy))
- [ ] Transcripts follow the same retention clock as audio. ([secrets, recordings, and privacy](lesson:voice-prod/secrets-recordings-and-privacy))
- [ ] Log redaction is recursive, and secrets are kept out of log calls in the first place. ([secrets, recordings, and privacy](lesson:voice-prod/secrets-recordings-and-privacy))

### Testing

- [ ] Every service has tests, starting with the ones that hold secrets or send money. ([testing what you can't call](lesson:voice-prod/testing-what-you-cant-call))
- [ ] A contract check runs in CI whenever a provider plugin version moves. ([testing what you can't call](lesson:voice-prod/testing-what-you-cant-call))
- [ ] A person places an inbound and an outbound call after every media deploy. ([testing what you can't call](lesson:voice-prod/testing-what-you-cant-call))

:::try
Capstone exercises. Each one combines two scripts in `code/voice-prod/`, except `jitter_buffer.py`, which now lives in `code/livekit/`.

1. Run `blocking_loop.py` and note how long the audio pump stalls. In `latency_report.py`, add that stall to the LLM stage on 10% of turns. Predict p50 and p95 before you run it.
2. In `consumer_group.py`, give failed events a retry delay taken from `jittered()` in `retry_backoff.py`. How many attempts should an event get before it goes to the dead-letter queue, and how long is that in minutes?
3. `stream_ticket.py` issues tickets that live 60 s inbound and 180 s outbound. In `retry_backoff.py`, a draining server refuses new streams with 1013. What happens to an outbound call whose ticket was issued 10 s before SIGTERM? Write down what the carrier should do next.
4. Use `jitter_buffer.py` to pick a buffer depth with no gaps. Add that depth to `tts_ttfb_ms` in `latency_report.py`. What share of your p50 is now buffering?
5. In `barge_in.py`, change the loudness threshold, then work out how many 20 ms µ-law frames from `mulaw.py` fit in the 0.6 s barge-in window.
:::

:::note What we did not test
We read the CI file, both compose files, and the deploy guide. We did not run the pipeline, deploy anything, or run the migrations. The checklist is our judgment from this track, not a standard. The capstone exercises are new. We did not run them.
:::

:::say
A deploy is a build, a test run, a migration, a drain, a restart and a real call, and anything less is moving files around.
:::

:::check The pipeline is green, but a real call still shows the old behavior. What is the first thing to check on this platform?
Whether the containers were restarted or rebuilt. The pipeline only unzips files on the server, so the running processes still have the old code loaded.
:::

:::check Why tag images with the commit SHA instead of `latest`?
A SHA names one exact build, so every machine runs the same thing and a rollback is just the previous SHA. `latest` moves, so two deploys of the same commit can run different code.
:::
