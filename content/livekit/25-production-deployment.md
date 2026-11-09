---
title: Production deployment
summary: What changes when the lab goes on the internet. Domains and TLS, TURN, external IPs and keys, the VM path with the config generator, the Kubernetes path with Helm, the firewall, and the metrics worth alerting on.
time: 25 min
---

The lab listens on `127.0.0.1`, signs nothing with TLS, and opens 201 UDP ports. None of that survives on the internet. A browser won't open `ws://` from an `https://` page. A phone behind a hotel firewall can't reach UDP at all. And a server inside a cloud VM doesn't know its own public IP. This lesson lists what to change, then walks the two supported ways to deploy: a VM with the config generator, or Kubernetes with Helm.

## From the lab to the internet

Start with a domain and a real certificate. Clients connect to something like `wss://livekit.example.com`. The certificate must come from a trusted authority, because "self-signed certs do not work here". TLS ends at a load balancer or reverse proxy in front of port 7880 ([deployment](https://docs.livekit.io/transport/self-hosting/deployment)). Port 7880 itself is never exposed.

Next is TURN. LiveKit has a built-in **TURN** server (a relay for clients that can't reach the server directly). **TURN/TLS** looks like HTTPS to a firewall, so it gets through the strictest corporate networks. It needs its own domain and certificate, and LiveKit ends that TLS itself. Without a load balancer, `turn.tls_port` must be 443, because that is the port clients are told to use. **TURN/UDP** listens on 3478 and also serves STUN ([deployment](https://docs.livekit.io/transport/self-hosting/deployment#improving-connectivity-with-turn)).

Then the public IP. Set `rtc.use_external_ip: true` on most cloud VMs. The host has a public IP that the process can't see, so LiveKit finds it through STUN and advertises it in ICE candidates.

Last, keys and webhooks. The `keys` map can hold several key pairs, so you can add a new pair, move clients and services to it, then remove the old one. That rotation plan is our advice, not a docs page. The docs' webhook example posts to an `https://` URL and signs each request with one of those keys ([webhooks](https://docs.livekit.io/intro/basics/rooms-participants-tracks/webhooks-events)). The lab posts to plain `http://127.0.0.1`, which is fine only on one machine.

The docs' recommended production config, trimmed to the parts the lab doesn't have:

```yaml
rtc:
  port_range_start: 50000
  port_range_end: 60000
  use_external_ip: true
turn:
  enabled: true
  domain: <turn.myhost.com>   # must match the TLS certificate
  tls_port: 5349              # 443 if there is no load balancer
```

The same sample still shows `#prometheus_port: 6789`. That flat key is deprecated, and v1.13.11 warns about it. Use `prometheus: {port: 6789}` as the lab does. For hardware, the docs say capacity is bound by CPU and bandwidth, and suggest compute-optimized instances, 10 Gbps networking, and host networking under Docker.

<figure>
<svg viewBox="0 0 880 360" role="img" aria-labelledby="t-pd-topo d-pd-topo">
  <title id="t-pd-topo">A production LiveKit topology</title>
  <desc id="d-pd-topo">Clients open a secure WebSocket to a load balancer that ends TLS on port 443 and forwards to the LiveKit nodes. Media goes straight from clients to the nodes over UDP, or through TURN/TLS on its own domain. The nodes share a Redis. Egress, ingress and SIP services join rooms on the nodes. Agent servers dial out to the nodes over a WebSocket. A SIP trunk reaches the SIP service on 5060 with RTP on 10000 to 20000.</desc>
  <defs><marker id="pd-ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="20" y="30" width="150" height="110" rx="10"/><text x="95" y="72">Clients</text><text x="95" y="94" font-size="12" class="small">browsers, apps</text>
    <rect class="box hot" x="220" y="30" width="160" height="50" rx="10"/><text x="300" y="52">LB or proxy</text><text x="300" y="70" font-size="12" class="small">TLS on :443</text>
    <rect class="box" x="220" y="150" width="160" height="50" rx="10"/><text x="300" y="172">TURN/TLS</text><text x="300" y="190" font-size="12" class="small">turn.example.com</text>
    <rect class="box" x="440" y="30" width="190" height="170" rx="10"/><text x="535" y="80">LiveKit nodes</text><text x="535" y="102" font-size="12" class="small">one room per node</text><text x="535" y="120" font-size="12" class="small">host networking</text>
    <rect class="box" x="440" y="250" width="190" height="50" rx="10"/><text x="535" y="272">Redis</text><text x="535" y="290" font-size="12" class="small">rooms + message bus</text>
    <rect class="box" x="20" y="250" width="150" height="50" rx="10"/><text x="95" y="272">SIP trunk</text><text x="95" y="290" font-size="12" class="small">phone calls</text>
    <rect class="box" x="690" y="30" width="170" height="50" rx="10"/><text x="775" y="60">Egress pool</text>
    <rect class="box" x="690" y="95" width="170" height="50" rx="10"/><text x="775" y="125">Ingress pool</text>
    <rect class="box" x="690" y="160" width="170" height="50" rx="10"/><text x="775" y="182">Agent servers</text><text x="775" y="200" font-size="12" class="small">dial out over wss</text>
    <rect class="box" x="690" y="250" width="170" height="50" rx="10"/><text x="775" y="280">SIP service</text>
  </g>
  <path class="arrow" d="M170 55 H216" marker-end="url(#pd-ah)"/>
  <path class="arrow" d="M380 55 H436" marker-end="url(#pd-ah)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M170 115 H436" marker-end="url(#pd-ah)"/>
  <path class="arrow" d="M160 140 L216 168" marker-end="url(#pd-ah)"/>
  <path class="arrow" d="M380 175 H436" marker-end="url(#pd-ah)"/>
  <path class="arrow" d="M535 200 V246" marker-start="url(#pd-ah)" marker-end="url(#pd-ah)"/>
  <path class="arrow" d="M686 55 H634" marker-end="url(#pd-ah)"/>
  <path class="arrow" d="M686 120 H634" marker-end="url(#pd-ah)"/>
  <path class="arrow" d="M686 185 H634" marker-end="url(#pd-ah)"/>
  <path class="arrow" d="M686 275 H634" marker-end="url(#pd-ah)"/>
  <path class="arrow" d="M95 300 V330 H775 V304" marker-end="url(#pd-ah)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="193" y="47">wss</text>
    <text x="305" y="108">UDP media, direct</text>
    <text x="660" y="268">Redis</text>
    <text x="435" y="350">SIP 5060, RTP 10000-20000</text>
  </g>
</svg>
<figcaption>Signaling goes through the load balancer, media goes straight to a node. Egress, ingress and SIP find their work through the same Redis.</figcaption>
</figure>

## The VM path

The docs' VM guide uses a generator that you run on your own machine ([virtual machines](https://docs.livekit.io/transport/self-hosting/vm)):

```bash
docker pull livekit/generate
docker run --rm -it -v$PWD:/output livekit/generate
```

It asks for your domains and writes a folder with `caddy.yaml`, `docker-compose.yaml`, `livekit.yaml`, `redis.conf`, and either `init_script.sh` or a `cloud_init.xxxx.yaml`. It can add egress and ingress too. Paste the cloud-init file into the VM's user data, or copy `init_script.sh` over and run it with `sudo`. The result is Docker and Compose, the config in `/opt/livekit`, and a systemd unit called `livekit-docker`. **Caddy** (a web server) ends TLS and gets certificates from Let's Encrypt or ZeroSSL on its own, so you need no certificate files. It can only do that once both the main and TURN domains point at the VM.

To upgrade, change the `livekit` image tag in `/opt/livekit/docker-compose.yaml` to a new `livekit/livekit-server:v<version>`. When something breaks, start with `systemctl status livekit-docker` and `sudo docker-compose logs` in `/opt/livekit`. The Caddy log line "certificate obtained successfully" tells you TLS worked.

## The Kubernetes path

LiveKit publishes Helm charts ([Kubernetes](https://docs.livekit.io/transport/self-hosting/kubernetes)):

```bash
helm repo add livekit https://helm.livekit.io
helm install <INSTANCE_NAME> livekit/livekit-server --namespace <NAMESPACE> --values values.yaml
helm install <INSTANCE_NAME> livekit/egress --namespace <NAMESPACE> --values values.yaml
```

LiveKit pods use **host networking**, so the node's UDP and TCP ports go straight to the server. That allows one LiveKit pod per node. TLS ends at the Kubernetes Ingress, and the chart sets this up for GKE and for ALB on EKS. The chart sets `terminationGracePeriodSeconds` to 5 hours so a pod can drain its rooms during an upgrade. GKE, EKS and DigitalOcean DOKS work out of the box. Serverless and private clusters are not supported, because private clusters add NAT layers that break WebRTC. A changed ConfigMap doesn't restart pods, so restart the deployment yourself after a config change.

## The firewall

<figure>
<svg viewBox="0 0 880 330" role="img" aria-labelledby="t-pd-fw d-pd-fw">
  <title id="t-pd-fw">Which ports to open</title>
  <desc id="d-pd-fw">Ports that pass through the firewall: 443 TCP for HTTPS and TURN/TLS, 80 TCP for certificate issuance, 7881 TCP for ICE over TCP, 3478 UDP for TURN/UDP, 50000 to 60000 UDP for ICE over UDP, 1935 TCP for RTMP ingress, 7885 UDP for WHIP ingress, 5060 UDP and TCP plus 10000 to 20000 UDP for SIP. Ports to keep closed: 7880, Redis 6379, metrics 6789, ingress relay 9090 and agent health 8081.</desc>
  <defs><marker id="pd-ah2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect class="box hot" x="330" y="30" width="20" height="230" rx="4"/>
  <g font-size="13">
    <text x="20" y="54">443/TCP</text><text x="20" y="82">80/TCP</text><text x="20" y="110">7881/TCP</text><text x="20" y="138">3478/UDP</text>
    <text x="20" y="166">50000-60000/UDP</text><text x="20" y="194">1935/TCP</text><text x="20" y="222">7885/UDP</text><text x="20" y="250">5060, 10000-20000</text>
  </g>
  <g font-size="12" class="small">
    <text x="530" y="54">HTTPS signaling and TURN/TLS</text><text x="530" y="82">Caddy certificate issuance (VM path)</text>
    <text x="530" y="110">ICE over TCP, when UDP is blocked</text><text x="530" y="138">TURN/UDP, also STUN</text>
    <text x="530" y="166">ICE over UDP, 2 ports per participant</text><text x="530" y="194">RTMP ingress</text>
    <text x="530" y="222">WHIP ingress media</text><text x="530" y="250">SIP signaling and RTP (SIP service)</text>
  </g>
  <path class="arrow" d="M170 50 H520" marker-end="url(#pd-ah2)"/><path class="arrow" d="M170 78 H520" marker-end="url(#pd-ah2)"/>
  <path class="arrow" d="M170 106 H520" marker-end="url(#pd-ah2)"/><path class="arrow" d="M170 134 H520" marker-end="url(#pd-ah2)"/>
  <path class="arrow" d="M170 162 H520" marker-end="url(#pd-ah2)"/><path class="arrow" d="M170 190 H520" marker-end="url(#pd-ah2)"/>
  <path class="arrow" d="M170 218 H520" marker-end="url(#pd-ah2)"/><path class="arrow" d="M170 246 H520" marker-end="url(#pd-ah2)"/>
  <rect class="box" x="20" y="275" width="840" height="46" rx="8"/>
  <text x="440" y="295" font-size="13" text-anchor="middle">Keep closed to the internet</text>
  <text x="440" y="313" font-size="12" class="small" text-anchor="middle">7880 (behind the LB), 6379 Redis, 6789 metrics, 9090 ingress relay, 8081 agent health</text>
</svg>
<figcaption>Open only what a client, encoder or phone trunk must reach. Everything else stays on the private network.</figcaption>
</figure>

The VM guide's list is 443, 80, 7881, 3478/UDP and 50000-60000/UDP, plus 1935 and 7885/UDP for ingress ([VM firewall](https://docs.livekit.io/transport/self-hosting/vm#firewall)). The ports page adds 7882/UDP, used only if you set `rtc.udp_port` to put all media on one port, and the SIP ports ([ports and firewall](https://docs.livekit.io/transport/self-hosting/ports-firewall)). The 9090 and 8081 entries in the closed list are our reading of the ingress and agent docs. Test from outside your network: `curl http://<yourdomain>` should return a 404, not hang.

## Metrics and logs

With `prometheus: {port: 6789}`, the server serves `/metrics`. On the lab, `curl -s 127.0.0.1:6789/metrics | grep '^livekit_'` listed, among others, `livekit_participant_total`, `livekit_room_total`, `livekit_packet_loss_percent`, `livekit_rtt_ms`, `livekit_jitter_us`, `livekit_forward_latency`, `livekit_node_twirp_request_status` and `livekit_webhook_queue_length`. The docs don't publish an alert list, so this one is ours:

- packet loss, RTT and jitter rising across the node, not in one room
- Twirp request errors, which means the server API is failing
- a growing webhook queue, which means your receiver is down or slow
- `livekit_egress_available` and `livekit_ingress_available` near zero
- host CPU and network on each node, since those set capacity

Set `log_level: info` and ship container logs off the box. On the VM path they are in `docker-compose logs`.

:::note Self-hosted vs Cloud
LiveKit Cloud runs the TLS, TURN, scaling and monitoring for you, with a global mesh where any edge can serve a room. Self-hosted, all of this lesson is yours, and a room lives on one node. Token revocation is Cloud-only, so self-hosted you rely on short token lifetimes and on removing participants ([self-hosting overview](https://docs.livekit.io/transport/self-hosting)).
:::

:::tip CLI
`lk project add <name> --url wss://livekit.example.com --api-key <key> --api-secret <secret>` to save the production server, then `lk room list --curl` to see the exact HTTPS request it sends, and `lk room join --publish-demo <room>` to prove media gets through from your laptop ([projects](https://docs.livekit.io/reference/developer-tools/livekit-cli/projects)).
:::

:::try
With the lab up, run `curl -s 127.0.0.1:6789/metrics | grep '^livekit_participant_total'`. Join a room with `lk room join --publish-demo test` in another terminal and run it again. Which labels change? Then pick the three metrics from the list above you would page someone for, and say why.
:::

:::warn A short API secret logs an error and starts anyway
We started a throwaway `livekit/livekit-server:v1.13.11` container, outside the lab, with `--keys "k1: tooshort"`. It logged `ERROR ... secret is too short, should be at least 32 characters for security`, then `starting LiveKit server`, and kept running. Nothing stops you from shipping a weak secret, and anyone with it can sign tokens for any room. Generate secrets of 32 characters or more, and treat that log line as a failed deploy.
:::

:::note What we did not test
The lab has no domain, TLS or TURN. We didn't run the generator, Caddy, the systemd unit, Helm or a Kubernetes cluster, and we didn't probe a firewall from outside. The short-secret test passed the key on the command line, not in a config file. The alert list is our judgment, made from metric names the lab server exposed.
:::

:::say
In production, put TLS in front of 7880, give TURN its own domain and certificate, advertise the public IP, open only the media ports, and watch loss, errors and worker availability.
:::

:::check Your VM has no load balancer. What must `turn.tls_port` be, and why?
443. LiveKit advertises that port to clients, and TURN/TLS only gets through strict firewalls if it looks like HTTPS on 443.
:::

:::check On a cloud VM whose network card only has a private 10.x address, clients connect to signaling but no audio flows. What is the likely missing setting?
`rtc.use_external_ip: true`. On a cloud VM the process doesn't see its public IP, so without STUN discovery it advertises an address clients can't reach.
:::
