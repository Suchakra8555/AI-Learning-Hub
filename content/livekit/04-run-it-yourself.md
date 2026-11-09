---
title: Run it yourself
summary: Start livekit-server in dev mode, then read the lab's real config key by key, learn which ports it needs and why the lab uses host networking, and check that the server is alive with curl, its startup log and Prometheus.
time: 25 min
---

You start a LiveKit server in Docker, open the web client, and it says "connected". Nobody hears anything. The signaling WebSocket got through on one TCP port, but the audio needs a whole range of UDP ports that Docker or a firewall quietly dropped. Most first self-hosting problems look like this. This lesson starts a server two ways, the quick way and the lab's way, and goes through every key and port so you know what each one is for.

The lab runs **livekit-server v1.13.11** with Redis 7, and `lk` v2.19.3.

## The quick start: dev mode

LiveKit's [local guide](https://docs.livekit.io/transport/self-hosting/local/) installs the server with `brew install livekit` on macOS or `curl -sSL https://get.livekit.io | bash` on Linux, then starts it with one flag:

```bash
livekit-server --dev
```

**Dev mode** starts the server with a fixed API key and secret, `devkey` and `secret`. It binds the signal port to `127.0.0.1:7880`, so only your machine can reach it. Pass `--bind 0.0.0.0` to let other devices on your network connect (same page). Everyone knows the dev key, so never expose a dev-mode server.

Dev mode is enough to try a client. The lab uses a real config file instead, so it behaves like a deployment: its own key, Redis, webhooks and metrics.

## The lab's config, key by key

`code/livekit/lab/docker-compose.yml` starts Redis and the server. Egress, ingress and SIP sit behind Compose profiles, so they start only when you ask:

```yaml
services:
  redis:
    image: redis:7-alpine
    network_mode: host
    command: ["redis-server", "--bind", "127.0.0.1", "--port", "6379"]
  livekit:
    image: livekit/livekit-server:v1.13.11
    network_mode: host
    command: ["--config", "/etc/livekit.yaml"]
    volumes: ["./livekit.yaml:/etc/livekit.yaml:ro"]
    depends_on: [redis]
  egress:
    profiles: [egress]
    ...
```

