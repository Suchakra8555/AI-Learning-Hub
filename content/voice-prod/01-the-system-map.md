---
title: The system map: nine services and three kinds of traffic
summary: A production voice platform is more than an agent. Learn the nine services, why only one of them faces the internet, and the three different ways data moves between them.
time: 20 min
---

The voice track showed one agent talking to one caller. A paid product needs more around that agent. Someone has to log in. Someone stores API keys and phone numbers. Someone sends the customer a webhook when the call ends, and someone keeps the recording. When a call goes wrong at 2 a.m., you need to know which part to look at.

This track follows a production voice platform we built. It is nine small services. Learn the map once and every later lesson will point to a place on it.

<figure>
<svg viewBox="0 0 1060 560" role="img" aria-labelledby="t-map d-map">
  <title id="t-map">The platform's nine services and three kinds of traffic</title>
  <desc id="d-map">Apps reach the API gateway, which fans out over sync HTTP to seven services, each with its own Postgres database. Phone carriers reach the media bridge over a WebSocket, and the bridge carries audio into a LiveKit room where the agent worker also sits. Call orchestration and the agent worker publish events to Redis Streams. The webhook dispatcher and the recording service consume them. LiveKit records to S3 or MinIO.</desc>
  <defs><marker id="ah-map" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="20" y="40" width="150" height="50" rx="10"/><text x="95" y="70">Apps, console</text>
    <rect class="box" x="900" y="40" width="140" height="50" rx="10"/><text x="970" y="70">Phone carriers</text>
    <rect class="box hot" x="20" y="130" width="150" height="56" rx="10"/><text x="95" y="154">API gateway</text><text x="95" y="174" font-size="11" class="small">public door, no DB</text>
    <rect class="box hot" x="900" y="130" width="140" height="56" rx="10"/><text x="970" y="154">Media bridge</text><text x="970" y="174" font-size="11" class="small">no DB, Redis only</text>
  </g>
  <text x="200" y="205" font-size="13" font-weight="700">Services. Each one owns its own Postgres database.</text>
  <g font-size="13" text-anchor="middle">
    <rect class="box" x="20" y="240" width="114" height="70" rx="10"/><text x="77" y="272">Auth</text>
    <rect class="box" x="144" y="240" width="114" height="70" rx="10"/><text x="201" y="262">Assistant</text><text x="201" y="279">config</text>
    <rect class="box" x="268" y="240" width="114" height="70" rx="10"/><text x="325" y="272">Credentials</text>
    <rect class="box" x="392" y="240" width="114" height="70" rx="10"/><text x="449" y="262">Telephony</text><text x="449" y="279">provisioning</text>
    <rect class="box" x="516" y="240" width="114" height="70" rx="10"/><text x="573" y="262">Call</text><text x="573" y="279">orchestration</text>
    <rect class="box" x="640" y="240" width="114" height="70" rx="10"/><text x="697" y="262">Webhook</text><text x="697" y="279">dispatcher</text>
    <rect class="box" x="764" y="240" width="114" height="70" rx="10"/><text x="821" y="262">Recording,</text><text x="821" y="279">transcripts</text>
  </g>
  <g font-size="11" text-anchor="middle" class="small">
    <text x="77" y="300" class="small">Postgres</text><text x="201" y="300" class="small">Postgres</text><text x="325" y="300" class="small">Postgres</text><text x="449" y="300" class="small">Postgres</text><text x="573" y="300" class="small">Postgres</text><text x="697" y="300" class="small">Postgres</text><text x="821" y="300" class="small">Postgres</text>
  </g>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="380" y="400" width="200" height="60" rx="10"/><text x="480" y="426">Redis Streams</text><text x="480" y="446" font-size="11" class="small">one stream of call events</text>
    <rect class="box" x="660" y="400" width="160" height="60" rx="10"/><text x="740" y="426">Agent worker</text><text x="740" y="446" font-size="11" class="small">call orch. image</text>
    <rect class="box hot" x="900" y="400" width="140" height="60" rx="10"/><text x="970" y="426">LiveKit</text><text x="970" y="446" font-size="11" class="small">rooms, SIP, egress</text>
    <rect class="box" x="900" y="500" width="140" height="44" rx="10"/><text x="970" y="527">S3 / MinIO</text>
  </g>
  <path class="arrow" d="M95 90 V126" marker-end="url(#ah-map)"/>
  <path class="arrow" d="M95 186 V215 H821"/>
  <path class="arrow" d="M940 186 V215 H821"/>
  <path class="arrow" d="M77 215 V236" marker-end="url(#ah-map)"/>
  <path class="arrow" d="M201 215 V236" marker-end="url(#ah-map)"/>
  <path class="arrow" d="M325 215 V236" marker-end="url(#ah-map)"/>
  <path class="arrow" d="M449 215 V236" marker-end="url(#ah-map)"/>
  <path class="arrow" d="M573 215 V236" marker-end="url(#ah-map)"/>
  <path class="arrow" d="M697 215 V236" marker-end="url(#ah-map)"/>
  <path class="arrow" d="M821 215 V236" marker-end="url(#ah-map)"/>
  <path class="arrow" d="M900 408 L622 314" marker-end="url(#ah-map)"/>
  <path class="arrow" stroke-dasharray="6 5" d="M560 310 L502 396" marker-end="url(#ah-map)"/>
  <path class="arrow" stroke-dasharray="6 5" d="M660 445 H584" marker-end="url(#ah-map)"/>
  <path class="arrow" stroke-dasharray="6 5" d="M580 410 L690 314" marker-end="url(#ah-map)"/>
  <path class="arrow" stroke-dasharray="6 5" d="M580 425 L810 314" marker-end="url(#ah-map)"/>
  <path class="arrow" style="stroke:var(--accent);stroke-width:3" d="M970 90 V126" marker-end="url(#ah-map)"/>
  <path class="arrow" style="stroke:var(--accent);stroke-width:3" d="M970 186 V396" marker-end="url(#ah-map)"/>
  <path class="arrow" style="stroke:var(--accent);stroke-width:3" d="M820 430 H896" marker-end="url(#ah-map)"/>
  <path class="arrow" style="stroke:var(--accent);stroke-width:3" d="M970 460 V496" marker-end="url(#ah-map)"/>
  <path class="arrow" d="M20 505 H70"/><text x="80" y="510" font-size="13">sync HTTP (/v1 and /internal)</text>
  <path class="arrow" stroke-dasharray="6 5" d="M300 505 H350"/><text x="360" y="510" font-size="13">events on Redis Streams</text>
  <path class="arrow" style="stroke:var(--accent);stroke-width:3" d="M580 505 H630"/><text x="640" y="510" font-size="13">media (audio)</text>
  <text x="20" y="540" font-size="12" class="small">The gateway and the bridge keep no database. The diagonal solid arrow is LiveKit's webhooks to call orchestration.</text>
