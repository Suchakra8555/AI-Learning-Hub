---
title: Mesh, MCU and SFU
summary: Three ways to move audio between more than two parties, what each costs, and why a voice agent fits best in a room on a selective forwarding unit.
time: 18 min
---

A phone call with an agent sounds like two parties, but it rarely stays at two. You want a recorder on every call. Someone wants to listen in live, and support may want to add a human later. Once three or four parties share a call, you have to decide where the audio goes and who pays for moving it.

[The last lesson](lesson:livekit/webrtc-from-the-wire-up) covered one WebRTC connection. Here we connect many of them.

## Three topologies

- **Mesh** (plain peer to peer): every participant sends its stream straight to every other participant. There is no media server. Each client uploads n − 1 copies.
- **MCU** (multipoint control unit): every participant sends one stream to a server. The server decodes all of them, mixes them, re-encodes, and sends each participant one mixed stream.
- **SFU** (selective forwarding unit): every participant sends one stream to a server. The server forwards copies of the encoded packets to whoever subscribes, **without decoding or re-encoding**.

LiveKit's SFU page compares the three and says LiveKit is an SFU ([LiveKit SFU](https://docs.livekit.io/reference/internals/livekit-sfu/)). It says peer to peer "works well for 2–3 peers". It says an MCU saves bandwidth, but your app "can't adjust the volume of an individual audio stream, because the MCU has already mixed it", and decoding every stream needs a big server. An SFU "trades downstream bandwidth for flexibility and scalability".

<figure>
<svg viewBox="0 0 880 310" role="img" aria-labelledby="t-topo d-topo">
  <title id="t-topo">Mesh, MCU and SFU with four participants each</title>
  <desc id="d-topo">Left: mesh, four participants all linked to each other with six links. Middle: MCU, four participants each send one stream to a server that decodes, mixes and re-encodes, and receive one mixed stream back. Right: SFU, four participants each send one stream to a server that forwards packets untouched, and each receives three streams.</desc>
  <defs><marker id="ah-topo" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="15" font-weight="700" text-anchor="middle">
    <text x="140" y="26">Mesh</text><text x="435" y="26">MCU</text><text x="730" y="26">SFU</text>
  </g>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="20" y="50" width="64" height="34" rx="8"/><text x="52" y="72">A</text>
    <rect class="box" x="196" y="50" width="64" height="34" rx="8"/><text x="228" y="72">B</text>
    <rect class="box" x="20" y="200" width="64" height="34" rx="8"/><text x="52" y="222">C</text>
    <rect class="box" x="196" y="200" width="64" height="34" rx="8"/><text x="228" y="222">D</text>
    <rect class="box" x="315" y="50" width="64" height="34" rx="8"/><text x="347" y="72">A</text>
    <rect class="box" x="491" y="50" width="64" height="34" rx="8"/><text x="523" y="72">B</text>
    <rect class="box" x="315" y="200" width="64" height="34" rx="8"/><text x="347" y="222">C</text>
    <rect class="box" x="491" y="200" width="64" height="34" rx="8"/><text x="523" y="222">D</text>
    <rect class="box hot" x="385" y="120" width="100" height="44" rx="8"/><text x="435" y="140">MCU</text><text x="435" y="157" font-size="11" class="small">decode + mix</text>
    <rect class="box" x="610" y="50" width="64" height="34" rx="8"/><text x="642" y="72">A</text>
    <rect class="box" x="786" y="50" width="64" height="34" rx="8"/><text x="818" y="72">B</text>
    <rect class="box" x="610" y="200" width="64" height="34" rx="8"/><text x="642" y="222">C</text>
    <rect class="box" x="786" y="200" width="64" height="34" rx="8"/><text x="818" y="222">D</text>
    <rect class="box hot" x="680" y="120" width="100" height="44" rx="8"/><text x="730" y="140">SFU</text><text x="730" y="157" font-size="11" class="small">forward only</text>
  </g>
  <path class="arrow" d="M84 67 H196"/><path class="arrow" d="M84 217 H196"/>
  <path class="arrow" d="M52 84 V200"/><path class="arrow" d="M228 84 V200"/>
  <path class="arrow" d="M84 84 L196 200"/><path class="arrow" d="M196 84 L84 200"/>
  <path class="arrow" d="M379 84 L400 116" marker-start="url(#ah-topo)" marker-end="url(#ah-topo)"/>
  <path class="arrow" d="M491 84 L470 116" marker-start="url(#ah-topo)" marker-end="url(#ah-topo)"/>
  <path class="arrow" d="M379 200 L400 168" marker-start="url(#ah-topo)" marker-end="url(#ah-topo)"/>
  <path class="arrow" d="M491 200 L470 168" marker-start="url(#ah-topo)" marker-end="url(#ah-topo)"/>
  <path class="arrow" d="M674 84 L695 116" marker-start="url(#ah-topo)" marker-end="url(#ah-topo)"/>
  <path class="arrow" d="M786 84 L765 116" marker-start="url(#ah-topo)" marker-end="url(#ah-topo)"/>
  <path class="arrow" d="M674 200 L695 168" marker-start="url(#ah-topo)" marker-end="url(#ah-topo)"/>
  <path class="arrow" d="M786 200 L765 168" marker-start="url(#ah-topo)" marker-end="url(#ah-topo)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="140" y="266">No server. Each peer</text><text x="140" y="284">uploads 3 copies.</text>
    <text x="435" y="266">1 stream up, 1 mixed stream down.</text><text x="435" y="284">Server decodes all 4.</text>
    <text x="730" y="266">1 stream up, 3 streams down.</text><text x="730" y="284">Server decodes none.</text>
  </g>
