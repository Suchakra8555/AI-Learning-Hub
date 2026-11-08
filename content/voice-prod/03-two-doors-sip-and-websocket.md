---
title: Two doors: SIP and WebSocket
summary: A phone call can reach a LiveKit room through SIP or through a carrier's WebSocket stream. Learn what each needs from your network, and why our cloud setup forced the second.
time: 20 min
---

You have a working agent in a LiveKit room and a phone number at a carrier. Now the call has to get from the carrier's network into your room. The textbook answer is SIP. On our cloud hosts SIP was not an option, because the instances have no public IP and no public UDP port. This lesson covers both doors and how to pick between them.

If SIP, RTP and WebRTC are new to you, read [WebRTC, phone lines, and LiveKit](lesson:voice/webrtc-sip-livekit) first.

## Door 1: SIP

The carrier speaks SIP to set the call up and sends the audio as **RTP**, a stream of small UDP packets with timestamps ([RFC 3550](https://datatracker.ietf.org/doc/html/rfc3550)). LiveKit's SIP service answers, turns the call into a participant, and puts it in a room ([LiveKit SIP](https://docs.livekit.io/sip/)). Your code never touches the audio.

The price is the network. LiveKit's own port table says SIP needs UDP 5060 for signaling and UDP 10000 to 20000 for media, both open to the internet ([ports and firewall](https://docs.livekit.io/home/self-hosting/ports-firewall/)). Your SIP host needs a public address, and the carrier must reach it directly.

## Door 2: the carrier's WebSocket

Many carriers can also stream a call's audio over a **WebSocket**, a long-lived two-way connection that starts as an HTTPS request on TCP 443 ([RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)). Twilio calls this Media Streams. Vobiz and Ozonetel have their own versions. TCP on 443 goes through an ordinary load balancer, the same way your web traffic does.

Now someone has to take the audio off that socket and put it in a room. That is the **media bridge**: a service that joins the room as a normal participant and passes audio both ways.

<figure>
<svg viewBox="0 0 900 360" role="img" aria-labelledby="t-doors d-doors">
  <title id="t-doors">Two ways a phone call reaches the same room</title>
  <desc id="d-doors">Left: the carrier sends SIP and RTP over public UDP to LiveKit SIP, which joins the room. Right: the carrier opens a WebSocket on TCP 443 to the load balancer, which forwards it to the media bridge, which joins the same room as a participant. The agent is in the room either way.</desc>
  <defs><marker id="ah-doors" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="40" y="18" font-size="15" font-weight="700">Door 1: SIP</text>
  <text x="600" y="18" font-size="15" font-weight="700">Door 2: WebSocket</text>
  <g font-size="15" text-anchor="middle">
    <rect class="box" x="40" y="30" width="260" height="50" rx="10"/><text x="170" y="60">Carrier</text>
    <rect class="box" x="40" y="180" width="260" height="50" rx="10"/><text x="170" y="210">LiveKit SIP</text>
    <rect class="box" x="600" y="30" width="260" height="50" rx="10"/><text x="730" y="60">Carrier</text>
    <rect class="box" x="600" y="105" width="260" height="50" rx="10"/><text x="730" y="135">Load balancer /telephony/*</text>
    <rect class="box" x="600" y="180" width="260" height="50" rx="10"/><text x="730" y="210">Media bridge</text>
    <rect class="box hot" x="340" y="270" width="220" height="56" rx="10"/><text x="450" y="294">LiveKit room</text><text x="450" y="314" font-size="12" class="small">caller + agent</text>
  </g>
  <path class="arrow" d="M170 80 V176" marker-end="url(#ah-doors)"/>
  <text x="180" y="125" font-size="12" class="small">SIP + RTP, public UDP</text>
  <path class="arrow" d="M730 80 V101" marker-end="url(#ah-doors)"/>
  <text x="740" y="96" font-size="12" class="small">wss:// on TCP 443</text>
  <path class="arrow" d="M730 155 V176" marker-end="url(#ah-doors)"/>
  <path class="arrow" d="M170 230 V298 H336" marker-end="url(#ah-doors)"/>
  <path class="arrow" d="M730 230 V298 H564" marker-end="url(#ah-doors)"/>
  <text x="40" y="350" font-size="12" class="small">Needs a public IP and open UDP ports.</text>
  <text x="600" y="350" font-size="12" class="small">Private hosts. LiveKit traffic stays inside.</text>
</svg>
<figcaption>Both doors end in the same room. The agent can't tell which one the caller used.</figcaption>
</figure>

## What the platform did

Locally, both doors work. On AWS, only the WebSocket door is used. The hosts have private IPs, and nobody wanted to open thousands of public UDP ports.

:::tip See the SIP door work
The platform never ran the SIP door in the cloud. [Self-hosted SIP](lesson:livekit/self-hosted-sip) runs it on a laptop: a script sends a raw SIP INVITE, gets a 200 OK, streams RTP, and hears the agent's audio come back. [SIP fundamentals](lesson:livekit/sip-fundamentals) explains each message on that path.
:::

A WebSocket call goes like this:

1. The carrier sends an HTTPS webhook: "a call came in on this number." The load balancer passes `/telephony/*` straight to the bridge. The API gateway is not in this path, since it can't proxy WebSockets.
2. The bridge looks up which assistant owns the number, creates a queued Call row, and stores a one-time **stream ticket** in Redis.
3. It replies with the carrier's XML, telling it to open a stream to the bridge with the ticket attached.
4. The carrier opens the socket and sends `start`. The bridge redeems the ticket, then joins the room as `pstn-<call_id>`. That join creates the room, and the agent is dispatched to it.

From here the rest of the platform can't tell this call from any other. LiveKit's webhooks mark the Call row active, and recording and customer webhooks work unchanged. [Who is on this socket](lesson:voice-prod/who-is-on-this-socket) covers the ticket in depth.

The bridge sets a few limits on the socket:

| Situation | What happens |
|---|---|
| No `start` within 10 s | Socket closed |
| `start` with a missing, reused or wrong ticket | Closed with code 1008, "policy violation" ([RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455#section-7.4.1)) |
| 15 s with no message | Treated as a hang-up |
| New stream while draining for a deploy | Closed with code 1013, "try again later" ([IANA registry](https://www.iana.org/assignments/websocket/websocket.xhtml#close-code-number)) |

During a deploy the bridge gets SIGTERM and starts to **drain**: `/health` returns 503 so the load balancer stops sending new calls, and live calls get up to 300 s to finish.

The bridge costs you one more service, and your own code now handles audio. Lesson 2 showed what that involves. Every feature also has to be rebuilt per carrier. On our platform, keypad digits (DTMF) on the WebSocket path are still only logged and never reach the agent.

:::warn Gotcha from the platform
The drain waits up to 300 s, but Fargate, where the platform plans to run, gives a task at most 120 s after SIGTERM before it kills it ([AWS docs](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_ContainerDefinition.html), see `stopTimeout`). On that target, a deploy would cut any call still running at 120 s. Carriers do not reconnect a dropped stream, so the caller just hears the line go dead.
:::

:::try
A deploy sends SIGTERM at t=0. One call is 2 minutes in and will last 4 more. A new call arrives at t=10 s. Using the table and the drain rule, predict what happens to each call on a host with a 330 s stop grace period. Then do it again for a 120 s limit.
:::

:::note What we did not test
We read the platform's design notes and code, and LiveKit's and AWS's docs. We did not place SIP calls on AWS. We did not time how long the WebSocket door adds compared with SIP.
:::

:::say
SIP needs public UDP. A carrier WebSocket needs only HTTPS, plus a bridge that you write and run.
:::

:::check Why does the media bridge sit beside the API gateway instead of behind it?
The gateway can't proxy WebSockets, and carriers need a long-lived socket. The load balancer sends `/telephony/*` straight to the bridge.
:::

:::check What does a new stream get while the bridge is draining, and why that code?
Close code 1013, "try again later". The bridge is shutting down, so the caller should be served by another instance. The 503 on `/health` already steers the load balancer away.
:::

Next: [How the platform rides LiveKit](lesson:voice-prod/how-the-platform-rides-livekit)
