---
title: What LiveKit is
summary: The parts of a self-hosted LiveKit deployment and how they connect, what you give up without LiveKit Cloud and what to use instead, and how the 28 lessons in this track are laid out.
time: 15 min
---

If you read [WebRTC, phone lines, and LiveKit](lesson:voice/webrtc-sip-livekit), you met the names. This track teaches the whole system, run on your own machines.

Maybe you built a voice agent from a starter template. It joins a room, it talks, it works. Then someone asks why calls drop behind a corporate VPN, where the recordings go, or whether the phone line can run without LiveKit Cloud, and you don't know which piece to look at. LiveKit is several programs, and each one fails in its own way. This lesson names them and shows how they connect.

## The pieces

- **livekit-server** is an open source WebRTC **SFU** (selective forwarding unit): it receives each participant's media and forwards it to the participants who subscribe, without decoding it. It also handles signaling, NAT traversal and quality control ([about LiveKit](https://docs.livekit.io/intro/about/)). It is written in Go on **Pion**, a Go WebRTC library ([LiveKit SFU](https://docs.livekit.io/reference/internals/livekit-sfu/)).
- **Redis** is optional for one node and required for several. It records which node hosts each room and carries messages between nodes and services (same page).
- **Client SDKs** (web, iOS, Android, Flutter, Unity, Python and more) join rooms and publish and subscribe to tracks. Agents use the same SDKs as human clients ([about LiveKit](https://docs.livekit.io/intro/about/)).
- **Server SDKs** call the server API from your backend: create rooms, list participants, sign tokens. The API is Twirp, which means JSON over HTTP POST ([room service API](https://docs.livekit.io/reference/other/roomservice-api/)).
- **Agents** is the Python and Node.js framework for voice agents: speech in, model, speech out, turn-taking and tools. An agent joins the room as a participant ([Agents](https://docs.livekit.io/agents/)).
- **Egress** records or streams a room or single tracks. **Ingress** brings in media that isn't WebRTC, such as RTMP from OBS. **SIP** connects phone calls. Self-hosted, each of these runs as its own service ([LiveKit Cloud comparison](https://docs.livekit.io/intro/cloud/)).
- **`lk`** is the command-line tool for tokens, rooms, dispatch, egress, ingress, SIP and load tests ([LiveKit CLI](https://docs.livekit.io/intro/basics/cli/)).

<figure>
<svg viewBox="0 0 880 420" role="img" aria-labelledby="map-t map-d">
  <title id="map-t">Map of a self-hosted LiveKit deployment</title>
  <desc id="map-d">A browser or app and an agent server connect to livekit-server over WebRTC. Your backend hands out access tokens and receives webhooks from livekit-server. livekit-server talks to Redis, and Redis connects to the egress, ingress and SIP services. OBS or ffmpeg sends RTMP or WHIP to ingress. A phone carrier sends SIP and RTP to the SIP service.</desc>
  <defs><marker id="map-ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="16" y="40" width="170" height="56" rx="10"/><text x="101" y="64">Browser or app</text><text x="101" y="84" font-size="12" class="small">client SDK</text>
    <rect class="box" x="16" y="130" width="170" height="56" rx="10"/><text x="101" y="154">Agent server</text><text x="101" y="174" font-size="12" class="small">Agents framework</text>
    <rect class="box" x="16" y="208" width="170" height="56" rx="10"/><text x="101" y="241">OBS / ffmpeg</text>
    <rect class="box" x="16" y="330" width="170" height="56" rx="10"/><text x="101" y="354">Phone carrier</text><text x="101" y="374" font-size="12" class="small">SIP trunk</text>
    <rect class="box hot" x="290" y="100" width="200" height="110" rx="10"/><text x="390" y="148">livekit-server</text><text x="390" y="170" font-size="12" class="small">SFU in Go, on Pion</text>
    <rect class="box" x="560" y="130" width="110" height="50" rx="10"/><text x="615" y="160">Redis</text>
    <rect class="box" x="730" y="40" width="134" height="56" rx="10"/><text x="797" y="64">Your backend</text><text x="797" y="84" font-size="12" class="small">tokens, webhooks</text>
    <rect class="box" x="730" y="110" width="134" height="56" rx="10"/><text x="797" y="134">livekit/egress</text><text x="797" y="154" font-size="12" class="small">recording</text>
    <rect class="box" x="730" y="208" width="134" height="56" rx="10"/><text x="797" y="232">livekit/ingress</text><text x="797" y="252" font-size="12" class="small">RTMP, WHIP, URL</text>
    <rect class="box" x="730" y="318" width="134" height="56" rx="10"/><text x="797" y="342">livekit/sip</text><text x="797" y="362" font-size="12" class="small">phone calls</text>
  </g>
  <path class="arrow" d="M186 68 L286 120" marker-start="url(#map-ah)" marker-end="url(#map-ah)"/>
  <path class="arrow" d="M186 158 H286" marker-start="url(#map-ah)" marker-end="url(#map-ah)"/>
  <path class="arrow" d="M490 112 L726 66" marker-end="url(#map-ah)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M797 40 V24 H101 V36" marker-end="url(#map-ah)"/>
  <path class="arrow" d="M490 155 H556" marker-start="url(#map-ah)" marker-end="url(#map-ah)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M670 155 H700 M700 138 V346 M700 138 H726 M700 250 H726 M700 346 H726"/>
  <path class="arrow" d="M186 228 H726" marker-end="url(#map-ah)"/>
  <path class="arrow" d="M186 400 H797 V378" marker-end="url(#map-ah)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="440" y="18">access token from your token endpoint</text>
    <text x="256" y="94">WebRTC</text>
    <text x="236" y="150">WebRTC</text>
    <text x="610" y="80">webhooks</text>
    <text x="615" y="200">control via Redis</text>
    <text x="440" y="222">RTMP or WHIP</text>
    <text x="440" y="394">SIP + RTP</text>
  </g>
</svg>
<figcaption>Clients and agents talk WebRTC to the server. Your backend issues tokens and receives webhooks. Egress, ingress and SIP get their work through Redis, then join rooms as participants.</figcaption>
</figure>

## How the pieces work together on one call

1. Your backend signs an **access token** (a JWT naming the room, the identity and the permissions) with the API secret. The browser connects to livekit-server with it.
2. The server creates the room if needed and sends a webhook to your backend.
3. The server dispatches an agent. The agent server joins the room as a second participant and subscribes to the caller's audio.
4. If you start a recording, the server passes the job through Redis to an egress worker, which joins the room and writes a file.
5. A phone call takes the same path, except the carrier reaches `livekit/sip`, and the SIP service joins the room for the caller.

The lab in this track runs all of it on one Linux machine with Docker Compose: livekit-server **v1.13.11**, `lk` **v2.19.3**, livekit/egress v1.15.0, livekit/ingress v1.6.0, livekit/sip v1.23.0 and Redis 7. The Python side uses `livekit` 1.2.0, `livekit-api` 1.2.2 and `livekit-agents` 1.8.11. Setup is in [Run it yourself](lesson:livekit/run-it-yourself).

## Self-hosted vs LiveKit Cloud

LiveKit Cloud runs the same open source server and the same APIs. It adds things around the server ([LiveKit Cloud](https://docs.livekit.io/intro/cloud/)). These are Cloud-only, with what this track uses instead:

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

:::note Self-hosted vs Cloud
The docs list a self-hosted room at up to about 3,000 users, because a room must fit on one node. LiveKit Cloud has no per-room limit ([LiveKit Cloud](https://docs.livekit.io/intro/cloud/)). Code moves between the two: per the same page, the connection endpoint is the main difference.
:::

## How this track is organized

- **A. Foundations:** 01 What LiveKit is · 02 [WebRTC from the wire up](lesson:livekit/webrtc-from-the-wire-up) · 03 [Mesh, MCU and SFU](lesson:livekit/mesh-mcu-sfu) · 04 [Run it yourself](lesson:livekit/run-it-yourself) · 05 [The lk CLI](lesson:livekit/the-lk-cli)
- **B. Core model:** 06 [Rooms, participants and tracks](lesson:livekit/rooms-participants-tracks) · 07 [Tokens and grants](lesson:livekit/tokens-and-grants) · 08 [The server API](lesson:livekit/the-server-api) · 09 [Webhooks and events](lesson:livekit/webhooks-and-events) · 10 [Media in depth](lesson:livekit/media-in-depth) · 11 [Data and state](lesson:livekit/data-and-state)
- **C. Agents:** 12 [The agents mental model](lesson:livekit/agents-mental-model) · 13 [Agent server and dispatch](lesson:livekit/agent-server-and-dispatch) · 14 [Turns and interruptions](lesson:livekit/turns-and-interruptions) · 15 [Tools, tasks and workflows](lesson:livekit/tools-tasks-and-workflows) · 16 [Nodes, hooks, RAG and fallbacks](lesson:livekit/nodes-hooks-rag-fallbacks) · 17 [Models without the Cloud](lesson:livekit/models-without-the-cloud)
- **D. Around the agent:** 18 [Frontends and sessions](lesson:livekit/frontends-and-sessions) · 19 [Testing and observability](lesson:livekit/testing-and-observability)
- **E. Telephony:** 20 [SIP fundamentals](lesson:livekit/sip-fundamentals) · 21 [Self-hosted SIP](lesson:livekit/self-hosted-sip) · 22 [Phone features](lesson:livekit/phone-features)
- **F. Media services:** 23 [Egress and recording](lesson:livekit/egress-recording) · 24 [Ingress](lesson:livekit/ingress)
- **G. Production:** 25 [Production deployment](lesson:livekit/production-deployment) · 26 [Scaling and load](lesson:livekit/scaling-and-load) · 27 [Robotics and hardware](lesson:livekit/robotics-and-hardware) · 28 [Cloud vs self-hosted, and upgrades](lesson:livekit/cloud-vs-self-hosted-and-upgrades)

Every lesson runs its code against the lab and pastes the real output. Each one says what we did not test.

:::tip CLI
After starting the lab: `lk project add lab --url http://127.0.0.1:7880 --api-key lab-key --api-secret <secret> --default`, then `lk room list`. `lk --help` lists every command group, and [lesson 5](lesson:livekit/the-lk-cli) marks which ones work self-hosted.
:::

:::try
Start the lab (`cd code/livekit/lab && docker compose up -d`) and run `curl localhost:7880`. It should print `OK`. Then run `docker compose ps` and match each running container to a box in the map above. Which boxes have no container yet, and which Compose profile starts them?
:::

:::warn Docs examples often assume LiveKit Cloud
Many examples in the docs use LiveKit Inference model strings, the v1 turn detector or `lk agent deploy`. On a self-hosted server these fail or need a key you don't have. Check each feature against the table above before you copy an example.
:::

:::note What we did not test
This lesson is a map, and its facts come from the docs. We ran every service in the map on the lab, but only on one machine: no multi-node Redis cluster, no TURN, no Kubernetes.
:::

:::say
LiveKit is an SFU plus a set of separate services (Redis, Agents, egress, ingress, SIP and the `lk` CLI), and self-hosting it means running each one and replacing the Cloud-only extras yourself.
:::

:::check Which pieces do you need to run for a browser-only voice agent with no recording and no phone calls?
livekit-server, an agent server, and a backend that issues tokens. Redis is optional on a single node. Egress, ingress and SIP aren't needed.
:::

:::check A docs example uses `inference.LLM("openai/gpt-4.1-mini")`. Will it work against your self-hosted server?
No. LiveKit Inference is Cloud-only. Use the model's plugin with your own API key, or a local model through an OpenAI-compatible `base_url`.
:::
