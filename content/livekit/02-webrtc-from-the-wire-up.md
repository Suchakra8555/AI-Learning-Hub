---
title: WebRTC from the wire up
summary: What actually happens between "join call" and hearing a voice. Signaling, SDP, ICE, STUN and TURN, DTLS-SRTP, RTP, Opus and the jitter buffer, with real output from two small scripts.
time: 25 min
---

[Lesson 1](lesson:livekit/what-livekit-is) drew the map of a LiveKit deployment. Every arrow on it that carries audio is a WebRTC connection, so before we look at rooms and tokens, we need to know what one of those connections does.

A user clicks "talk to the agent". Two seconds later they hear it. In between, two programs that have never met found a network path through two routers, agreed on a codec, set up encryption, and began trading 50 small packets a second each way. When any of those steps fails, the user hears nothing and your logs say little. This lesson walks the steps in order so you know where to look.

## Why audio rides on UDP

**TCP** delivers every byte, in order. If one packet is lost, every packet behind it waits until the lost one is resent. That wait is **head-of-line blocking**. A resend costs at least one round trip, often 100 ms or more.

For a file download, waiting is right. For a voice, it is wrong. Each packet holds 20 ms of sound. A packet that shows up 200 ms late has missed its moment to play, and while it was missing it held back the packets that arrived on time. A WebSocket runs over TCP, so it has the same problem.