The server reads `code/livekit/lab/livekit.yaml`. The [deployment guide](https://docs.livekit.io/transport/self-hosting/deployment/) gives a recommended production config, and the lab follows it with a few shortcuts:

| Key | Lab value | What it does |
|---|---|---|
| `port` | `7880` | HTTP API and the signaling WebSocket at `/rtc`. Put TLS in front of it in production. |
| `bind_addresses` | `["127.0.0.1"]` | Lab shortcut: only this machine can connect. Production listens on all interfaces behind a load balancer. |
| `rtc.tcp_port` | `7881` | ICE over TCP, the fallback when UDP is blocked. |
| `rtc.port_range_start` / `_end` | `50000` / `50200` | ICE over UDP, two ports per participant. Lab shortcut: the docs' range is 50000–60000. |
| `rtc.use_external_ip` | `false` | `true` on a cloud VM, so the server finds its public IP with STUN and advertises that. |
| `redis.address` | `127.0.0.1:6379` | Turns on **distributed mode**: rooms and messages go through Redis. Egress, ingress and SIP must use the same Redis. |
| `keys` | `lab-key: lab-secret-…` | API key and secret pairs. Tokens and API calls are signed with these. |
| `webhook.api_key`, `webhook.urls` | `lab-key`, `http://127.0.0.1:8099/webhook` | Where the server POSTs room events. Each one is signed with that key's secret. |
| `prometheus.port` | `6789` | Metrics at `/metrics`. |
| `room.empty_timeout` | `300` | Seconds an empty room lives before it closes. |
| `room.departure_timeout` | `20` | Seconds a room lives after the last participant leaves. |
| `ingress.rtmp_base_url`, `whip_base_url` | `rtmp://127.0.0.1:1935/live`, `http://127.0.0.1:8080/w` | The URLs the server hands out when you create an ingress. |

The full list of keys is in [config-sample.yaml](https://github.com/livekit/livekit/blob/master/config-sample.yaml).

## Why the lab uses host networking

WebRTC media rides on a range of UDP ports, and the server puts its own IP and ports into every ICE candidate. With Docker's default bridge network, the container sees a private Docker IP and every port has to be mapped through Docker's NAT. That gives you thousands of port mappings, and candidates that may carry an address nobody outside can reach. That is our reading of why it fails. The docs only say that in Docker "host networking should be used for optimal performance" ([deployment](https://docs.livekit.io/transport/self-hosting/deployment/)), and that on Kubernetes the pods need host networking, so you get one LiveKit pod per node ([Kubernetes](https://docs.livekit.io/transport/self-hosting/kubernetes/)).

With `network_mode: host`, the container uses the host's interfaces directly. That only works this way on Linux, which is why the Compose file says "Linux only".

## Ports

From [ports and firewall](https://docs.livekit.io/transport/self-hosting/ports-firewall/), plus the [ingress](https://docs.livekit.io/transport/self-hosting/ingress/) and [SIP server](https://docs.livekit.io/transport/self-hosting/sip-server/) pages:

| Port | Config key | What uses it |
|---|---|---|
| 7880/tcp | `port` | API and WebSocket signaling. Not exposed directly; put a TLS load balancer in front. |
| 7881/tcp | `rtc.tcp_port` | ICE over TCP, when UDP fails (VPN, corporate firewall). |
| 50000–60000/udp | `rtc.port_range_start/end` | ICE over UDP, advertised as host candidates. Two per participant. |
| 7882/udp | `rtc.udp_port` | Optional: all UDP on one port (UDP mux). The range is then unused. |
| 3478/udp | `turn.udp_port` | Optional embedded TURN/UDP. Also serves as STUN. |
| 5349/tcp | `turn.tls_port` | Optional TURN/TLS. Set it to 443 if there's no load balancer. |
| 5060/udp+tcp | `sip_port` (SIP config) | SIP signaling. The docs say it must be reachable from the internet. |
| 10000–20000/udp | `rtp_port` (SIP config) | SIP RTP media. Also must be reachable. |
| 1935/tcp, 8080/tcp, 7885/udp | ingress config | RTMP ingest, WHIP over HTTP, and WebRTC for WHIP. |

<figure>
<svg viewBox="0 0 860 446" role="img" aria-labelledby="run-t run-d">
  <title id="run-t">Ports and paths of a self-hosted LiveKit deployment</title>
  <desc id="run-d">Browsers and agent servers reach livekit-server with signaling on TCP 7880 and media on the UDP range. A phone carrier reaches the SIP service on 5060 and RTP 10000 to 20000. OBS or ffmpeg reach the ingress service on 1935, 8080 or 7885. The SIP service joins rooms over WebRTC. livekit-server, SIP, ingress and egress all talk through Redis. livekit-server sends webhooks to your backend.</desc>
  <defs><marker id="run-ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="16" y="40" width="150" height="56" rx="10"/><text x="91" y="64">Browser or app</text><text x="91" y="84" font-size="12" class="small">client SDK</text>
    <rect class="box" x="16" y="150" width="150" height="56" rx="10"/><text x="91" y="174">Agent server</text><text x="91" y="194" font-size="12" class="small">Python SDK</text>
    <rect class="box" x="16" y="290" width="150" height="56" rx="10"/><text x="91" y="323">Phone carrier</text>
    <rect class="box" x="16" y="370" width="150" height="56" rx="10"/><text x="91" y="403">OBS / ffmpeg</text>
    <rect class="box hot" x="330" y="30" width="260" height="220" rx="10"/><text x="460" y="54" font-weight="700">livekit-server</text>
    <rect class="box" x="330" y="290" width="260" height="56" rx="10"/><text x="460" y="312">livekit/sip</text><text x="460" y="334" font-size="12" class="small">5060 udp/tcp · RTP 10000–20000</text>
    <rect class="box" x="330" y="370" width="260" height="56" rx="10"/><text x="460" y="392">livekit/ingress</text><text x="460" y="414" font-size="12" class="small">1935 RTMP · 8080 WHIP · 7885/udp</text>
    <rect class="box" x="660" y="30" width="184" height="56" rx="10"/><text x="752" y="54">Your backend</text><text x="752" y="74" font-size="12" class="small">webhook receiver</text>
    <rect class="box" x="660" y="150" width="184" height="56" rx="10"/><text x="752" y="174">Redis</text><text x="752" y="194" font-size="12" class="small">6379</text>
    <rect class="box" x="660" y="260" width="184" height="56" rx="10"/><text x="752" y="284">livekit/egress</text><text x="752" y="304" font-size="12" class="small">no inbound port</text>
  </g>
  <g font-size="13" text-anchor="start">
    <text x="346" y="84">7880/tcp   API + /rtc signaling</text>
    <text x="346" y="108">7881/tcp   ICE over TCP</text>
    <text x="346" y="132">50000–60000/udp   ICE media</text>
    <text x="346" y="156">7882/udp   UDP mux (optional)</text>
    <text x="346" y="180">3478/udp   TURN/UDP (optional)</text>
    <text x="346" y="204">5349/tcp   TURN/TLS (optional)</text>
    <text x="346" y="228">6789/tcp   Prometheus /metrics</text>
  </g>
  <path class="arrow" d="M166 58 H326" marker-end="url(#run-ah)"/>
  <path class="arrow" stroke-width="3.5" d="M166 82 H326" marker-start="url(#run-ah)" marker-end="url(#run-ah)"/>
  <path class="arrow" d="M166 168 H326" marker-end="url(#run-ah)"/>
  <path class="arrow" stroke-width="3.5" d="M166 192 H326" marker-start="url(#run-ah)" marker-end="url(#run-ah)"/>
  <path class="arrow" d="M166 318 H326" marker-start="url(#run-ah)" marker-end="url(#run-ah)"/>
  <path class="arrow" d="M166 398 H326" marker-end="url(#run-ah)"/>
  <path class="arrow" d="M460 286 V254" marker-start="url(#run-ah)" marker-end="url(#run-ah)"/>
  <path class="arrow" d="M590 58 H656" marker-end="url(#run-ah)"/>
  <path class="arrow" d="M590 178 H656" marker-start="url(#run-ah)" marker-end="url(#run-ah)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M630 178 V398 M590 318 H630 M590 398 H630 M660 288 H630"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="248" y="52">signaling :7880</text>
    <text x="248" y="76">media, UDP range</text>
    <text x="248" y="162">signaling :7880</text>
    <text x="248" y="186">media, UDP range</text>
    <text x="248" y="312">SIP + RTP</text>
    <text x="248" y="392">RTMP / WHIP</text>
    <text x="623" y="50">webhooks</text>
    <text x="752" y="232">jobs and routing via Redis</text>
  </g>
  <text x="468" y="274" font-size="12" class="small" text-anchor="start">joins rooms over WebRTC</text>
</svg>
<figcaption>Clients need 7880 for signaling and the UDP range for audio. SIP and ingress have their own public ports. Ingress also joins rooms as a participant, and egress records by subscribing to tracks. Everything except your backend talks through Redis.</figcaption>
</figure>

## Start it and check it

```bash
cd code/livekit/lab
docker compose up -d                  # redis + livekit-server
curl localhost:7880                   # health check
curl -s localhost:6789/metrics | head -3
docker compose logs livekit | grep "starting LiveKit server"
```

Real output from the lab:

```text
OK
# HELP go_gc_duration_seconds A summary of the wall-time pause (stop-the-world) duration in garbage collection cycles.
# TYPE go_gc_duration_seconds summary
go_gc_duration_seconds{quantile="0"} 3.9761e-05
2026-11-08T09:26:48.377Z	INFO	livekit	service/server.go:309	starting LiveKit server	{"portHttp": 7880, "nodeID": "ND_BMq5GmY2stv8", "nodeIP": "10.148.102.64", "version": "1.13.11", "bindAddresses": ["127.0.0.1"], "rtc.portTCP": 7881, "rtc.portICERange": [50000, 50200], "portPrometheus": 6789}
```

The startup line is the quickest config check you have. It shows the version, the bind address, the TCP port, the UDP range and the metrics port the server actually loaded. `nodeIP` is the machine's LAN address. Just before it, the server logs `connecting to redis`, which tells you it started in distributed mode.

One more line showed up in the lab's log when the CLI joined a room: `ERROR ... could not match local candidate` for an IPv6 link-local (`fe80::`) address. Audio still flowed on every lab run. We didn't dig into why it is logged.

An older config key gives you a warning. With the flat `prometheus_port: 6789`, the lab's server printed "prometheus_port is deprecated, please switch to prometheus.port". The deployment guide's sample config still shows `#prometheus_port: 6789` in a comment, so copying it gets you the warning. Use `prometheus: {port: 6789}`.

## How a client gets through

The [connection guide](https://docs.livekit.io/intro/basics/connect/#connection-reliability) lists the order a client tries:

1. ICE over UDP, which works in most cases.
2. TURN over UDP (3478), when ICE/UDP can't reach the server.
3. ICE over TCP (7881), when the network blocks UDP, for example on a VPN.
4. TURN over TLS, when the firewall allows only outbound TLS. To a firewall it looks like HTTPS.

The lab only has the first and third. TURN needs a domain and a certificate signed by a trusted CA; self-signed certs don't work ([deployment](https://docs.livekit.io/transport/self-hosting/deployment/)).

:::note Self-hosted vs Cloud
LiveKit Cloud runs TURN/TLS servers for you. Self-hosted, ICE over UDP and TCP work out of the box, but TURN needs the `turn:` block, a TURN domain and your own SSL certificate ([connection guide](https://docs.livekit.io/intro/basics/connect/#connection-reliability)). Without TURN/TLS, callers behind strict corporate firewalls won't connect.
:::

:::tip CLI
Point `lk` at the server and check it answers. `lk room list --dev` uses `devkey`/`secret` for a dev-mode server. For the lab, save it once with `lk project add lab --url http://127.0.0.1:7880 --api-key lab-key --api-secret <secret> --default`, then `lk room list`. On the lab, `lk room list --dev` printed "Using dev credentials" and then a 401, because the lab doesn't accept the dev key.
:::

:::try
Change `livekit.yaml` back to `prometheus_port: 6789`, run `docker compose up -d --force-recreate livekit`, and find the deprecation warning in `docker compose logs livekit`. Put the key back. Then work out how many participants the lab's range of 50000–50200 can hold at two ports each, and check `rtc.portICERange` in the startup line.
:::

:::warn Bound to 127.0.0.1 means invisible
The lab sets `bind_addresses: ["127.0.0.1"]` and `use_external_ip: false`. That is right for a laptop and wrong anywhere else. A phone on your Wi-Fi or a client on the internet can't reach 7880 at all. On a cloud VM, also set `use_external_ip: true`, or the server advertises its private IP in every candidate and media never arrives. Open the UDP range in the cloud firewall too, not just in the config.
:::

:::note What we did not test
We didn't run `livekit-server --dev` itself or the brew and curl installers; the lab used the Docker image. We didn't enable TURN, TLS, UDP mux or a load balancer, and didn't test from outside the machine. Host networking was only tried on Linux.
:::

:::say
A self-hosted LiveKit needs TCP 7880 for signaling and a UDP range for media, and the startup log line tells you which ones it actually opened.
:::

:::check The web client says "connected" but nobody hears audio. Which port is most likely blocked?
The UDP media range (50000–60000 by default). Signaling on TCP 7880 got through, so the client connected, but ICE found no UDP pair. If 7881 is also blocked, there's no TCP fallback either.
:::

:::check Why does setting `redis.address` matter even on a single machine?
It switches the server into distributed mode. Egress, ingress and SIP find the server and get their jobs through that same Redis, so without it they can't work with it.
:::
