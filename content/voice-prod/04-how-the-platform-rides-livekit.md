---
title: How the platform rides LiveKit
summary: One phone call from ring to hang-up, through a LiveKit room. Where the audio changes format, which webhook moves the call row, and the LiveKit mistakes we only found on real calls.
time: 25 min
---

This lesson assumes you have read the LiveKit track, starting with [what LiveKit is](lesson:livekit/what-livekit-is). It does not explain the basics again. For those, see [rooms, participants, tracks](lesson:livekit/rooms-participants-tracks), [tokens and grants](lesson:livekit/tokens-and-grants), [agent server and dispatch](lesson:livekit/agent-server-and-dispatch), [webhooks and events](lesson:livekit/webhooks-and-events) and [egress recording](lesson:livekit/egress-recording).

A phone carrier knows none of LiveKit's nouns. It sends 8 kHz audio over a WebSocket or over SIP, and it expects the same back. Your billing, your customer's webhook and your recording all hang off a database row that LiveKit has never heard of. This lesson joins the two. It follows one call through the platform and names the piece that does each step.

## One room per call

Every call gets its own room. The caller and the agent are its two participants. The recorder joins as a third when recording is on. Nothing is shared between calls, so one stuck call cannot leak audio into another.

How the caller gets into the room depends on the door (see [two doors](lesson:voice-prod/two-doors-sip-and-websocket)).

On a WebSocket call, the media bridge joins the room as an ordinary participant named `pstn-<call_id>`. Its token grants join, publish and subscribe for that one room, and no data messages. It also puts the carrier name, direction and phone numbers in participant attributes. It publishes one audio track, with source "microphone", at the carrier's own rate of 8 kHz. It receives every track in the room but forwards only audio from the `AGENT` participant to the carrier. For an inbound call, the bridge's join is what creates the room. For an outbound call, call orchestration creates the room before dialing, so the agent can set up while the phone rings.