</svg>
<figcaption>Same four people, three shapes. The difference is who uploads how much, and whether a server has to decode audio.</figcaption>
</figure>

## The numbers

`code/livekit/sfu_math.py` counts the bandwidth for each shape. Every participant publishes one audio stream at 32 kbit/s, a typical Opus voice rate.

```python
def mcu(n):    # server decodes all, mixes one stream per person, re-encodes
    return dict(client_up=KBPS, client_down=KBPS, server_in=n * KBPS, server_out=n * KBPS, decodes=n)

def sfu(n):    # server forwards packets untouched
    return dict(client_up=KBPS, client_down=(n - 1) * KBPS, server_in=n * KBPS, server_out=n * (n - 1) * KBPS, decodes=0)
```

Real output of `python3 code/livekit/sfu_math.py`. The script prints "kb", but every number is kbit/s:

```text
  n topology  client up  client down  server out  server decodes
  2 mesh          32 kb        32 kb        0 kb               0
  2 MCU           32 kb        32 kb       64 kb               2
  2 SFU           32 kb        32 kb       64 kb               0

  3 mesh          64 kb        64 kb        0 kb               0
  3 MCU           32 kb        32 kb       96 kb               3
  3 SFU           32 kb        64 kb      192 kb               0

 10 mesh         288 kb       288 kb        0 kb               0
 10 MCU           32 kb        32 kb      320 kb              10
 10 SFU           32 kb       288 kb     2880 kb               0

A voice-agent call is n=2: caller + agent. The SFU just forwards; the agent does its own decoding.
```

Read the columns. Mesh makes each client upload n − 1 copies, which hurts a phone on a weak uplink. The MCU keeps every client at 32 kbit/s but decodes 10 streams for 10 people. The SFU never decodes. It pays in server output, which grows with n × (n − 1).

The script assumes everyone publishes. A recorder or a silent listener only subscribes. Take a call with a caller, an agent and a recorder: two tracks, each forwarded to two subscribers, is 4 × 32 = 128 kbit/s out, not the 192 in the n=3 row. Adding a listener costs one more copy of each track and zero decoding.

## Why an SFU fits a voice agent

The agent is just another participant. It joins the room, subscribes to the caller's track, and publishes its own. The agent decodes the caller's Opus itself, because it needs raw samples for speech-to-text anyway. Nothing else in the path has to decode.

