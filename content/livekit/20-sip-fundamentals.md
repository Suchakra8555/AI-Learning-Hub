---
title: SIP fundamentals
summary: How a phone call becomes a participant in a LiveKit room. The SIP handshake, SDP and codecs, RTP, media timeouts and the SIP participant, walked through with a real call placed into the lab by a 90-line script.
time: 25 min
---

Your agent works in the browser. Then someone asks for a phone number, and a new set of words shows up: trunk, INVITE, PCMU, 180 Ringing, BYE. When a phone call fails, the error is usually a three-digit SIP code in a log you have never read. This lesson walks one real call into the lab, packet by packet, so those words map to things you have seen.

If SIP and RTP are new, [WebRTC, phone lines, and LiveKit](lesson:voice/webrtc-sip-livekit) gives the short version. [WebRTC from the wire up](lesson:livekit/webrtc-from-the-wire-up) covers SDP and RTP for the browser side.

## Where a phone call comes from

**SIP** (Session Initiation Protocol, [RFC 3261](https://datatracker.ietf.org/doc/html/rfc3261)) sets calls up and tears them down. It carries no audio. The audio goes as **RTP** packets over UDP. LiveKit's primer describes the inbound path like this ([SIP primer](https://docs.livekit.io/reference/telephony/sip-primer)):

1. A person dials a number. The call enters the **PSTN** (public switched telephone network, the global phone network).
2. The PSTN routes it to the **SIP trunk** that owns the number. A trunk is a SIP account at a provider (Twilio, Telnyx, Plivo and so on) that links phone numbers to an internet address.
3. The provider sends a SIP `INVITE` to the address you configured, which is LiveKit's SIP service.
4. LiveKit creates a room, adds the caller as a participant, and your agent joins.

Outbound runs the other way. You call the SIP API, LiveKit sends the `INVITE` to the provider, the provider rings the phone, and the answer comes back as `200 OK`. On a mobile phone the network first signals "answered" over SS7 and the provider turns that into a `200 OK` (same page).

<figure>
<svg viewBox="0 0 820 250" role="img" aria-labelledby="t-sipplane d-sipplane">
  <title id="t-sipplane">Signaling path and media path of a phone call into LiveKit</title>
  <desc id="d-sipplane">A phone reaches a SIP provider through the phone network. The provider sends SIP signaling to livekit-sip on port 5060 and RTP audio to it on a UDP port range. livekit-sip talks to livekit-server through Redis and the server API, and joins the room as a WebRTC participant. The agent joins the same room over WebRTC.</desc>
  <defs><marker id="ah-sipplane" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="10" y="40" font-size="13" font-weight="700">Signaling (dashed): who calls whom, which codec, hang up</text>
  <text x="10" y="240" font-size="13" font-weight="700">Media (solid): the audio itself, 50 packets a second each way</text>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="10" y="110" width="110" height="65" rx="10"/><text x="65" y="147">Phone</text>
    <rect class="box" x="160" y="110" width="150" height="65" rx="10"/><text x="235" y="138">SIP provider</text><text x="235" y="158" font-size="12" class="small">owns the number</text>
    <rect class="box hot" x="360" y="110" width="140" height="65" rx="10"/><text x="430" y="138">livekit-sip</text><text x="430" y="158" font-size="12" class="small">a room participant</text>
    <rect class="box" x="550" y="110" width="140" height="65" rx="10"/><text x="620" y="138">livekit-server</text><text x="620" y="158" font-size="12" class="small">the room</text>
    <rect class="box" x="740" y="110" width="70" height="65" rx="10"/><text x="775" y="147">Agent</text>
  </g>
  <g font-size="12" class="small" text-anchor="middle">
    <path class="arrow" stroke-dasharray="5 5" d="M124 128 H156" marker-start="url(#ah-sipplane)" marker-end="url(#ah-sipplane)"/><text x="140" y="95">PSTN</text>
    <path class="arrow" stroke-dasharray="5 5" d="M314 128 H356" marker-start="url(#ah-sipplane)" marker-end="url(#ah-sipplane)"/><text x="335" y="95">SIP on 5060</text>
    <path class="arrow" stroke-dasharray="5 5" d="M504 128 H546" marker-start="url(#ah-sipplane)" marker-end="url(#ah-sipplane)"/><text x="525" y="95">Redis + API</text>
    <path class="arrow" stroke-dasharray="5 5" d="M694 128 H736" marker-start="url(#ah-sipplane)" marker-end="url(#ah-sipplane)"/><text x="715" y="95">join</text>
    <path class="arrow" stroke-width="3" d="M124 158 H156" marker-start="url(#ah-sipplane)" marker-end="url(#ah-sipplane)"/><text x="140" y="205">voice</text>
    <path class="arrow" stroke-width="3" d="M314 158 H356" marker-start="url(#ah-sipplane)" marker-end="url(#ah-sipplane)"/><text x="335" y="205">RTP, UDP range</text>
    <path class="arrow" stroke-width="3" d="M504 158 H546" marker-start="url(#ah-sipplane)" marker-end="url(#ah-sipplane)"/><text x="525" y="205">WebRTC</text>
    <path class="arrow" stroke-width="3" d="M694 158 H736" marker-start="url(#ah-sipplane)" marker-end="url(#ah-sipplane)"/><text x="715" y="205">WebRTC</text>
  </g>
</svg>
<figcaption>SIP and RTP stop at livekit-sip. From there on, the caller is just another WebRTC participant, so your agent code never sees SIP.</figcaption>
</figure>

## The handshake, step by step

LiveKit's handshake page names caller A and callee B ([SIP handshake](https://docs.livekit.io/reference/telephony/sip-handshake)):

- **INVITE.** A asks for a call. The headers `From` (with a tag), `To`, `Call-ID`, `Via` and `Contact` identify the dialog. The body is usually the **SDP offer**: every codec A supports, in order of preference.
- **401 or 407** (optional). B wants credentials. A sends the INVITE again with an `Authorization` header and the same `Call-ID`. This is a normal digest challenge, not a failure.
- **100 Trying.** "Got it, stop resending." Over UDP this stops retransmits.
- **180 Ringing** or **183 Session Progress.** 183 usually carries SDP and opens **early media**, audio that flows before the answer, such as a custom ringback.
- **200 OK** with the **SDP answer**: the codecs B picked. The call is now "connected".
- **ACK.** A confirms. It is mandatory, and media can flow from here.
- **BYE**, answered by `200 OK`, ends the call and frees the RTP ports.

## A real call into the lab

`code/livekit/sip_call.py` plays the phone provider. There is no provider and no phone. It sends a raw SIP INVITE over UDP to the lab's `livekit/sip` container (v1.23.0, next to livekit-server v1.13.11), waits for `200 OK`, sends `ACK`, then streams a 440 Hz tone as real **G.711 µ-law** RTP. The µ-law bytes come from `mulaw.py`, the 60-line codec from the Voice in production track ([phone audio](lesson:voice-prod/phone-audio-is-different)). The inbound trunk and dispatch rule from [the next lesson](lesson:livekit/self-hosted-sip) send the call to a new room with the echo agent in it, which plays our tone back after 300 ms.

```python
sdp = (f"v=0\r\no=- 1 1 IN IP4 {ME}\r\ns=-\r\nc=IN IP4 {ME}\r\nt=0 0\r\n"
       f"m=audio {rtp_port} RTP/AVP 0 101\r\na=rtpmap:0 PCMU/8000\r\na=rtpmap:101 telephone-event/8000\r\na=sendrecv\r\n")
sip.sendto(request("INVITE", 1, sdp), SIP_SERVER)
...
    if " 200 " in status:
        to_tag = re.search(r"^To:.*?(;tag=[^\s;]+)", msg, re.M | re.I).group(1)
        ip = re.search(r"c=IN IP4 (\S+)", msg).group(1)
        port = int(re.search(r"m=audio (\d+)", msg).group(1))
...
sip.sendto(request("ACK", 1, extra=to_tag)..., SIP_SERVER)
for i in range(250):  # 5 s: 1 s tone, then silence
    amp = 8000 if i < 50 else 0
    payload = bytes(encode_sample(int(amp * math.sin(2 * math.pi * 440 * (ts + n) / 8000))) for n in range(160))
    rtp.sendto(struct.pack("!BBHII", 0x80, 0, seq & 0xFFFF, ts, ssrc) + payload, remote)
    seq, ts = seq + 1, ts + 160
```

The RTP header is 12 bytes: version 2 (`0x80`), payload type 0 (PCMU), a sequence number, a timestamp that grows by 160 per packet (160 samples at 8 kHz is 20 ms), and a random **SSRC** that names the stream. Real output of `python sip_call.py`:

```text
 0.00s  <- SIP/2.0 100 Processing
 0.00s  <- SIP/2.0 180 Ringing
 0.49s  <- SIP/2.0 200 OK
        answer SDP: send RTP to 10.148.102.64:10060, codecs ['0 PCMU/8000', '101 telephone-event/8000']
 0.50s  -> ACK (call is up)
        <- RTP from LiveKit: payload type 0, 160 bytes, loud: our tone came back after 0.48 s
 5.50s  -> BYE, <- SIP/2.0 200 OK
```

Read it against the handshake:

- LiveKit answered `100 Processing`, where the docs say `100 Trying`. The text after a SIP code is free-form. Software matches the number.
- `180 Ringing` came at once. The `200 OK` came 0.49 s later. The docs say an inbound call rings until someone in the room subscribes to the caller's audio ([SIP participant](https://docs.livekit.io/reference/telephony/sip-participant)). So that half second covered creating the room, dispatching the echo agent and getting it subscribed.
- The answer kept PCMU and `telephone-event` (payload 101, used for keypad tones in [phone features](lesson:livekit/phone-features)). The RTP port, 10060, is inside the lab's `rtp_port: 10000-10100`.
- The tone came back as 160-byte, payload type 0 packets, 0.48 s after the first packet went out. That is the 300 ms delay set in the dispatch rule plus about 180 ms through livekit-sip, the room and the agent. The earlier dispatch test with a 500 ms delay measured 0.63 s, so the overhead is about the same.
- `10.148.102.64` is the host's private address. It worked because everything ran on one machine. [Self-hosted SIP](lesson:livekit/self-hosted-sip) explains why a real provider could never reach it.

<figure>
<svg viewBox="0 0 800 520" role="img" aria-labelledby="t-sipseq d-sipseq">
  <title id="t-sipseq">The lab call as a sequence diagram, with measured times</title>
  <desc id="d-sipseq">sip_call.py sends INVITE with an SDP offer to livekit-sip at 0.00 s. livekit-sip replies 100 Processing and 180 Ringing at once, adds the SIP participant to a new room, and the echo agent subscribes. At 0.49 s livekit-sip sends 200 OK with the SDP answer. The script sends ACK at 0.50 s. PCMU RTP flows both ways and the echoed tone arrives 0.48 s after the first packet. At 5.50 s the script sends BYE and gets 200 OK.</desc>
  <defs><marker id="ah-sipseq" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="70" y="16" width="200" height="44" rx="10"/><text x="170" y="43">sip_call.py (provider)</text>
    <rect class="box hot" x="320" y="16" width="200" height="44" rx="10"/><text x="420" y="43">livekit-sip :5060</text>
    <rect class="box" x="570" y="16" width="200" height="44" rx="10"/><text x="670" y="43">Room + echo agent</text>
  </g>
  <path class="arrow" stroke-dasharray="3 5" d="M170 60 V510"/>
  <path class="arrow" stroke-dasharray="3 5" d="M420 60 V510"/>
  <path class="arrow" stroke-dasharray="3 5" d="M670 60 V510"/>
  <g font-size="12" class="small" text-anchor="end">
    <text x="60" y="104">0.00 s</text><text x="60" y="139">0.00 s</text><text x="60" y="174">0.00 s</text>
    <text x="60" y="289">0.49 s</text><text x="60" y="324">0.50 s</text><text x="60" y="424">+0.48 s</text>
    <text x="60" y="469">5.50 s</text>
  </g>
  <g font-size="12" class="small" text-anchor="middle">
    <path class="arrow" d="M170 100 H416" marker-end="url(#ah-sipseq)"/><text x="295" y="94">INVITE + SDP offer (PCMU, 101)</text>
    <path class="arrow" d="M420 135 H174" marker-end="url(#ah-sipseq)"/><text x="295" y="129">100 Processing</text>
    <path class="arrow" d="M420 170 H174" marker-end="url(#ah-sipseq)"/><text x="295" y="164">180 Ringing</text>
    <path class="arrow" d="M420 210 H666" marker-end="url(#ah-sipseq)"/><text x="545" y="204">SIP participant joins</text>
    <path class="arrow" d="M670 245 H424" marker-end="url(#ah-sipseq)"/><text x="545" y="239">agent subscribes</text>
    <path class="arrow" d="M420 285 H174" marker-end="url(#ah-sipseq)"/><text x="295" y="279">200 OK + SDP answer, port 10060</text>
    <path class="arrow" d="M170 320 H416" marker-end="url(#ah-sipseq)"/><text x="295" y="314">ACK</text>
  </g>
  <path class="arrow" stroke-dasharray="8 4" d="M70 345 H790"/>
  <text x="790" y="365" font-size="13" font-weight="700" text-anchor="end">Media: RTP over UDP</text>
  <g font-size="12" class="small" text-anchor="middle">
    <path class="arrow" stroke-width="3" d="M174 385 H416" marker-start="url(#ah-sipseq)" marker-end="url(#ah-sipseq)"/><text x="295" y="379">PCMU, 160 bytes / 20 ms</text>
    <path class="arrow" stroke-width="3" d="M424 385 H666" marker-start="url(#ah-sipseq)" marker-end="url(#ah-sipseq)"/><text x="545" y="379">WebRTC audio</text>
    <path class="arrow" d="M420 420 H174" marker-end="url(#ah-sipseq)"/><text x="295" y="414">our tone back, payload type 0</text>
    <path class="arrow" stroke-dasharray="8 4" d="M70 440 H790"/>
    <path class="arrow" d="M170 465 H416" marker-end="url(#ah-sipseq)"/><text x="295" y="459">BYE</text>
    <path class="arrow" d="M420 495 H174" marker-end="url(#ah-sipseq)"/><text x="295" y="489">200 OK</text>
  </g>
</svg>
<figcaption>Times are from the real run. Ringing is instant. The half second before 200 OK is LiveKit getting a listener into the room.</figcaption>
</figure>

## Codecs on the phone side

The phone side has its own codec list, separate from the room's. LiveKit SIP offers **PCMU** (G.711 µ-law), **PCMA** (G.711 A-law) and **G.722** by default ([codecs](https://docs.livekit.io/reference/telephony/codecs-negotiation)). PCMU and PCMA are 8 kHz narrowband at about 64 kbps. G.722 is wideband: it carries 16 kHz audio, but its SDP line still says `G722/8000`. The docs call that "a known quirk of the SDP specification". Wideband on a phone call is **HD voice**, and the docs say Telnyx is currently the only SIP provider that supports it ([HD voice](https://docs.livekit.io/telephony/features/hd-voice)).

The `media` field on a trunk, a dispatch rule or a single call can add codecs. Set `only_listed_codecs: true` to drop the defaults. If the two sides share no codec, the call fails with `488 Not Acceptable Here` ([troubleshooting](https://docs.livekit.io/reference/telephony/troubleshooting)). An INVITE with no SDP at all (a **delayed offer**) gets `400 Bad Request` unless LiveKit support turns delayed offers on.

## Media timeouts

If no RTP arrives within 30 seconds, LiveKit hangs up with `media timeout`. Once packets have flowed, the limit is 15 seconds after the last one ([SIP primer](https://docs.livekit.io/reference/telephony/sip-primer)). Some providers send nothing during silence, so a quiet caller can trip it. The fix is `media_timeout` in the `media` config, for example `"60s"`, or comfort noise on the provider side ([media timeout](https://docs.livekit.io/reference/telephony/troubleshooting#media-timeout)).

## The SIP participant

To your agent, the caller is a normal participant with kind `SIP` and a set of `sip.*` attributes ([SIP participant](https://docs.livekit.io/reference/telephony/sip-participant)). This is the lab room during the call, printed with a `ListParticipants` call (the snippet is not saved in the repo):

```text
call-_+15550001111_4bQjEHLxq6Ht sip_+15550001111 SIP
  attributes: {'lk.sip.inviteTime': '1794131283074', 'sip.callID': 'SCL_7mFW93qtCAaa', 'sip.callIDFull': '405473c4', 'sip.callStatus': 'active', 'sip.callTag': '4c8828d9', 'sip.hostname': '127.0.0.1', 'sip.phoneNumber': '+15550001111', 'sip.ruleID': 'SDR_QBFWgicdUUyt', 'sip.trunkID': 'ST_dhoypENZSnpK', 'sip.trunkPhoneNumber': '+15105550100'}
call-_+15550001111_4bQjEHLxq6Ht agent-AJ_CFLsoaqLLyt4 AGENT
  attributes: {'lk.agent.name': 'echo', 'lk.agent_name': 'echo'}
```

- `sip.phoneNumber` is who called. `sip.trunkPhoneNumber` is the number they dialed.
- `sip.callID` (`SCL_…`) is LiveKit's ID for the call. `sip.callIDFull` is the provider's SIP `Call-ID`. Here it is `405473c4`, the random hex our script put in its INVITE. When you open a ticket with a provider, give them `callIDFull`.
- `sip.callStatus` moves through `dialing`, `ringing`, `automation` (outbound DTMF still dialing), `active` and `hangup`.
- `sip.ruleID` and `sip.trunkID` match the IDs `lk sip` printed when we created them.

When a SIP participant leaves, its `disconnect_reason` says why. `CLIENT_INITIATED` (someone hung up), `ROOM_DELETED` and `USER_REJECTED` (486 or 603) close the `AgentSession` for you. `USER_UNAVAILABLE` (408 or 480) and `SIP_TRUNK_FAILURE` (5xx) do not. For those two, your code must call `ctx.shutdown()` itself.

:::warn The caller's phone number is in the room name
The individual dispatch rule names the room `<prefix>_<caller number>_<random>`. That is why the lab room is `call-_+15550001111_…`: our prefix `call-` plus the `_` LiveKit adds. Room names go into logs and traces, and LiveKit's PII redaction does not remove them ([dispatch rule](https://docs.livekit.io/telephony/accepting-calls/dispatch-rule)). The identity `sip_+15550001111` has the number too. [The next lesson](lesson:livekit/self-hosted-sip) covers `hide_phone_number` and rules that keep the number out of names.
:::

:::note Self-hosted vs Cloud
The handshake, codecs and attributes are the same on both. LiveKit Phone Numbers, where the call skips the trunk and goes straight to LiveKit, are Cloud-only. Self-hosted, you always need a trunk from a provider and your own `livekit/sip`. HD voice "out of the box" is a Phone Numbers feature, so self-hosted you need a provider that supports G.722. Delayed offers are enabled by contacting LiveKit support. We don't know how to turn them on for a self-hosted service.
:::

:::tip CLI
The `lk` CLI (v2.19.3 in the lab) has no command that places a test call into your own server. Use `sip_call.py` for that. These show what the call used:

- `lk sip inbound list`
- `lk sip dispatch list`
- `lk room participants list <room>`, then compare the identity to the `sip_+…` pattern above
:::

:::try
In `sip_call.py`, change the offer to `m=audio {rtp_port} RTP/AVP 18` with `a=rtpmap:18 G729/8000`. LiveKit does not list G.729 as a codec. Predict the final response before you run it: `488`, a `200 OK` with no audio, or something else. Then put PCMU back, comment out the `rtp.sendto(...)` line, and raise the loop to `range(2000)` (40 s). The call is up but no RTP arrives. Predict when LiveKit ends the call, and watch `docker compose logs sip` in `code/livekit/lab/` to check.
:::

:::note What we did not test
We placed one inbound call with no authentication and no real provider. We did not see a 401/407 challenge, early media (183), G.722, PCMA, a delayed offer or a `media timeout`. The ~180 ms of overhead is from one call on one machine.
:::

:::say
SIP sets the call up, SDP picks the codec, RTP carries 20 ms of µ-law at a time, and livekit-sip turns all of it into an ordinary room participant.
:::

:::check The 200 OK arrived 0.49 s after 180 Ringing. What was LiveKit waiting for?
For someone in the room to subscribe to the caller's audio. An inbound call keeps ringing until then. In the lab that meant creating the room, dispatching the echo agent and getting it subscribed.
:::

:::check An outbound call fails with USER_UNAVAILABLE and your agent process stays in the room. Why?
`AgentSession` closes itself only for `CLIENT_INITIATED`, `ROOM_DELETED` and `USER_REJECTED`. For `USER_UNAVAILABLE` and `SIP_TRUNK_FAILURE` you have to call `ctx.shutdown()` yourself.
:::