</svg>
<figcaption>The platform from above. Solid lines are request and reply. Dashed lines are events that someone reads later. Thick accent lines carry audio.</figcaption>
</figure>

## The nine services

All nine are FastAPI apps on Python 3.11. Each does one job:

| Service | Its job |
|---|---|
| API gateway | The only public entry for `/v1/*`. Routes each path to a service. |
| Auth | Logins, JWTs, organizations, roles. |
| Assistant config | Assistants, their versions, and the catalog of STT, LLM and TTS providers. |
| Credentials | Stores customer API keys encrypted. The only service that can decrypt them. |
| Telephony provisioning | Buys or adopts phone numbers and attaches them to assistants. |
| Call orchestration | Owns the Call record and handles LiveKit's webhooks. The same image also runs the agent worker. |
| Webhook dispatcher | Sends signed webhooks to customers, with retries. |
| Recording and transcripts | Starts recordings, stores transcripts, deletes old data. |
| Media bridge | Carries phone audio from a carrier's WebSocket into a LiveKit room. |

A **Call row** is the database record for one call: who, when, status, how it ended. Half the services read or write it, which is why it lives in one owner, call orchestration.

## Why one public door

The **API gateway** is a reverse proxy: it takes a request, decides which service owns the path, and forwards it. Ours has no database. It matches paths against an ordered list of regular expressions, and the first match wins. Order matters. `/v1/calls/{id}/transcript` belongs to the recording service, but it also matches the general `/v1/calls` rule. So the transcript rule must sit above it.

One door gives one place to enforce two rules. Services talk to each other on `/internal/*` routes, guarded by a shared internal key in a header. The gateway always drops that header from outside requests, and it answers 404 to any path with a segment called `internal`. A customer can't reach an internal route, even by guessing it.

The media bridge is the exception. Carriers reach it on `/telephony/*` straight from the load balancer, because the gateway can't proxy WebSockets. [Two doors](lesson:voice-prod/two-doors-sip-and-websocket) covers why.

## Why a database per service

Seven services have state, and each gets its own Postgres database. The gateway and the bridge keep none. No service reads another's tables. If the recording service needs the Call row, it asks call orchestration over HTTP.

This costs you joins. What you get back: a schema change in one service can't break another, and credentials sit in a database that only one service can open. The credentials service is the only one holding the decryption key, and every other service asks it for a secret when needed.

## Three kinds of traffic

1. **Sync HTTP.** One service calls another and waits for the answer. Use it when the caller can't go on without the reply: "which assistant owns this number?"
2. **The event bus.** Call orchestration and the agent worker write call events (started, ended, transcript lines) to one **Redis stream**, an append-only log in Redis. The webhook dispatcher and the recording service each read it through their own **consumer group**, which tracks what that reader has handled ([Redis docs](https://redis.io/docs/latest/develop/data-types/streams/)). The writer doesn't wait for them, and a slow reader can't slow down a call.
3. **Media.** Audio never goes through HTTP or Redis. It moves through self-hosted, unmodified LiveKit: the server, plus its SIP, egress and ingress parts. The bridge and the agent both join the same room. LiveKit then sends the room's events to call orchestration as webhooks.

There is no gRPC anywhere. With only three kinds of traffic, there are only three kinds of failure to learn.

:::warn Gotcha from the platform
Our first local setup had no `webhook:` block in the LiveKit config. Calls connected and audio flowed, yet the agent quit with "no call row for room". LiveKit never told call orchestration that the room had started, so no Call row was ever created. The diagonal arrow in the diagram is easy to forget, and everything downstream depends on it.
:::

:::try
Take the path `/v1/calls/abc/recording`. Walk it down the gateway's rule order: recording rules first, then auth, assistants, credentials, telephony, and calls last. Which service gets it? Now move the `/v1/calls` rule to the top and walk it again. Which customer-facing feature breaks, and what would the error look like?
:::

:::note What we did not test
This map comes from reading the platform's service entry points, its gateway routing table and its compose file. We did not load-test it or time the HTTP hops between services. The labs for later lessons are in `code/voice-prod/`.
:::

:::say
One public door for requests, one side door for phone audio, and three kinds of traffic between nine services.
:::

:::check Why does the recording service read call events from Redis instead of being called by call orchestration over HTTP?
So call orchestration never waits on it. If the recording service is slow or down, calls go on. When it comes back, its consumer group picks up the events it hasn't handled yet.
:::

:::check Why can't a customer call an `/internal/*` route through the gateway?
The gateway returns 404 for any path with an `internal` segment, and it strips the internal-key header from every outside request.
:::