The server doesn't transcode. An MCU would decode, mix and re-encode, which adds work and delay on the [latency budget](lesson:voice/where-the-milliseconds-go). It would also hand the agent a mix when the agent wants the caller's voice on its own.

Observers and recorders are cheap to add. LiveKit **egress** records a room or single tracks ([LiveKit egress](https://docs.livekit.io/transport/media/ingress-egress/egress/)). To the SFU it's one more subscriber. Since the tracks stay separate, you can record and transcribe each speaker on their own.

<figure>
<svg viewBox="0 0 880 360" role="img" aria-labelledby="t-room d-room">
  <title id="t-room">A voice-agent room on an SFU</title>
  <desc id="d-room">The caller publishes one audio track to the SFU and receives the agent's track. The agent publishes one track and receives the caller's track. The recorder, an egress worker, publishes nothing and receives both tracks. The SFU forwards packets without decoding.</desc>
  <defs><marker id="ah-room" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="20" y="120" width="190" height="70" rx="10"/><text x="115" y="150">Caller</text><text x="115" y="172" font-size="12" class="small">browser or phone bridge</text>
    <rect class="box hot" x="330" y="110" width="220" height="90" rx="10"/><text x="440" y="145">LiveKit SFU (one room)</text><text x="440" y="170" font-size="12" class="small">forwards, never decodes</text>
    <rect class="box" x="670" y="120" width="190" height="70" rx="10"/><text x="765" y="150">Agent worker</text><text x="765" y="172" font-size="12" class="small">STT → LLM → TTS</text>
    <rect class="box" x="340" y="280" width="200" height="60" rx="10"/><text x="440" y="306">Recorder (egress)</text><text x="440" y="326" font-size="12" class="small">subscribes only</text>
  </g>
  <path class="arrow" d="M210 140 H326" marker-end="url(#ah-room)"/>
  <path class="arrow" d="M330 172 H214" marker-end="url(#ah-room)"/>
  <path class="arrow" d="M670 140 H554" marker-end="url(#ah-room)"/>
  <path class="arrow" d="M550 172 H666" marker-end="url(#ah-room)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M410 200 V276" marker-end="url(#ah-room)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M470 200 V276" marker-end="url(#ah-room)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="268" y="132">caller track up</text>
    <text x="268" y="190">agent track down</text>
    <text x="612" y="132">agent track up</text>
    <text x="612" y="190">caller track down</text>
    <text x="330" y="244">caller track</text>
    <text x="552" y="244">agent track</text>
  </g>
</svg>
<figcaption>Three participants, two published tracks. The recorder costs two forwarded copies and no decoding.</figcaption>
</figure>

## Simulcast, selective subscription and RTCP

**Simulcast** means a publisher sends the same video at several quality layers, and the SFU forwards the layer each subscriber can handle. LiveKit's server "estimates the downstream bandwidth for each subscriber and forwards the quality layer... that fits within it" ([LiveKit SFU](https://docs.livekit.io/reference/internals/livekit-sfu/), [simulcast](https://docs.livekit.io/transport/media/advanced/#video-simulcast)). It matters for video. A single voice track at around 32 kbit/s rarely needs it.

**Selective subscription** lets a participant choose which tracks it receives. LiveKit subscribes you to every track by default (`autoSubscribe`). Turn that off and only tracks you subscribe to are delivered ([subscribing to tracks](https://docs.livekit.io/transport/media/subscribe/)). A recorder that only wants the caller, or an agent that should ignore a supervisor's mic, can use this.

With an SFU, each participant has its own WebRTC connection to the server, not to the other participants. So RTCP reports and NACKs from a subscriber go to the SFU. In general an SFU can answer a NACK from packets it has cached and use the reports to estimate each subscriber's bandwidth, rather than pushing every request back to the publisher. LiveKit's docs confirm the bandwidth estimation. We didn't check how it handles NACKs in its code.

## Inside LiveKit's SFU

**livekit-server** is written in Go on top of **Pion**, a Go implementation of WebRTC. A single node has no outside dependencies. Several nodes need **Redis**, which records which node hosts each room and passes messages between nodes, so every client in a room lands on the same node ([LiveKit SFU](https://docs.livekit.io/reference/internals/livekit-sfu/)). That is why a self-hosted room must fit on one node. At two or three participants per voice call, the limit is far away.

The server also adapts what each subscriber gets. It estimates the downstream bandwidth of each subscriber and forwards the quality layer that fits, such as a lower resolution or bitrate. In SDKs with **adaptive stream**, the client can also ask for a resolution that matches its video element and pause video nobody can see (same page).

**Signaling** is LiveKit's own protocol. The [client protocol page](https://docs.livekit.io/reference/internals/client-protocol/) describes it:

- The client opens a WebSocket to `/rtc` with its access token, `auto_subscribe` and a `protocol` version. Messages are Protocol Buffers: the client sends `SignalRequest`, the server sends `SignalResponse`.
- Each client has up to two PeerConnections, one for publishing and one for subscribing. The side that sends tracks always makes the offer. Separate connections avoid **glare**, where both sides send an offer at once.
- The subscriber connection opens at join, and the server makes its offer. The publisher connection opens only when the client first publishes.
- Server events (`ParticipantUpdate`, `SpeakersChanged`, `LeaveRequest`) can repeat, so clients must handle them idempotently.

The docs say the current protocol version is 17. On the lab (livekit-server v1.13.11), the server log showed the `lk` CLI's Go SDK joining with `"protocol": 17`, and the Python agent server (livekit-agents 1.8.11) registered with `protocol: 18`. So SDKs already speak a newer version than the docs page states, and the server accepts both.

:::note Self-hosted vs Cloud
Self-hosted, each room lives on one node, up to about 3,000 users per room. LiveKit Cloud runs a global mesh of SFUs with no per-room limit, and each user connects to the nearest edge ([LiveKit Cloud](https://docs.livekit.io/intro/cloud/)). For voice agents this gap rarely matters. Add nodes with Redis for more rooms, not bigger ones.
:::

:::tip CLI
`lk room list` shows the rooms on your server. `lk room participants list <room>` shows who is connected. `lk perf load-test` measures what one node can forward (see the scaling lesson).
:::

For how a real system lays out caller, agent and recorder in one room, see [the system map](lesson:voice-prod/the-system-map) in the Voice in production track.

:::warn "Just another participant" works both ways
The agent joins rooms like any client. LiveKit's docs say that an agent with `agent_name` set is only sent to rooms when it is dispatched explicitly. Without `agent_name`, it is dispatched automatically into every new room ([agent dispatch](https://docs.livekit.io/agents/server/agent-dispatch/)). That includes rooms that were never meant to have an agent, such as a load test or a recording-only room.
:::

:::try
Add `4` to the tuple `(2, 3, 10)` in `sfu_math.py` and predict the SFU row's client down and server out before you run it. Then set `KBPS = 24` and check that every number scales by exactly 0.75. Why does the "server decodes" column not change?
:::

:::note What we did not test
We read LiveKit's SFU, client protocol, subscription, egress and dispatch pages. The two protocol numbers come from the lab's logs. We didn't measure bandwidth per topology on a live room here, and we didn't read the server's NACK or bandwidth-estimation code. `sfu_math.py` leaves out video, simulcast, RTCP overhead and the encoding cost on each client.
:::

:::say
An SFU forwards encoded packets without decoding them, so the agent, the caller and any recorder are equal participants, and adding a listener costs bandwidth, not CPU.
:::

:::check In a call with a caller, an agent and a silent supervisor, how many audio tracks does the SFU forward per second's worth of audio?
Two tracks are published (caller and agent). The caller's track goes to the agent and the supervisor, and the agent's track goes to the caller and the supervisor. That makes four forwarded copies, about 128 kbit/s at 32 kbit/s each.
:::

:::check Why not use an MCU so every client receives only one stream?
The MCU must decode and re-encode every stream, which costs server CPU and adds delay. It also hands out a mix, so the agent and the recorder lose the separate per-speaker tracks they want.
:::
