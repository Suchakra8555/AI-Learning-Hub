---
title: WebRTC, phone lines, and LiveKit in plain words
summary: How audio gets from a browser or a phone to your agent, and what LiveKit's parts are for.
time: 20 min
---

Your agent needs a way to hear the caller. There are two common doors in: a web browser, and a normal phone call.

## WebRTC: the browser door

**WebRTC** lets two devices send audio and video straight to each other. Before they can, they must find a network path. MDN names the pieces ([source](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Protocols)):

- **ICE** tries the possible paths between two devices.
- **STUN** tells a device what its public address is.
- **TURN** relays the traffic when no direct path works.
- **SDP** is a text description of the media, such as which codecs each side supports.
- **Signaling** is how the two sides swap that information. WebRTC does not include it. You supply your own.

## SIP: the phone door

**SIP** is the protocol that starts, changes, and ends calls. RFC 3261 calls it an application-layer signaling protocol for sessions, and says it relies on other protocols for the audio itself ([RFC 3261](https://datatracker.ietf.org/doc/html/rfc3261)). A **SIP trunk** connects your system to a phone provider. An **inbound** trunk takes calls in. An **outbound** trunk places calls out. In LiveKit, a **dispatch rule** decides which room an inbound caller joins ([source](https://docs.livekit.io/sip/)).

## LiveKit's four parts

LiveKit is a real-time media platform built on WebRTC. From its docs:

| Part | What it does |
|---|---|
| **Agents** | An open-source framework (Apache 2.0). Your Python or Node.js program joins a room as a participant and talks. |
| **SIP** | Connects phone calls into rooms. |
| **Ingress** | Brings in sources that are not WebRTC, such as RTMP, WHIP or files. |
| **Egress** | Exports a room or tracks, for example to MP4, HLS or RTMP. This is how you record a call. |

Sources: [Agents](https://docs.livekit.io/agents/), [Ingress](https://docs.livekit.io/home/ingress/overview/), [Egress](https://docs.livekit.io/home/egress/overview/). LiveKit Cloud includes egress. If you host LiveKit yourself, egress is a separate deployment.

With a media platform like this, one agent can serve both doors. A browser caller and a phone caller both end up in a room with the agent.

:::note What we did not test
We read these pages. We did not run LiveKit, place a SIP call, or set up a trunk here. A real phone number needs a paid provider. For a first hands-on step, the LiveKit Agents quickstart is the place to start, and it needs API keys for your STT, LLM and TTS providers.
:::

## Dig deeper

Our [research notes on voice, LLMOps and inference](lesson:research/voice-llmops-inference) list every page we read, what we could not confirm, and a laptop exercise for each topic.

:::check What problem does a TURN server solve?
When two devices cannot connect directly, for example behind strict firewalls, TURN relays their traffic so the call still works.
:::