**UDP** sends each packet on its own, with no resends and no ordering. Lost is lost. Real-time audio prefers that and fixes losses itself, with the tools further down: forward error correction, concealment and a jitter buffer. MDN lists the WebRTC protocols this way ([MDN: protocols](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Protocols)), and RFC 8825 gives the overview ([RFC 8825](https://datatracker.ietf.org/doc/html/rfc8825)).

## Two planes: signaling and media

**Signaling** is how the two sides swap setup messages before any audio flows. WebRTC does not define it. You build it, usually a WebSocket to your own server. **The media plane** is the audio itself, which goes straight between the peers (or through a relay) over UDP.

<figure>
<svg viewBox="0 0 780 470" role="img" aria-labelledby="t-seq d-seq">
  <title id="t-seq">Signaling plane and media plane in a WebRTC call</title>
  <desc id="d-seq">Peer A asks a STUN server for its public address. Peer A and Peer B swap an SDP offer, an SDP answer and ICE candidates through a signaling server that you run. Then, in the media plane, the peers run ICE connectivity checks, a DTLS handshake and finally SRTP audio directly, or through a TURN relay if no direct path works.</desc>
  <defs><marker id="ah-seq" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="20" y="16" width="140" height="44" rx="10"/><text x="90" y="43">Peer A (browser)</text>
    <rect class="box hot" x="220" y="16" width="140" height="44" rx="10"/><text x="290" y="43">Signaling server</text>
    <rect class="box" x="420" y="16" width="140" height="44" rx="10"/><text x="490" y="43">STUN / TURN</text>
    <rect class="box" x="620" y="16" width="140" height="44" rx="10"/><text x="690" y="43">Peer B</text>
  </g>
  <path class="arrow" stroke-dasharray="3 5" d="M90 60 V455"/>
  <path class="arrow" stroke-dasharray="3 5" d="M290 60 V455"/>
  <path class="arrow" stroke-dasharray="3 5" d="M490 60 V455"/>
  <path class="arrow" stroke-dasharray="3 5" d="M690 60 V455"/>
  <text x="770" y="84" font-size="12" class="small" text-anchor="end">ICE gathering (STUN, before the offer)</text>
  <text x="770" y="148" font-size="13" font-weight="700" text-anchor="end">Signaling plane (you build it)</text>
  <g font-size="12" class="small" text-anchor="middle">
    <path class="arrow" d="M90 108 H486" marker-end="url(#ah-seq)"/><text x="290" y="102">STUN binding request</text>
    <path class="arrow" d="M490 132 H94" marker-end="url(#ah-seq)"/><text x="390" y="126">"you are 203.0.113.7:54400"</text>
    <path class="arrow" d="M90 168 H286" marker-end="url(#ah-seq)"/><text x="190" y="162">SDP offer</text>
    <path class="arrow" d="M290 168 H686" marker-end="url(#ah-seq)"/><text x="490" y="162">SDP offer</text>
    <path class="arrow" d="M690 200 H294" marker-end="url(#ah-seq)"/><text x="490" y="194">SDP answer</text>
    <path class="arrow" d="M290 200 H94" marker-end="url(#ah-seq)"/><text x="190" y="194">SDP answer</text>
    <path class="arrow" stroke-dasharray="5 5" d="M94 232 H686" marker-start="url(#ah-seq)" marker-end="url(#ah-seq)"/><text x="390" y="226">ICE candidates, trickled both ways via the server</text>
  </g>
  <path class="arrow" stroke-dasharray="8 4" d="M10 262 H770"/>
  <text x="770" y="286" font-size="13" font-weight="700" text-anchor="end">Media plane (UDP, peer to peer)</text>
  <g font-size="12" class="small" text-anchor="middle">
    <path class="arrow" d="M94 318 H686" marker-start="url(#ah-seq)" marker-end="url(#ah-seq)"/><text x="390" y="312">ICE connectivity checks (STUN on each candidate pair)</text>
    <path class="arrow" d="M94 352 H686" marker-start="url(#ah-seq)" marker-end="url(#ah-seq)"/><text x="390" y="346">DTLS handshake, fingerprints checked against the SDP</text>
    <path class="arrow" stroke-width="3.5" d="M94 388 H686" marker-start="url(#ah-seq)" marker-end="url(#ah-seq)"/><text x="390" y="382">SRTP audio + RTCP, about 50 packets/s each way</text>
    <path class="arrow" stroke-dasharray="5 5" d="M94 432 H486" marker-end="url(#ah-seq)"/>
    <path class="arrow" stroke-dasharray="5 5" d="M494 432 H686" marker-end="url(#ah-seq)"/><text x="390" y="426">or, if no direct path: relayed through TURN</text>
  </g>
</svg>
<figcaption>Your server carries only setup messages. Once ICE picks a path, audio goes peer to peer or through a TURN relay and never touches the signaling server.</figcaption>
</figure>

## The SDP offer, line by line

**SDP** (Session Description Protocol) is a text format that describes a media session: codecs, encryption, addresses. One side sends an **offer**, the other replies with an **answer** that picks from it. `code/livekit/sdp_peek.py` holds a trimmed audio-only offer of the kind a browser makes, using documentation IP ranges. The important lines:

```text
a=group:BUNDLE 0                      all media shares one transport (RFC 8843)
m=audio 9 UDP/TLS/RTP/SAVPF 111 0     audio; port 9 is a placeholder, ICE finds the real one;
                                      payload types 111 then 0, in order of preference
c=IN IP4 0.0.0.0                      also a placeholder for the same reason
a=ice-ufrag:EsAw                      ICE username fragment and password: each STUN check
a=ice-pwd:P2uYro0UCOQ4zxjKXaWCBui1    is signed with these, so strangers can't hijack the path
a=fingerprint:sha-256 D2:FA:...       hash of this side's DTLS certificate
a=setup:actpass                       "I can be DTLS client or server; you choose"
a=rtcp-mux                            RTP and RTCP share one port
a=rtpmap:111 opus/48000/2             payload 111 means Opus, 48 kHz RTP clock
a=fmtp:111 minptime=10;useinbandfec=1 Opus options: send in-band FEC
a=rtpmap:0 PCMU/8000                  payload 0 is G.711 µ-law, the phone codec
a=candidate:... typ host / srflx / relay   addresses to try (next section)
```

The script parses it the way a stack would:

```python
if kind == "m":
    media, _port, proto, *pts = value.split()
elif value.startswith("rtpmap:"):
    pt, name = value[7:].split(" ", 1)
elif value.startswith("candidate:"):
    f = value.split()
    cands.append((f[7], f[4], f[5], int(f[3])))  # type, ip, port, priority
```

Real output of `python3 code/livekit/sdp_peek.py` (the script cuts the fingerprint short on purpose):

```text
media          audio
proto          UDP/TLS/RTP/SAVPF
payload order  ['111', '0']
ice-ufrag      EsAw
fingerprint    sha-256 D2:FA:0E:C3:22:...
setup          actpass

codecs, in order of preference:
  111 -> opus/48000/2  (minptime=10;useinbandfec=1)
    0 -> PCMU/8000

ICE candidates, highest priority first:
  host   192.168.1.20:54400  priority 2122260223
  srflx  203.0.113.7:54400  priority 1686052607
  relay  198.51.100.9:3478   priority 41885439
```

`UDP/TLS/RTP/SAVPF` reads as: RTP over UDP, keyed by DTLS, secure (S), with feedback (F) such as NACK. The `/2` in `opus/48000/2` doesn't mean the call is stereo. RFC 7587 requires that exact string for every Opus stream ([RFC 7587](https://datatracker.ietf.org/doc/html/rfc7587)).

## ICE: finding a path through two routers

Most devices sit behind **NAT** (network address translation): the router owns the public IP and maps each private address to a public port. A peer can't be reached at `192.168.1.20` from outside. **ICE** (Interactive Connectivity Establishment, [RFC 8445](https://datatracker.ietf.org/doc/html/rfc8445)) gathers every address that might work and tests them in pairs. Each address is a **candidate**:

- **host**: the device's own address. Works on the same network only.
- **srflx** (server reflexive): the public address and port the NAT gave you, learned by asking a **STUN** server "what address do you see me at?"
- **relay**: an address on a **TURN** server, which forwards every packet for you. Always works if TURN is reachable, but adds a hop and server cost.

<figure>
<svg viewBox="0 0 860 330" role="img" aria-labelledby="t-ice d-ice">
  <title id="t-ice">Host, server reflexive and relay paths between two peers behind NAT</title>
  <desc id="d-ice">Peer A on a private network sits behind NAT A. Peer B sits behind NAT B. STUN tells Peer A its public address. The srflx path goes straight through both NATs. The relay path goes from Peer A to a TURN server and on to Peer B. The host address only works inside the same network.</desc>
  <defs><marker id="ah-ice" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="16" y="120" width="136" height="60" rx="10"/><text x="84" y="146">Peer A</text><text x="84" y="166" font-size="12" class="small">192.168.1.20</text>
    <rect class="box" x="196" y="120" width="124" height="60" rx="10"/><text x="258" y="146">NAT A</text><text x="258" y="166" font-size="12" class="small">203.0.113.7</text>
    <rect class="box" x="370" y="24" width="120" height="50" rx="10"/><text x="430" y="54">STUN</text>
    <rect class="box hot" x="370" y="236" width="120" height="60" rx="10"/><text x="430" y="262">TURN relay</text><text x="430" y="282" font-size="12" class="small">198.51.100.9</text>
    <rect class="box" x="540" y="120" width="124" height="60" rx="10"/><text x="602" y="150">NAT B</text>
    <rect class="box" x="708" y="120" width="136" height="60" rx="10"/><text x="776" y="150">Peer B</text>
  </g>
  <path class="arrow" stroke-dasharray="5 5" d="M290 120 L370 64" marker-end="url(#ah-ice)"/>
  <text x="250" y="80" font-size="12" class="small" text-anchor="middle">"what's my public address?"</text>
  <path class="arrow" d="M152 150 H192" marker-end="url(#ah-ice)"/>
  <path class="arrow" d="M320 150 H536" marker-start="url(#ah-ice)" marker-end="url(#ah-ice)"/>
  <path class="arrow" d="M664 150 H704" marker-end="url(#ah-ice)"/>
  <text x="430" y="142" font-size="12" class="small" text-anchor="middle">srflx: direct, through both NATs</text>
  <path class="arrow" stroke-dasharray="5 5" d="M84 180 C84 266 250 266 366 266" marker-end="url(#ah-ice)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M490 266 C620 266 776 266 776 184" marker-end="url(#ah-ice)"/>
  <text x="640" y="256" font-size="12" class="small" text-anchor="middle">relay: when nothing direct works</text>
  <text x="84" y="106" font-size="12" class="small" text-anchor="middle">host: same LAN only</text>
</svg>
<figcaption>Three kinds of candidate. ICE tries the pairs in priority order and keeps the best one that answers.</figcaption>
</figure>

Each candidate has a **priority**. RFC 8445 section 5.1.2.1 computes it as `2^24 × type preference + 2^8 × local preference + (256 − component)`. Divide the numbers above by 2^24 and you get the type preferences: 126 for host, 100 for srflx, 2 for relay. The RFC recommends 126 for host, 100 for srflx and 0 for relay. This offer is a hand-made sample, and its 2 for relay is just the value that sample uses. Either way, a direct path beats a relayed one.

Then come **connectivity checks**. Each side sends STUN binding requests on every candidate pair, signed with the other side's `ice-pwd`. A pair that gets a reply is valid. The controlling side nominates one, and media starts on it.

Why do you need TURN at all? MDN puts it this way: some routers use **symmetric NAT**, which "will only accept connections from peers you've previously connected to", and TURN gets around this by relaying everything ([MDN: protocols](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Protocols)). RFC 4787 explains why: with an address-dependent mapping, the NAT picks a new public port for each destination. So the port STUN reported is not the one the other peer would need ([RFC 4787](https://datatracker.ietf.org/doc/html/rfc4787)). MDN's [connectivity page](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Connectivity) walks through the whole exchange.

## DTLS, then SRTP: always encrypted

Once ICE has a path, the peers run a **DTLS** handshake over it. DTLS is TLS adapted for UDP. Each side checks that the certificate it received hashes to the `a=fingerprint` from the SDP, so the signaling channel vouches for the media channel. `setup:actpass` in the offer and `active` or `passive` in the answer decide who acts as the DTLS client. The handshake then exports keys for **SRTP**, encrypted RTP ([RFC 5764](https://datatracker.ietf.org/doc/html/rfc5764)). WebRTC has no unencrypted mode for media.

<figure>
<svg viewBox="0 0 640 360" role="img" aria-labelledby="t-stack d-stack">
  <title id="t-stack">The WebRTC protocol stack</title>
  <desc id="d-stack">From the bottom: IP, UDP, then ICE. Above ICE the stack splits. On the audio side: SRTP and SRTCP, then RTP and RTCP, then Opus audio. On the data side: DTLS, then SCTP, then data channel messages. The DTLS handshake hands keys to SRTP.</desc>
  <defs><marker id="ah-stack" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <text x="161" y="28" font-weight="700">Audio</text>
    <text x="479" y="28" font-weight="700">Data channels</text>
    <rect class="box" x="16" y="40" width="290" height="40" rx="8"/><text x="161" y="65">Opus frames (20 ms each)</text>
    <rect class="box" x="334" y="40" width="290" height="40" rx="8"/><text x="479" y="65">Your messages</text>
    <rect class="box" x="16" y="88" width="290" height="40" rx="8"/><text x="161" y="113">RTP + RTCP</text>
    <rect class="box" x="334" y="88" width="290" height="40" rx="8"/><text x="479" y="113">SCTP</text>
    <rect class="box hot" x="16" y="136" width="290" height="40" rx="8"/><text x="161" y="161">SRTP / SRTCP</text>
    <rect class="box hot" x="334" y="136" width="290" height="40" rx="8"/><text x="479" y="161">DTLS</text>
    <rect class="box" x="16" y="184" width="608" height="40" rx="8"/><text x="320" y="209">ICE (STUN checks pick and keep the path)</text>
    <rect class="box" x="16" y="232" width="608" height="40" rx="8"/><text x="320" y="257">UDP</text>
    <rect class="box" x="16" y="280" width="608" height="40" rx="8"/><text x="320" y="305">IP</text>
  </g>
  <path class="arrow" d="M330 156 H310" marker-end="url(#ah-stack)"/>
  <text x="320" y="344" font-size="12" class="small" text-anchor="middle">The DTLS handshake exports the SRTP keys. With BUNDLE and rtcp-mux, all of it shares one UDP port.</text>
</svg>
<figcaption>Audio and data share the same ICE path and UDP port. Audio is SRTP keyed by DTLS. Data channels are SCTP carried inside DTLS.</figcaption>
</figure>

## RTP, RTCP and Opus

**RTP** ([RFC 3550](https://datatracker.ietf.org/doc/html/rfc3550)) wraps each audio frame with a header. Two fields matter most. The **sequence number** goes up by one per packet, so the receiver can spot loss and reordering. The **timestamp** counts audio samples, so the receiver knows when to play the frame. For Opus the RTP clock is always 48 kHz, so a 20 ms frame moves the timestamp by 960 (RFC 7587).

**RTCP** is the control channel next to it. Sender and receiver reports carry the fraction of packets lost, the total lost, and the interarrival jitter (RFC 3550). Feedback messages such as a **NACK** ("I'm missing packet 4512") come from RFC 4585. A resent audio packet often arrives too late to be useful, so for voice the codec does most of the recovery.

**Opus** ([RFC 6716](https://datatracker.ietf.org/doc/html/rfc6716)) runs from 6 to 510 kbit/s with frames of 2.5 to 60 ms. Two features matter for voice. **DTX** (discontinuous transmission) sends almost nothing during silence, which saves bandwidth. **In-band FEC** (forward error correction) tucks a low-bitrate copy of the previous frame into the current packet, so one lost packet can be rebuilt from the next. That is what `useinbandfec=1` turns on.

## The jitter buffer

Packets leave every 20 ms but arrive unevenly. That variation is **jitter**. The receiver holds audio in a **jitter buffer** for a few ms before playing it. Make it too small and late packets miss their slot. Make it too big and every word arrives later. `code/livekit/jitter_buffer.py` sends 500 packets through a network with a 40 ms base delay, a random tail and 2% loss:

```python
delay = 40 + rnd.expovariate(1 / 15)        # 40 ms base + a long tail
...
deadline = seq * FRAME_MS + 40 + depth_ms   # when this frame must play
```

Real output:

```text
500 packets, 11 lost, 68 arrived before the one sent ahead of them

buffer  added delay  late frames  gaps to conceal
   0 ms         0 ms          489              500
  10 ms        10 ms          227              238
  20 ms        20 ms          127              138
  40 ms        40 ms           35               46
  60 ms        60 ms            7               18
 100 ms       100 ms            1               12
```

The 0 ms row isn't a bug. The deadline is exactly the 40 ms base, and every packet in this model takes longer than that, so all 489 that arrived were late. "Gaps to conceal" is late plus lost. Going from 40 to 60 ms of buffer cuts the gaps from 46 to 18. Another 40 ms after that only removes 6 more. Every gap is filled by **PLC** (packet loss concealment): the decoder makes up plausible sound, usually by stretching what came before. The script keeps the depth fixed. Real stacks such as NetEq in libwebrtc grow and shrink it as conditions change.

:::try
In `network()`, change the loss from `0.02` to `0.05` and predict the 100 ms row before you run it. Then put loss back and change the tail from `1 / 15` to `1 / 30`. Which change hurts the 40 ms row more, and why does more buffer fix only one of them?
:::

## Data channels

**Data channels** send arbitrary messages over the same connection, using **SCTP** (a message-based transport) inside DTLS ([RFC 8831](https://datatracker.ietf.org/doc/html/rfc8831)). Each channel can be reliable or not, and ordered or not. LiveKit lists data messaging (text, files, RPC) among its WebRTC transport features ([LiveKit docs index](https://docs.livekit.io/llms.txt)). We did not check which of those ride on SCTP.

## Where this shows up in LiveKit

Every participant's link to a LiveKit server is one of these connections. A browser, a Python agent and a CLI bot all run ICE, DTLS and SRTP the same way. The LiveKit server plays the other peer. A phone call is different: it reaches LiveKit as SIP plus RTP through the separate SIP service, which then joins the room as a participant (the telephony lessons cover it). For these legs in a real system, see [the system map](lesson:voice-prod/the-system-map) in the Voice in production track. [WebRTC for the Curious](https://webrtcforthecurious.com/) is a free book that goes through every layer in more depth.

On the server side, the ports decide whether ICE finds a UDP pair. LiveKit advertises its UDP range (default 50000 to 60000) as host candidates, and each participant in a room uses two ports. TCP port 7881 is the fallback when a client can't connect over UDP, for example behind a VPN or a corporate firewall ([LiveKit: ports and firewall](https://docs.livekit.io/transport/self-hosting/ports-firewall/)). If the firewall blocks the range, calls fall back to TCP, with the head-of-line blocking from the top of this page, or fail. Rough sizing from the two-ports rule: a range of 101 ports covers about 50 participants on a node. [Run it yourself](lesson:livekit/run-it-yourself) goes through every port.

:::note Self-hosted vs Cloud
LiveKit tries ICE over UDP first, then TURN over UDP, then ICE over TCP, then TURN over TLS. LiveKit Cloud runs the TURN/TLS servers for you. Self-hosted, ICE over UDP and TCP work out of the box, but TURN needs extra config and your own SSL certificate ([connecting to LiveKit](https://docs.livekit.io/intro/basics/connect/#connection-reliability)).
:::

:::tip CLI
None of this needs a command, but `lk room join --publish-demo <room>` opens a real WebRTC connection from your terminal. On the lab, the server log then shows a `starting RTC session` line for that participant.
:::

:::warn A port range that works on a laptop proves nothing
On your own machine, host candidates connect straight away, so any port range seems fine. A production voice platform (see the Voice in production track) found that its servers had no public IP, so SIP's RTP could not reach them at all and phone audio had to come in another way. Before you trust a WebRTC or SIP port range, test it from outside the network.
:::

:::note What we did not test
The SDP is a hand-trimmed sample, not a capture from a live browser. The jitter buffer is a fixed-depth model. We didn't capture packets from a live LiveKit call or measure its jitter. LiveKit's port behavior comes from its docs, not from a firewall test.
:::

:::say
WebRTC is signaling you build, then ICE to find a UDP path, DTLS to swap keys, and SRTP carrying Opus that a jitter buffer and PLC smooth over.
:::

:::check Why would you rather lose an audio packet than wait for TCP to resend it?
A 20 ms frame that arrives after its play time is useless, and while TCP waits for the resend it also holds back the packets behind it. With UDP, the lost frame is concealed and the rest play on time.
:::

:::check Two peers each have a srflx candidate, but the call only works through TURN. What is the likely cause?
At least one NAT is symmetric (address-dependent mapping). It gives a different public port for each destination, so the port STUN reported doesn't work for the other peer and only the relay path gets through.
:::

Next: [Mesh, MCU and SFU](lesson:livekit/mesh-mcu-sfu)