On a SIP call, livekit-sip answers the carrier and adds the caller as a participant of kind `SIP`. A dispatch rule picks the room ([source](https://docs.livekit.io/telephony/accepting-calls/dispatch-rule.md)). For outbound SIP, orchestration calls `CreateSIPParticipant` on an outbound trunk. The platform does not use this door on AWS, because SIP needs public UDP ports.

From the agent's side the two doors look the same. It sees one remote participant with one audio track.

## Where the audio changes shape

<figure>
<svg viewBox="0 0 980 290" role="img" aria-labelledby="t-lkpath d-lkpath">
  <title id="t-lkpath">The media path of one call, with formats on each hop</title>
  <desc id="d-lkpath">The carrier sends µ-law or PCM16 at 8 kHz to the media bridge, or G.711 over RTP to livekit-sip. Both publish into the LiveKit SFU room. The bridge's SDK encodes to Opus at 48 kHz. The SFU forwards Opus to the agent, which runs VAD at 16 kHz and STT, then the LLM, then TTS. TTS audio goes back as Opus 48 kHz through the SFU to the bridge, which sends 8 kHz frames to the carrier.</desc>
  <defs><marker id="ah-lkpath" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g text-anchor="middle">
    <rect class="box" x="16" y="40" width="120" height="200" rx="10"/>
    <text x="76" y="134" font-size="15">Carrier</text>
    <text x="76" y="154" font-size="12" class="small">phone network</text>
    <rect class="box" x="270" y="40" width="170" height="110" rx="10"/>
    <text x="355" y="66" font-size="14">Media bridge</text>
    <text x="355" y="88" font-size="12" class="small">pstn-&lt;call_id&gt;</text>
    <text x="355" y="110" font-size="12" class="small">µ-law ↔ PCM16 8k</text>
    <text x="355" y="130" font-size="12" class="small">SDK: 8k ↔ 48k Opus</text>
    <rect class="box" x="270" y="180" width="170" height="60" rx="10"/>
    <text x="355" y="206" font-size="14">livekit-sip</text>
    <text x="355" y="226" font-size="12" class="small">SIP signaling, RTP</text>
    <rect class="box hot" x="560" y="40" width="150" height="200" rx="10"/>
    <text x="635" y="128" font-size="15">LiveKit SFU</text>
    <text x="635" y="148" font-size="12" class="small">one room per call</text>
    <text x="635" y="166" font-size="12" class="small">forwards, no decode</text>
    <text x="877" y="30" font-size="12" class="small">Agent job (AgentSession)</text>
    <rect class="box" x="790" y="40" width="174" height="200" rx="10"/>
    <rect class="box" x="802" y="56" width="150" height="44" rx="8"/><text x="877" y="83" font-size="13">VAD 16k + STT</text>
    <rect class="box" x="802" y="118" width="150" height="44" rx="8"/><text x="877" y="145" font-size="13">LLM</text>
    <rect class="box" x="802" y="180" width="150" height="44" rx="8"/><text x="877" y="199" font-size="13">TTS</text><text x="877" y="216" font-size="11" class="small">provider's own rate</text>
  </g>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="201" y="67">µ-law or PCM16 8k</text>
    <text x="201" y="117">same, 20 ms frames</text>
    <text x="498" y="67">Opus 48k</text>
    <text x="498" y="117">Opus 48k</text>
    <text x="201" y="192">G.711 8k, RTP</text>
    <text x="498" y="192">room track</text>
    <text x="750" y="70">Opus 48k</text>
    <text x="752" y="194">Opus 48k</text>
  </g>
  <path class="arrow" d="M136 75 H266" marker-end="url(#ah-lkpath)"/>
  <path class="arrow" d="M266 125 H140" marker-end="url(#ah-lkpath)"/>
  <path class="arrow" d="M440 75 H556" marker-end="url(#ah-lkpath)"/>
  <path class="arrow" d="M556 125 H444" marker-end="url(#ah-lkpath)"/>
  <path class="arrow" d="M136 200 H266" marker-end="url(#ah-lkpath)"/>
  <path class="arrow" d="M440 200 H556" marker-end="url(#ah-lkpath)"/>
  <path class="arrow" d="M556 228 H444" marker-end="url(#ah-lkpath)"/>
  <path class="arrow" d="M266 228 H140" marker-end="url(#ah-lkpath)"/>
  <path class="arrow" d="M710 78 H798" marker-end="url(#ah-lkpath)"/>
  <path class="arrow" d="M798 202 H714" marker-end="url(#ah-lkpath)"/>
  <path class="arrow" d="M877 100 V114" marker-end="url(#ah-lkpath)"/>
  <path class="arrow" d="M877 162 V176" marker-end="url(#ah-lkpath)"/>
  <text x="490" y="275" font-size="13" class="small" text-anchor="middle">Top: the WebSocket door. Bottom: the SIP door. The STT input rate depends on the plugin; we did not measure it.</text>
</svg>
<figcaption>Codecs change at the edges. The SFU in the middle forwards Opus without decoding it.</figcaption>
</figure>

Follow the caller's voice left to right:

1. Twilio and Vobiz send base64 µ-law, 160 bytes per 20 ms frame. Ozonetel sends raw PCM16 in 10 ms packets. All of it is 8 kHz.
2. The bridge decodes µ-law to PCM16 with a lookup table. It does not resample. It hands 8 kHz frames to the LiveKit SDK's audio source.
3. The SDK sends the track as Opus. Opus in WebRTC always uses a 48 kHz RTP clock ([RFC 7587](https://datatracker.ietf.org/doc/html/rfc7587)).
4. The SFU forwards the packets to the agent. It does not decode them ([mesh, MCU, SFU](lesson:livekit/mesh-mcu-sfu)).
5. The agent decodes. The platform runs Silero VAD at 16 kHz by default. The STT plugin gets the audio in whatever form it wants.

The agent's reply goes right to left. TTS audio is published as the agent's track. The bridge subscribes with `rtc.AudioStream(track, sample_rate=8000)`, so the frames it reads are already 8 kHz ([AudioStream](https://docs.livekit.io/reference/python/livekit/rtc/audio_stream.html)). LiveKit hands over 10 ms frames, and a small chunker joins them into the 20 ms frames the carrier expects. The bridge forwards each frame as it arrives. The agent's own audio source already paces playout in real time, so the bridge needs no timer.

## The call row follows the webhooks

LiveKit does not know about calls. Call orchestration keeps a `Call` row in Postgres and moves it with LiveKit webhooks. The handler checks the webhook signature, then:

- `room_started` and `participant_joined` run the same function. If a row exists for the room, it flips `queued` or `ringing` to `active`, but only when the joiner is a caller kind (`STANDARD`, `SIP` or `BRIDGE`). The agent's join and the recorder's join do not count. If no row exists, it builds one from room metadata (web calls) or from the SIP participant's attributes (inbound SIP). If it has neither, it waits for the next event.
- `room_finished` marks the row `completed`, unless it is already completed or failed.
- `track_published` is ignored.

Every branch reads before it writes. A repeated or late webhook changes nothing, so the handler is **idempotent**: running it twice gives the same result as once. That matters because LiveKit retries webhooks.

Recording hangs off the event bus. When orchestration publishes `call.started`, the recording service starts an audio-only room composite egress that uploads to S3 or MinIO. On `call.ended` it stops the egress. LiveKit then sends `egress_updated` and `egress_ended` to the recording service's own webhook URL, which marks the recording row complete or failed. Once the call ends, a webhook dispatcher sends the customer a signed `call.ended` webhook.

Hang-up runs the same path from the other end. When the caller hangs up, the bridge calls `DeleteRoom`. That disconnects the agent, the job ends, and `room_finished` completes the row. When the agent ends the call, the bridge sees the agent leave and hangs up the carrier leg through the carrier's API.

<figure>
<svg viewBox="0 0 940 500" role="img" aria-labelledby="t-lkseq d-lkseq">
  <title id="t-lkseq">Lifecycle of one inbound WebSocket call</title>
  <desc id="d-lkseq">Sequence diagram with lifelines for carrier, bridge, LiveKit, agent, orchestration, recording and customer. The carrier webhook leads to a ticket and a WebSocket start. The bridge joins, LiveKit sends room_started and participant_joined, the call row goes active, the agent is dispatched, recording starts, the agent greets, turns follow, the caller hangs up, the bridge deletes the room, room_finished ends the call row, egress_ended updates the recording row, and the customer gets a call.ended webhook.</desc>
  <defs><marker id="ah-lkseq" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="13" text-anchor="middle">
    <rect class="box" x="4" y="14" width="112" height="32" rx="8"/><text x="60" y="35">Carrier</text>
    <rect class="box" x="134" y="14" width="112" height="32" rx="8"/><text x="190" y="35">Bridge</text>
    <rect class="box hot" x="274" y="14" width="112" height="32" rx="8"/><text x="330" y="35">LiveKit</text>
    <rect class="box" x="414" y="14" width="112" height="32" rx="8"/><text x="470" y="35">Agent</text>
    <rect class="box" x="554" y="14" width="112" height="32" rx="8"/><text x="610" y="35">Orchestration</text>
    <rect class="box" x="694" y="14" width="112" height="32" rx="8"/><text x="750" y="35">Recording</text>
    <rect class="box" x="820" y="14" width="100" height="32" rx="8"/><text x="870" y="35">Customer</text>
  </g>
  <g class="arrow" stroke-dasharray="3 5">
    <path d="M60 46 V492"/><path d="M190 46 V492"/><path d="M330 46 V492"/><path d="M470 46 V492"/><path d="M610 46 V492"/><path d="M750 46 V492"/><path d="M870 46 V492"/>
  </g>
  <g font-size="12" text-anchor="middle">
    <text x="125" y="78">1 call webhook</text>
    <text x="125" y="106">2 stream URL + ticket</text>
    <text x="125" y="134">3 WS start, ticket</text>
    <text x="260" y="162">4 join as pstn-&lt;id&gt;</text>
    <text x="470" y="190">5 room_started, participant_joined</text>
    <text x="400" y="218">6 job dispatched</text>
    <text x="680" y="246">7 call.started → egress</text>
    <text x="540" y="274">8 look up Call row</text>
    <text x="265" y="302">9 greeting via SFU and bridge</text>
    <text x="265" y="330">10 turns, both ways</text>
    <text x="125" y="358">11 hang-up</text>
    <text x="260" y="386">12 DeleteRoom</text>
    <text x="470" y="414">13 room_finished → Call ended</text>
    <text x="540" y="442">14 egress_ended → recording row</text>
    <text x="740" y="470">15 call.ended webhook</text>
  </g>
  <path class="arrow" d="M60 84 H186" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M190 112 H64" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M60 140 H186" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M190 168 H326" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M330 196 H606" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M330 224 H466" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M610 252 H746" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M470 280 H606" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M470 308 H64" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M64 336 H466" marker-start="url(#ah-lkseq)" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M60 364 H186" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M190 392 H326" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M330 420 H606" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M330 448 H746" marker-end="url(#ah-lkseq)"/>
  <path class="arrow" d="M610 476 H866" marker-end="url(#ah-lkseq)"/>
</svg>
<figcaption>One inbound WebSocket call. Steps 5 and 6 race each other, and that race is the first gotcha below.</figcaption>
</figure>

## The toy, read as a call

`code/voice-prod/room_model.py` fakes a room in about 80 lines. It has tokens that name one room, publish and subscribe, and the webhooks a call produces, but no audio. Run `python3 code/voice-prod/room_model.py` and it prints the same story in miniature:

```text
webhook -> room_started        {'room': 'call-42'}
webhook -> participant_joined  {'identity': 'pstn-42'}
webhook -> track_published     {'identity': 'pstn-42', 'track': 'caller-audio'}
webhook -> participant_joined  {'identity': 'agent'}
    [sfu] agent now receives pstn-42/caller-audio (packets forwarded, not decoded)
webhook -> track_published     {'identity': 'agent', 'track': 'agent-audio'}
    [sfu] pstn-42 now receives agent/agent-audio (packets forwarded, not decoded)
rejected: token is for room call-7
webhook -> participant_left    {'identity': 'pstn-42'}
webhook -> participant_left    {'identity': 'agent'}
webhook -> room_finished       {'room': 'call-42'}
           call rows: {'42': 'in-progress'} -> mark ended, start recording upload
```

Line two is the bridge joining. In production that is the moment the row goes `active`. The toy keys its row off the `pstn-` prefix; the real handler checks the participant kind. Line four is the agent joining, which must not activate anything. The `[sfu]` lines are the two subscriptions in the media diagram. The last line is `room_finished`: the row is marked ended, and the recorder's own webhook arrives separately.

:::try
In the toy, the agent joins after the bridge. Move the two `room.join` and `room.publish` lines for `agent` above the `pstn-42` ones and predict the output. We ran it. The agent publishes into an empty room, and nobody receives `agent-audio` until `pstn-42` joins and picks it up as a late joiner. The call row still comes from the `pstn-` join, so it ends up the same. In the real platform, an agent that joins first is the normal outbound case. That is why the handler only activates the row on a caller-kind join.
:::

## What broke, and what is still open

:::warn Gotcha from the platform
The agent races the call row. The worker has no `agent_name`, so LiveKit dispatches a job the moment any room is created. That job may connect before call orchestration has handled `room_started` or `participant_joined`. If the row is not there yet, the agent logs "no call row for room" and exits, and the caller hears nothing. The lookup runs alongside `ctx.connect()` to save time, which makes the race tighter. Outbound calls avoid it by writing a `queued` row before creating the room or dialing. For outbound SIP, writing the row first was itself a fix: dial first, and the webhook could insert its own row, misread the outbound leg as inbound, and then the real insert failed on the unique room name.
:::

The other LiveKit lessons from real calls:

- The missing webhook block. Without `webhook:` in the server config, no call row ever appeared ([webhooks and events](lesson:livekit/webhooks-and-events)).
- The local egress webhook gap. The cloud config is rendered with two webhook URLs, orchestration and recording, and each handler ignores events it does not own. The local config lists only orchestration. Locally, `egress_ended` never reaches the recording service, so recording rows never finish.
- Outbound silence. By default the agent waits for the user to speak first. Someone answering a phone waits for the caller to speak. Both sides sat in silence until the silence timeout hung up, 10 to 16 seconds in. The fix is to speak first: `session.say()` with a fixed first message, or `generate_reply()`.
- The greeting that got cut off. Callees say "hello" as they pick up. That cut the greeting off, and the caller heard silence, then a reply to their own "hello" about 3 seconds later. The first message is now not interruptible by default. While it plays, the SDK drops caller audio. Before greeting, the agent also waits up to 1.5 s for the caller to subscribe to its track, so the first word is not clipped.
- AMD started too early. Answering-machine detection starts a 20 s budget the moment it is armed. Outbound rooms are created while the phone rings. When AMD was armed at that point, it spent its budget on ringing and returned "uncertain" before voicemail picked up. It now starts only after the bridge's participant joins. No audio is lost, since none flows before that.

:::note What the docs would have told us
Every bug above has a docs page that covers it. The team hadn't read them.

- **The agent in every room.** The docs say automatic dispatch "is not recommended for most applications". With no `agent_name`, the agent is sent to every new room, and no metadata comes with it ([agent dispatch](https://docs.livekit.io/agents/server/agent-dispatch)). See [agent server and dispatch](lesson:livekit/agent-server-and-dispatch).
- **No call row.** On a self-hosted server, "webhooks can be enabled by setting the `webhook` section in your config", with a signing API key and a list of URLs ([webhooks](https://docs.livekit.io/intro/basics/rooms-participants-tracks/webhooks-events)). See [webhooks and events](lesson:livekit/webhooks-and-events).
- **The recording call.** `StartRoomCompositeEgress` is deprecated. The replacement is `StartEgress` with a `TemplateSource`, which needs server v1.13.5 or later when self-hosted ([egress API](https://docs.livekit.io/reference/other/egress/api)). See [egress recording](lesson:livekit/egress-recording).
- **Outbound silence.** For outbound calls the docs say to call `wait_for_participant` with the SIP participant's identity before starting the session ([job lifecycle](https://docs.livekit.io/agents/server/job)). Then the agent speaks first with `say()` or `generate_reply()`. See [agent server and dispatch](lesson:livekit/agent-server-and-dispatch) and [tools, tasks and workflows](lesson:livekit/tools-tasks-and-workflows).
- **AMD armed too early.** livekit-agents has AMD built in. You open it before creating the SIP participant and pass `participant_identity`, "so AMD's timers wait for that specific participant's audio track" ([AMD](https://docs.livekit.io/telephony/features/answering-machine-detection)). That is the platform's fix, already in the SDK. See [phone features](lesson:livekit/phone-features).
:::

:::note Version gap
The platform pins livekit-agents 1.6.8. It builds its worker with `WorkerOptions`, loads models in `prewarm_fnc`, and passes flat turn arguments. The current docs target 1.8, with `AgentServer`, `setup_fnc` and `TurnHandlingOptions`. The old names still run on 1.8 with deprecation warnings. [Cloud vs self-hosted, and upgrading](lesson:livekit/cloud-vs-self-hosted-and-upgrades) maps one to the other.
:::

:::note What we did not test
The flow, field names and fixes here were read from the platform's code and config, plus the LiveKit docs linked above. We did not capture packets or measure sample rates. The claim that the SDK turns 8 kHz frames into 48 kHz Opus, and back, is what the platform relies on. The `AudioStream` reference shows a `sample_rate` parameter but does not spell out resampling. We also did not check how livekit-sip encodes its track, or what rate each STT plugin uses. `room_model.py` is a toy. It has no real JWTs, no media and no network, and its webhooks fire inline instead of being retried.
:::

:::say
Each call is one room; the bridge and the agent are its two participants; the webhooks, not the media, move the call row, so the webhooks must be configured, verified and idempotent.
:::

:::check Why does the webhook handler ignore the agent's `participant_joined` when deciding a call is active?
On outbound calls the room and the agent exist while the phone is still ringing. If the agent's join counted, a call nobody answered would show as active and start recording. Only a caller-kind join (`STANDARD`, `SIP` or `BRIDGE`) means a human is on the line.
:::

:::check The bridge publishes 8 kHz audio. Who turns it into 48 kHz, and does the SFU ever decode it?
The LiveKit SDK inside the bridge encodes it to Opus, whose RTP clock is 48 kHz. The SFU only forwards packets. The agent's SDK decodes them.
:::
