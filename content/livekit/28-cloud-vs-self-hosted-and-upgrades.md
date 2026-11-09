---
title: Cloud vs self-hosted, and upgrading
summary: What only LiveKit Cloud does and what to run instead, how to move old agent code to livekit-agents 1.8, the server and egress renames, and a production checklist for a self-hosted stack that links back to every lesson in this track.
time: 25 min
---

Your agent runs on a server you own, and it works. Then someone pastes a docs snippet that uses `inference.LLM("openai/gpt-4.1-mini")` and it fails, because that model string goes to a Cloud service you don't have. A week later you upgrade `livekit-agents` and the logs fill with deprecation warnings. This lesson covers what self-hosting doesn't get and what changed between versions.

## What only Cloud does

LiveKit Cloud runs the same open-source server you ran in this track. The docs say your client and agent code stays portable, and that "the connection endpoint is the primary difference" ([LiveKit Cloud](https://docs.livekit.io/intro/cloud)). Everything around the server is different. These features exist only on Cloud, each with its self-hosted alternative:

| Cloud-only | Self-hosted alternative |
|---|---|
| LiveKit Inference (`inference.STT/LLM/TTS`, string model names) | Plugins with your own keys; local models via OpenAI-compatible `base_url` |
| Turn detector v1, adaptive interruption | `TurnDetector(version="v1-mini")` (local CPU), `interruption={"mode":"vad"}` |
| Enhanced noise cancellation (Krisp, BVC) | WebRTC `echoCancellation` / `noiseSuppression`; ai-coustics with your own license key |
| Agent observability, Insights, PII redaction | OpenTelemetry via `set_tracer_provider`, `make_session_report()`, egress recordings |
| Agent Console, simulations, `lk agent debugger --audio` | Console mode, `lk agent debugger` in text mode, the pytest framework |
| Token revocation, MoveParticipant / ForwardParticipant | Short token TTLs; remove the participant and don't re-issue |
| Phone Numbers, connectors (WhatsApp, Twilio Connector), region pinning | A SIP trunk from any provider plus the self-hosted `livekit/sip` service |
| Managed agent hosting (`lk agent create/deploy/...`), Agent Builder, the sandbox token server | Run agent servers yourself (Docker/K8s); write your own token endpoint |
| Global mesh (no per-room size limit) | Single-home rooms: one node per room, multi-node via Redis |

A self-hosted server is a **single-home SFU**: every participant in a room connects to the one node that hosts it. The docs list self-hosted rooms at "up to ~3,000" users. Cloud is a **global mesh SFU**, where each user connects to the nearest edge and rooms have no size limit ([LiveKit Cloud](https://docs.livekit.io/intro/cloud)). More self-hosted nodes give you more rooms, not bigger ones. Redis lets them share state ([distributed](https://docs.livekit.io/transport/self-hosting/distributed)).

:::note Self-hosted vs Cloud
The v1 turn detector is not locked to Cloud, but it runs on LiveKit Inference. A self-hosted agent can call it, and past a monthly development allowance each request is billed ([turn detector](https://docs.livekit.io/agents/logic/turns/turn-detector)). `v1-mini` runs on your CPU for free. On the lab, `MoveParticipant` returned "unknown: not implemented" ([the server API](lesson:livekit/the-server-api)).
:::

## Upgrade notes

<figure>
<svg viewBox="0 0 760 290" role="img" aria-labelledby="t-up d-up">
  <title id="t-up">The upgrade path for agents and for the server</title>
  <desc id="d-up">Top row: the Python agents framework moves from 0.x with VoicePipelineAgent, to 1.0 with AgentSession and Agent, to 1.6 with WorkerOptions and flat turn arguments, to 1.8 with AgentServer and TurnHandlingOptions. Only the first step needs a rewrite. Bottom row: older server calls and config, StartRoomCompositeEgress and prometheus_port, move to StartEgress with a source on server v1.13.5 or later, and prometheus.port.</desc>
  <defs><marker id="up-ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="20" y="28" font-size="13" font-weight="700">Agents framework (Python)</text>
  <g text-anchor="middle">
    <rect class="box" x="20" y="40" width="160" height="72" rx="10"/>
    <text x="100" y="64" font-size="14">Agents 0.x</text>
    <text x="100" y="84" font-size="12" class="small">VoicePipelineAgent</text>
    <text x="100" y="101" font-size="12" class="small">MultimodalAgent</text>
    <rect class="box" x="210" y="40" width="160" height="72" rx="10"/>
    <text x="290" y="64" font-size="14">Agents 1.0</text>
    <text x="290" y="84" font-size="12" class="small">AgentSession + Agent</text>
    <text x="290" y="101" font-size="12" class="small">@function_tool, nodes</text>
    <rect class="box" x="400" y="40" width="160" height="72" rx="10"/>
    <text x="480" y="64" font-size="14">Agents 1.6</text>
    <text x="480" y="84" font-size="12" class="small">WorkerOptions</text>
    <text x="480" y="101" font-size="12" class="small">flat turn kwargs</text>
    <rect class="box hot" x="590" y="40" width="160" height="72" rx="10"/>
    <text x="670" y="64" font-size="14">Agents 1.8</text>
    <text x="670" y="84" font-size="12" class="small">AgentServer</text>
    <text x="670" y="101" font-size="12" class="small">TurnHandlingOptions</text>
  </g>
  <path class="arrow" d="M180 76 H206" marker-end="url(#up-ah)"/>
  <path class="arrow" d="M370 76 H396" marker-end="url(#up-ah)"/>
  <path class="arrow" d="M560 76 H586" marker-end="url(#up-ah)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="195" y="134">breaking: rewrite</text><text x="195" y="150">the agent loop</text>
    <text x="385" y="134">1.3.1: RoomOptions</text><text x="385" y="150">same shape otherwise</text>
    <text x="575" y="134">old names still work</text><text x="575" y="150">and warn until v2.0</text>
  </g>
  <text x="20" y="190" font-size="13" font-weight="700">Server and services</text>
  <g text-anchor="middle">
    <rect class="box" x="20" y="202" width="270" height="72" rx="10"/>
    <text x="155" y="226" font-size="14">Older calls and config</text>
    <text x="155" y="246" font-size="12" class="small">StartRoomCompositeEgress</text>
    <text x="155" y="263" font-size="12" class="small">prometheus_port: 6789</text>
    <rect class="box hot" x="400" y="202" width="350" height="72" rx="10"/>
    <text x="575" y="226" font-size="14">Server v1.13.5 and later (lab: v1.13.11)</text>
    <text x="575" y="246" font-size="12" class="small">StartEgress with one source</text>
    <text x="575" y="263" font-size="12" class="small">prometheus: {port: 6789}</text>
  </g>
  <path class="arrow" d="M290 238 H396" marker-end="url(#up-ah)"/>
</svg>
<figcaption>Only 0.x to 1.0 is a rewrite. Every later step renames things, and the old names keep working with a warning, so you can upgrade first and clean up after.</figcaption>
</figure>

### Agents 0.x to 1.x

Agents 1.0 came out in April 2025 for Python. 0.x gets no more updates ([v0 migration, Python](https://docs.livekit.io/reference/migration-guides/v0-migration/python)).

| 0.x | 1.x |
|---|---|
| `VoicePipelineAgent`, `MultimodalAgent` | `AgentSession` running an `Agent`; one class for pipeline and speech-to-speech models |
| `before_llm_cb`, `before_tts_cb` | Override `llm_node` / `tts_node` on your `Agent` |
| `@llm.ai_callable` in an `llm.FunctionContext` | `@function_tool` methods on the `Agent`, taking a `RunContext` |
| Editing `chat_ctx.messages` | `agent.update_chat_ctx()` or a handoff |
| `publish_transcription()`, `TranscriptionReceived` | A text stream on topic `lk.transcription` (the framework writes both for now) |
| `user_started_speaking` / `agent_started_speaking` | `user_state_changed` / `agent_state_changed` |

### Agents 1.6 to 1.8

Older projects pinned 1.6.x. The docs now pin `livekit-agents~=1.8`, and the lab ran 1.8.11. We read these from the installed 1.8.11 package and the docs:

| 1.6 | 1.8 |
|---|---|
| `WorkerOptions(entrypoint_fnc=..., prewarm_fnc=..., agent_name=..., num_idle_processes=..., load_threshold=...)` | `server = AgentServer(...)`, `@server.rtc_session(agent_name=...)`, `server.setup_fnc = ...` ([server options](https://docs.livekit.io/agents/server/options)) |
| Flat turn kwargs on `AgentSession` | `turn_handling=TurnHandlingOptions(...)` ([turn handling options](https://docs.livekit.io/reference/agents/turn-handling-options)) |
| `session.on("metrics_collected")` | `ChatMessage.metrics` for per-turn latency, `session_usage_updated` for usage ([events](https://docs.livekit.io/reference/agents/events)) |
| `room_input_options=RoomInputOptions(...)`, `room_output_options=...` | `room_options=room_io.RoomOptions(...)`, since 1.3.1 ([agent sessions](https://docs.livekit.io/agents/logic/sessions)) |

The old forms still run. In the package, `WorkerOptions` is now an alias of `ServerOptions` (`worker.py`), and `AgentServer.from_server_options` copies `prewarm_fnc` into `setup_fnc`. The flat turn kwargs are wrapped in `@deprecate_params(..., target_version="v2.0")`. The session-level `metrics_collected` logs "metrics_collected is deprecated" when you subscribe. Per-plugin `metrics_collected` events are not deprecated. Even `cli.run_app` raises a `DeprecationWarning`, "the built-in Python CLI is deprecated", pointing at `lk agent ...` or `python -m livekit.agents`. Python hides that warning class by default, so the lab's runs never printed it.

`code/livekit/turn_config.py` passes a 1.6-style set of kwargs through the library's own `_migrate_turn_handling`:

```text
old flat kwargs : {"min_endpointing_delay": 0.4, "max_endpointing_delay": 3.0, "allow_interruptions": true, "min_interruption_duration": 0.6, "min_interruption_words": 2, "false_interruption_timeout": 1.5, "resume_false_interruption": true, "preemptive_generation": true}
new nested form : {"endpointing": {"min_delay": 0.4, "max_delay": 3.0}, "interruption": {"min_duration": 0.6, "min_words": 2, "false_interruption_timeout": 1.5, "resume_false_interruption": true}, "preemptive_generation": {"enabled": true}}
```

`allow_interruptions=True` maps to nothing, because it is already the default. Only `False` writes `interruption.enabled: false`. An old `agent_false_interruption_timeout` becomes `false_interruption_timeout`.

### Egress, server config, client SDKs

- **Egress.** `StartEgress` takes one source and one or more outputs. It replaces the five source-specific calls, and `StartRoomCompositeEgress` becomes `StartEgress` with a `TemplateSource`. Self-hosted, it needs server v1.13.5 or later ([egress API](https://docs.livekit.io/reference/other/egress/api)).
- **Server config.** The lab server warned "prometheus_port is deprecated, please switch to prometheus.port". The docs' sample config and the egress and ingress pages still show the flat key, so the warning is the source here, not the docs.
- **Client SDKs v1 to v2.** `room.participants` became `room.remoteParticipants`, keyed by identity instead of SID. `participant.tracks` became `trackPublications`. `publishData` takes recipient identities, a topic and a reliable flag. The room SID now arrives asynchronously, usually within 300 ms ([SDK v1 to v2](https://docs.livekit.io/reference/migration-guides/migrate-from-v1)).

:::warn Copied 1.8 examples can call Cloud models
Copy a 1.8 example from the docs and you may get `inference.*` string models or the v1 turn detector. Both call LiveKit Inference. On a self-hosted stack, use plugins with your own keys, and pin `TurnDetector(version="v1-mini")` and `interruption={"mode": "vad"}` yourself ([turns and interruptions](lesson:livekit/turns-and-interruptions)).
:::

:::tip CLI
These `lk` commands work self-hosted: `project`, `token`, `room`, `room participants` (except move/forward), `dispatch`, `egress`, `ingress`, `sip`, `perf load-test` / `agent-load-test`, `agent init/dev/start/console`, and `agent debugger` (text mode). `lk agent create`, `lk agent deploy` and `lk agent debugger --audio` need Cloud.
:::

## Self-hosted LiveKit production checklist

Each item links to the lesson that covers it.

### Server and network
- [ ] livekit-server, egress, ingress and SIP images are pinned to versions you tested, never `:latest`. ([production deployment](lesson:livekit/production-deployment))
- [ ] TLS sits in front of port 7880, the UDP range is open, and `use_external_ip: true` is set on cloud VMs. ([production deployment](lesson:livekit/production-deployment))
- [ ] Clients behind strict firewalls can reach TURN. ([WebRTC from the wire up](lesson:livekit/webrtc-from-the-wire-up))
- [ ] `empty_timeout` and `departure_timeout` are set on purpose. ([run it yourself](lesson:livekit/run-it-yourself))
- [ ] Every node, plus egress, ingress and SIP, shares one Redis. ([scaling and load](lesson:livekit/scaling-and-load))
- [ ] You ran `lk perf load-test` on your own hardware and know the biggest room one node can host. ([scaling and load](lesson:livekit/scaling-and-load))

### Security and tokens
- [ ] The API secret is at least 32 characters, lives in a secret store, and never ships to a client. ([tokens and grants](lesson:livekit/tokens-and-grants))
- [ ] Tokens are minted server-side with short TTLs, since self-hosted has no revocation. ([tokens and grants](lesson:livekit/tokens-and-grants))
- [ ] Grants are minimal; `can_update_own_metadata` only where a client sets attributes. ([data and state](lesson:livekit/data-and-state))
- [ ] Each person gets a unique identity, because a duplicate kicks the first one out. ([rooms, participants, tracks](lesson:livekit/rooms-participants-tracks))
- [ ] The webhook receiver verifies signatures and dedupes by `event.id`. ([webhooks and events](lesson:livekit/webhooks-and-events))
- [ ] Your backend counts people with `ListParticipants`, not `ListRooms`. ([the server API](lesson:livekit/the-server-api))

### Agents
- [ ] Every agent sets `agent_name` and is dispatched explicitly. ([agent server and dispatch](lesson:livekit/agent-server-and-dispatch))
- [ ] You checked the production defaults: 12 idle processes, load threshold 0.7, drain timeout 3600 s. ([agent server and dispatch](lesson:livekit/agent-server-and-dispatch))
- [ ] Turn detection is `v1-mini` and interruption is `vad`, set explicitly. ([turns and interruptions](lesson:livekit/turns-and-interruptions))
- [ ] No `inference.*` models; every model is a plugin with your key or a local server. ([models without the cloud](lesson:livekit/models-without-the-cloud))
- [ ] STT, LLM and TTS each have a fallback. ([nodes, hooks, RAG, fallbacks](lesson:livekit/nodes-hooks-rag-fallbacks))
- [ ] Tool calls have pytest tests, with `mock_tools` lambdas that take `ctx` first. ([testing and observability](lesson:livekit/testing-and-observability))

### Telephony
- [ ] SIP port 5060 and the RTP range are open only to your provider's addresses. ([self-hosted SIP](lesson:livekit/self-hosted-sip))
- [ ] Logs and dashboards treat room names as PII, since they contain the caller's number. ([SIP fundamentals](lesson:livekit/sip-fundamentals))
- [ ] Outbound calls catch failures and read the SIP status code. ([phone features](lesson:livekit/phone-features))
- [ ] AMD waits for the callee's identity, and someone decides who speaks first. ([phone features](lesson:livekit/phone-features))

### Recording
- [ ] Recordings start with `StartEgress`, not the deprecated per-source calls. ([egress recording](lesson:livekit/egress-recording))
- [ ] The egress output path is writable, and egress hosts are sized by `cpu_cost`. ([egress recording](lesson:livekit/egress-recording))
- [ ] Ingress sets `cpu_cost`; unset, it logs "max cost: 0.000000" and warns about every input. ([ingress](lesson:livekit/ingress))

### Observability
- [ ] Prometheus scrapes `prometheus.port` on every node. ([production deployment](lesson:livekit/production-deployment))
- [ ] Agent traces go to your OpenTelemetry backend via `set_tracer_provider`. ([testing and observability](lesson:livekit/testing-and-observability))
- [ ] Per-turn latency comes from `ChatMessage.metrics`, usage from `session_usage_updated`. ([testing and observability](lesson:livekit/testing-and-observability))

### Upgrades
- [ ] `livekit-agents` and its plugins are pinned together, and you read the notes above before moving. ([agents mental model](lesson:livekit/agents-mental-model))
- [ ] CI fails on deprecation warnings, so renames show up before v2.0 removes them. ([cloud vs self-hosted](lesson:livekit/cloud-vs-self-hosted-and-upgrades))
- [ ] Frontends use client SDK v2 names and read the room SID asynchronously. ([frontends and sessions](lesson:livekit/frontends-and-sessions))
- [ ] Your shell has no stray `LIVEKIT_*` variables, because they beat the saved `lk` project. ([the lk CLI](lesson:livekit/the-lk-cli))

## Capstone

:::try
Each exercise combines lab scripts in `code/livekit/`. Predict, then run.

1. **A phone call, end to end.** Start `webhook_receiver.py` and `echo_agent.py start`, run `sip_setup.sh`, then `sip_call.py`. List every webhook in order. Which one carries `sip_+15550001111`, and where does the caller's number show up?
2. **Record the call.** Make `sip_call.py` stream for 30 s. While it runs, find the room with `lk room list`, put its name in a copy of `egress/room-audio.json`, and `lk egress start` it. Does the file's length match the call? Which `egress_*` webhooks reach the receiver?
3. **Echo under load.** Run `echo_check.py` alone (0.63 s on the lab), then again while `load_test.sh` runs. How much of the delay is the server and how much is your own CPU?
4. **Upgrade in reverse.** Rewrite `echo_agent.py` in 1.6 style with `WorkerOptions(entrypoint_fnc=..., agent_name="echo")` and `cli.run_app`. Does it still register on 1.8.11? Run it with `python -W default` and list the warnings. Then add your own flat turn kwargs to `turn_config.py` and read the nested form.
5. **No revocation.** With `tokens.py`, mint a 2-minute token. Join, remove the participant with `room_admin.py`'s `remove_participant` call, and join again with the same token. What does that tell you about TTLs on a self-hosted server?
:::

:::note What we did not test
We did not migrate a real 0.x or 1.6 project. We did not call `StartRoomCompositeEgress` on the lab, and we did not run a client SDK v2 migration. The 1.6 to 1.8 notes come from reading the installed 1.8.11 package and the docs; no migration guide covers them. The capstone exercises combine scripts we ran one by one, but we did not run the combinations.
:::

:::say
Self-hosted LiveKit runs the same server as Cloud, minus inference, managed hosting, observability and the global mesh; and every upgrade since 1.0 is a rename you can make one warning at a time.
:::

:::check Why can't you make one self-hosted room bigger by adding nodes?
A self-hosted server is single-home: every participant in a room connects to the node that hosts that room. More nodes, sharing Redis, host more rooms, not bigger ones. Only Cloud's global mesh spreads one room across edges.
:::

:::check A 1.6 agent runs on 1.8.11 without code changes. Why fix it now?
The old kwargs and `WorkerOptions` still work, but they warn and are marked for removal in v2.0. The docs only show the new names, so every example you copy will use them.
:::

The Voice in production track comes next. It is a case study that shows these pieces inside a real phone platform, including the mistakes it made by skipping the docs.
