---
title: Phone features
summary: The things phone calls need that browser calls don't. Keypad tones, answering machine detection, cold and warm transfers, TLS and SRTP, Twilio without a trunk, and a map from SIP error codes to causes. With notes on what breaks when you self-host.
time: 25 min
---

Your agent answers the phone and talks well. Then the real requests come in. "Press 1 for billing." "Don't talk to voicemail." "Hand angry callers to a person." "Security wants the calls encrypted." And at 2 a.m. a call fails with `486` and nobody knows what that means. This lesson covers each of these, and says where self-hosting changes the answer.

Everything here builds on [SIP fundamentals](lesson:livekit/sip-fundamentals) and the lab trunks from [self-hosted SIP](lesson:livekit/self-hosted-sip).

## DTMF: keypad tones

**DTMF** (dual-tone multi-frequency) is the tone a keypad makes. On SIP it travels as RTP with the `telephone-event/8000` payload, as event codes rather than sound ([DTMF](https://docs.livekit.io/telephony/features/dtmf)). The lab call offered it as payload type 101, and LiveKit kept it in the answer. Codes 0 to 9 are the digits, `*` is 10 and `#` is 11 ([RFC 4733](https://datatracker.ietf.org/doc/html/rfc4733#section-3.2)).

```python
await local_participant.publish_dtmf(code=1, digit='1')    # any participant can send; the SIP side plays it
await local_participant.publish_dtmf(code=11, digit='#')

@room.on("sip_dtmf_received")
def dtmf_received(dtmf: rtc.SipDTMF):
    logging.info(f"DTMF from {dtmf.participant.identity}: {dtmf.code} / {dtmf.digit}")
```

The Agents framework adds two helpers. `AgentSession(ivr_detection=True)` detects an **IVR** (a "press 1 for…" phone menu) and lets the agent answer it with tones. The installed 1.8.11 source defaults it to `False`. **`GetDtmfTask`** (in `livekit.agents.beta.workflows`) collects digits from keypresses or speech, for example an account number ([GetDtmfTask](https://docs.livekit.io/agents/prebuilt/tasks/get-dtmf)). For outbound calls that must dial an extension, `CreateSIPParticipant` takes `dtmf`, where `w` adds a 0.5 s pause ([SIP API](https://docs.livekit.io/reference/telephony/sip-api#createsipparticipant)).

## Answering machine detection

On an outbound call, voicemail answers with `200 OK`, the same as a person. So `wait_until_answered` succeeds and no error fires. **AMD** listens to the first utterance, classifies it, and holds the agent's speech until it decides, so the agent doesn't talk over the greeting ([AMD](https://docs.livekit.io/telephony/features/answering-machine-detection)). It runs once, not for the whole call. The five results:

| Result | Meaning | Usual action |
|---|---|---|
| `human` | a person | talk |
| `uncertain` | can't tell, or silence | treat as human |
| `machine-ivr` | a phone menu | IVR navigation (Python, when AMD's own `ivr_detection` is on, the default) |
| `machine-vm` | voicemail that takes messages | leave a message, then `ctx.shutdown()` |
| `machine-unavailable` | mailbox full or unreachable | hang up |

Open `AMD` (from `livekit.agents`) before you dial, so it is ready when audio starts:

```python
async with AMD(session, participant_identity=participant_identity) as detector:
    await ctx.api.sip.create_sip_participant(api.CreateSIPParticipantRequest(
        sip_trunk_id=trunk_id, sip_call_to=phone_number, room_name=ctx.room.name,
        participant_identity=participant_identity, wait_until_answered=True))
    await ctx.wait_for_participant(identity=participant_identity)
    result = await detector.execute()
    if result.category == "machine-vm":
        ...
```

Two paths race. A fast heuristic says `human` when speech is shorter than `human_speech_threshold` (2.5 s) and followed by `human_silence_threshold` (0.5 s) of silence. An LLM classifies longer speech after `machine_silence_threshold` (1.5 s) of silence. With no speech for `no_speech_threshold` (10 s), the result is `uncertain`.

<figure>
<svg viewBox="0 0 800 330" role="img" aria-labelledby="t-pfamd d-pfamd">
  <title id="t-pfamd">How answering machine detection decides</title>
  <desc id="d-pfamd">After the call is answered, AMD waits for the first utterance. If there is no speech for 10 seconds the result is uncertain. Speech under 2.5 seconds followed by 0.5 seconds of silence goes to the fast heuristic, which returns human. Longer speech followed by 1.5 seconds of silence goes to the LLM classifier, which returns human, machine-ivr, machine-vm, machine-unavailable or uncertain. Human and uncertain continue the conversation, machine-ivr starts IVR navigation, machine-vm leaves a message and machine-unavailable hangs up.</desc>
  <defs><marker id="ah-pfamd" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="10" y="130" width="150" height="60" rx="10"/><text x="85" y="156">Call answered</text><text x="85" y="176" font-size="12" class="small">agent speech paused</text>
    <rect class="box" x="230" y="30" width="180" height="56" rx="10"/><text x="320" y="54">Fast heuristic</text><text x="320" y="73" font-size="12" class="small">speech &lt; 2.5 s, 0.5 s quiet</text>
    <rect class="box hot" x="230" y="132" width="180" height="56" rx="10"/><text x="320" y="156">LLM classifier</text><text x="320" y="175" font-size="12" class="small">longer speech, 1.5 s quiet</text>
    <rect class="box" x="230" y="234" width="180" height="56" rx="10"/><text x="320" y="258">No speech</text><text x="320" y="277" font-size="12" class="small">10 s, nothing heard</text>
    <rect class="box" x="490" y="16" width="290" height="48" rx="8"/><text x="635" y="45">human / uncertain → talk</text>
    <rect class="box" x="490" y="88" width="290" height="48" rx="8"/><text x="635" y="117">machine-ivr → IVR navigation</text>
    <rect class="box" x="490" y="160" width="290" height="48" rx="8"/><text x="635" y="189">machine-vm → message, shutdown</text>
    <rect class="box" x="490" y="232" width="290" height="48" rx="8"/><text x="635" y="261">machine-unavailable → hang up</text>
  </g>
  <path class="arrow" d="M160 150 L226 66" marker-end="url(#ah-pfamd)"/>
  <path class="arrow" d="M160 160 H226" marker-end="url(#ah-pfamd)"/>
  <path class="arrow" d="M160 172 L226 256" marker-end="url(#ah-pfamd)"/>
  <path class="arrow" d="M410 56 L486 42" marker-end="url(#ah-pfamd)"/>
  <path class="arrow" d="M410 150 L486 46" marker-end="url(#ah-pfamd)"/>
  <path class="arrow" d="M410 158 L486 114" marker-end="url(#ah-pfamd)"/>
  <path class="arrow" d="M410 164 L486 184" marker-end="url(#ah-pfamd)"/>
  <path class="arrow" d="M410 172 L486 252" marker-end="url(#ah-pfamd)"/>
  <path class="arrow" d="M410 258 L486 50" stroke-dasharray="5 5" marker-end="url(#ah-pfamd)"/>
  <text x="400" y="320" font-size="12" class="small" text-anchor="middle">Whichever path decides first wins. Thresholds are the Python defaults in detection_options.</text>
</svg>
<figcaption>AMD runs once, at the start of the call. Only the LLM path can return a machine result.</figcaption>
</figure>

## Transfers: cold and warm

A **cold transfer** hands the caller to another number and leaves. `TransferSIPParticipant` makes LiveKit send a **SIP REFER** ("call this address instead") through the trunk. The provider connects the caller, and the caller leaves the room ([call forwarding](https://docs.livekit.io/telephony/features/transfers/cold)). The provider must allow REFER. On Twilio you enable Call Transfer on the trunk. Plivo allows it by default. On Telnyx, REFER must be enabled for your account. `ringing_timeout` (default 30 s) caps the wait. If nobody answers, the request fails and the caller stays in the room.

A **warm transfer** briefs a human first ([warm transfer](https://docs.livekit.io/telephony/features/transfers/warm)). The caller goes on hold. The manager is dialed into a private consultation room. An agent summarizes the call. Then the manager is moved into the caller's room. **`WarmTransferTask`** (Python only, beta, in `livekit.agents.beta.workflows`) runs the whole flow. You can also build it by hand with two agent sessions.

<figure>
<svg viewBox="0 0 800 300" role="img" aria-labelledby="t-pfxfer d-pfxfer">
  <title id="t-pfxfer">Cold transfer compared with warm transfer</title>
  <desc id="d-pfxfer">Cold: the agent calls TransferSIPParticipant, livekit-sip sends SIP REFER to the provider, and the provider connects the caller to the new number. The caller leaves the room. Warm: the caller waits on hold in the call room. The manager is dialed into a consultation room, where a transfer agent summarizes the call. Then MoveParticipant moves the manager into the call room. MoveParticipant is Cloud-only.</desc>
  <defs><marker id="ah-pfxfer" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="10" y="26" font-size="15" font-weight="700">Cold (SIP REFER)</text>
  <text x="420" y="26" font-size="15" font-weight="700">Warm (agent briefs a human first)</text>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="10" y="50" width="170" height="70" rx="10"/><text x="95" y="80">Call room</text><text x="95" y="100" font-size="12" class="small">caller + agent</text>
    <rect class="box hot" x="220" y="50" width="160" height="70" rx="10"/><text x="300" y="80">SIP provider</text><text x="300" y="100" font-size="12" class="small">must allow REFER</text>
    <rect class="box" x="120" y="200" width="170" height="60" rx="10"/><text x="205" y="235">New number</text>
    <rect class="box" x="420" y="50" width="170" height="70" rx="10"/><text x="505" y="80">Call room</text><text x="505" y="100" font-size="12" class="small">caller on hold</text>
    <rect class="box" x="620" y="50" width="170" height="70" rx="10"/><text x="705" y="80">Consult room</text><text x="705" y="100" font-size="12" class="small">agent briefs manager</text>
    <rect class="box hot" x="620" y="200" width="170" height="60" rx="10"/><text x="705" y="235">Manager (dialed)</text>
  </g>
  <g font-size="12" class="small" text-anchor="middle">
    <path class="arrow" d="M180 85 H216" marker-end="url(#ah-pfxfer)"/><text x="200" y="140">REFER</text>
    <path class="arrow" d="M300 120 L240 196" marker-end="url(#ah-pfxfer)"/><text x="300" y="170">connects caller</text>
    <path class="arrow" stroke-dasharray="5 5" d="M95 120 L170 196" marker-end="url(#ah-pfxfer)"/><text x="80" y="170">caller leaves room</text>
    <path class="arrow" d="M705 196 V124" marker-end="url(#ah-pfxfer)"/><text x="745" y="165">1. dial in</text>
    <path class="arrow" d="M620 85 H594" marker-end="url(#ah-pfxfer)"/>
    <text x="560" y="165">2. MoveParticipant</text>
    <text x="560" y="182">(Cloud-only)</text>
  </g>
</svg>
<figcaption>Cold transfer hands the call to the phone network. Warm transfer keeps it in LiveKit and moves the manager between rooms.</figcaption>
</figure>

:::warn Warm transfer moves the manager with an API that self-hosted doesn't have
The manual flow's step 3 calls `MoveParticipant`. The installed `WarmTransferTask` source calls `job_ctx.api.room.move_participant(...)` too. On the lab, `MoveParticipant` returned "unknown: not implemented", because it is Cloud-only. So on a self-hosted server the warm transfer should fail at the moment the manager is moved. We didn't run it, but both pieces are verified. Self-hosted options: a cold transfer through REFER, or dial the manager straight into the caller's room with `CreateSIPParticipant` and brief them there. You would need to control the caller's subscriptions so they don't hear the briefing, and we haven't tested that.
:::

## Secure trunking: TLS and SRTP

By default SIP is plain text and RTP is unencrypted. **Secure trunking** uses TLS for signaling (port 5061) and **SRTP** for media ([secure trunking](https://docs.livekit.io/telephony/features/secure-trunking)). It takes three steps: turn it on at the provider, use `;transport=tls` URIs or port 5061, and set media encryption on the trunk or call. Use the `encryption` field inside `media`: `SIP_MEDIA_ENCRYPT_DISABLE` (default), `_ALLOW` or `_REQUIRE`. The top-level `media_encryption` is deprecated ([SIPMediaConfig](https://docs.livekit.io/reference/telephony/sip-api#sipmediaconfig)). Outbound trunks also need `transport: SIP_TRANSPORT_TLS`. TLS supports the secure suites in Go's `crypto/tls`. SRTP supports `AES_CM_128_HMAC_SHA1_80`, `AES_CM_128_HMAC_SHA1_32`, `AES_256_CM_HMAC_SHA1_80` and `AES_256_CM_HMAC_SHA1_32`. Changing only the port to 5061 without turning on TLS is not enough.

## Twilio without a trunk, and what is Cloud-only

The **Twilio Voice integration** uses TwiML, Twilio's XML for call handling, to forward a call as plain SIP. A `<Dial><Sip username=… password=…>` points at `sip:<number>@<your SIP endpoint>;transport=tcp`, and an inbound trunk with `--auth-user`/`--auth-pass` checks the credentials ([Twilio Voice](https://docs.livekit.io/telephony/accepting-calls/inbound-twilio)). It is ordinary SIP, so self-hosted `livekit/sip` should accept it at `<your-host>:5060`. It supports no REFER and no outbound calls.

The **Twilio Connector** (Media Streams over WebSocket) and the **WhatsApp Connector** are "available in LiveKit Cloud only" ([connectors](https://docs.livekit.io/telephony/connectors)). If you self-host and need a carrier WebSocket, you write a bridge yourself. The Voice in production track does that in [Two doors](lesson:voice-prod/two-doors-sip-and-websocket). **Region pinning** works on LiveKit Cloud's distributed SIP ([region pinning](https://docs.livekit.io/telephony/features/region-pinning)). Self-hosted, the call goes wherever your host is.

## When a call fails: the error map

From the troubleshooting guide ([troubleshooting](https://docs.livekit.io/reference/telephony/troubleshooting)):

| Symptom | Likely cause |
|---|---|
| `403 Forbidden` | wrong trunk username or password, or the provider's regional rules |
| `404` / `object cannot be found` | the trunk ID doesn't exist, or the number is invalid |
| `486 Busy Here` on inbound | no agent answered: wrong `agent_name` in the rule, worker down, or the job exited early |
| `503` on outbound | wrong `address`, such as a Telnyx subdomain instead of `sip.telnyx.com` |
| `408` | transfer: the REFER target never answered. Outbound: the far end didn't respond |
| `488 Not Acceptable Here` | no codec in common |
| connected, total silence | `c=IN IP4 0.0.0.0` (no media), `m=audio 0` (stream rejected), or RTP ports blocked |
| one-way audio | a private IP in the SDP. Self-hosted: `use_external_ip: true` |
| static or garbled audio | RTP payload type doesn't match the SDP, e.g. `PT=8` when `PT=0` was agreed |

The guide's thresholds for a healthy call: packet loss under 1% (over 3% breaks up), mean jitter under 5 ms (over 20 ms is choppy), one-way latency under 150 ms (over 300 ms and people talk over each other). Its first stop is the Cloud dashboard and its PCAPs. Self-hosted, use `docker compose logs sip`, `lk room participants list <room>` for the `sip.*` attributes, and `sip.callIDFull` to find the call in your provider's logs.

:::note Self-hosted vs Cloud
DTMF, cold transfer, TLS/SRTP and the Twilio Voice (TwiML) path are SIP features and should work self-hosted. AMD works, but its defaults (`google/gemini-3.1-flash-lite`, `cartesia/ink-whisper`) go through LiveKit Inference, which is Cloud-only. Without Inference, it "falls back to the session's own LLM" and the session's STT transcripts. Pass `llm=` and `stt=` explicitly, and expect a compatibility warning for models outside the evaluated list. Warm transfer needs `MoveParticipant` (Cloud-only). Connectors, region pinning, the telephony dashboard and its PCAP downloads are Cloud-only.
:::

:::tip CLI
From the docs' telephony CLI page ([CLI: telephony](https://docs.livekit.io/reference/developer-tools/livekit-cli/telephony)):

- `lk sip participant transfer --room my-sip-room --identity sip-caller --to tel:+15105550100 --play-dialtone`
- `lk sip outbound create outbound-trunk.json --transport tls`
- `lk sip outbound update --id <trunk-id> --transport tls`
- `--media-enc require` on trunk or participant `create`/`update` for SRTP
- `lk sip inbound create inbound-trunk.json --auth-user <sip_trunk_username> --auth-pass <sip_trunk_password>` for the TwiML path
:::

:::try
Send a keypress from `sip_call.py`. After the tone, send three RTP packets with payload type 101 and one fixed timestamp. Each payload is `struct.pack("!BBH", 5, 10, 800)` (event 5, volume 10, duration 800), and the last uses `0x80 | 10` to set the end bit. Add `@room.on("sip_dtmf_received")` to a script that joins the call room. Predict the `code` and `digit` it prints, then run it. We haven't run this.
:::

:::note What we did not test
None of this lesson ran on the lab: not DTMF, AMD, transfers, TLS/SRTP or TwiML. The only lab evidence is that `telephone-event` was accepted in the SDP and that `MoveParticipant` is not implemented self-hosted. The warm transfer failure is inferred from that and the package source. We don't know how to configure TLS certificates for self-hosted `livekit/sip`, because the SIP server page doesn't cover it.
:::

:::say
Phone features are SIP features: DTMF rides RTP, transfers ride REFER, encryption is TLS plus SRTP, and anything that moves people between rooms or uses Inference needs Cloud or a workaround.
:::

:::check An outbound call reaches voicemail. Why doesn't `wait_until_answered` raise an error, and what catches it?
Voicemail answers with `200 OK`, the same as a person, so the call counts as answered. AMD catches it by classifying the greeting as `machine-vm`.
:::

:::check Inbound calls ring for a while and then fail with 486. The worker is running. What do you check?
That the dispatch rule's `room_config.agents[].agent_name` matches the `agent_name` the worker registered. If no agent subscribes to the caller, the trunk's `ringing_timeout` expires and LiveKit sends `486 Busy Here`.
:::

Next: [Recording calls with egress](lesson:livekit/egress-recording)
