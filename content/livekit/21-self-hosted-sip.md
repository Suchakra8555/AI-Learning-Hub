---
title: Self-hosted SIP
summary: Run the livekit/sip service next to your server, then wire it up with an inbound trunk, a dispatch rule and an outbound trunk. Real lk sip output from the lab, a failed outbound call explained down to the SDK source, and the network settings that cause one-way audio.
time: 30 min
---

Every provider guide in LiveKit's docs tells you to point your number at `sip:<subdomain>.sip.livekit.cloud`. You run your own server, so that address doesn't exist for you. You need your own SIP service, a public address for it, and three pieces of config: a trunk for calls coming in, a rule that picks the room, and a trunk for calls going out. This lesson sets up all of it on the lab and shows what each piece printed.

## Running livekit/sip

SIP is a separate service, `livekit/sip`. The lab runs `livekit/sip:v1.23.0` as the `sip` profile of `code/livekit/lab/docker-compose.yml`:

```yaml
  sip:
    profiles: [sip]
    image: livekit/sip:v1.23.0
    network_mode: host
    volumes: ["./sip.yaml:/sip/config.yaml:ro"]   # the image runs: livekit-sip --config=/sip/config.yaml
```

Start it with `docker compose --profile sip up -d`. The image reads `/sip/config.yaml`, so mount your file at exactly that path. This is `code/livekit/lab/sip.yaml`:

```yaml
api_key: lab-key
api_secret: lab-secret-change-me-it-must-be-at-least-32-chars
ws_url: ws://127.0.0.1:7880
redis:
  address: 127.0.0.1:6379
sip_port: 5060            # SIP signaling (UDP/TCP). Must be reachable by your SIP provider.
rtp_port: 10000-10100     # shortcut: docs default is 10000-20000
use_external_ip: false    # true on a public VM, or callers get one-way audio
health_port: 8092
```

The keys match the docs' sample config ([SIP server](https://docs.livekit.io/transport/self-hosting/sip-server)). `api_key`, `api_secret` and `ws_url` let the service act on your server. `redis` must be the **same Redis** your livekit-server uses, because that is how trunks, rules and calls are shared. `sip_port` is signaling and `rtp_port` is the media range. **`use_external_ip: true`** makes the service find its public IP and put that in the SDP it sends.

The docs say 5060 and the RTP range "must be accessible from the Internet" ([SIP server](https://docs.livekit.io/transport/self-hosting/sip-server)). The port table lists SIP on 5060 over UDP and TCP, TLS on 5061 (`tls.port`), and RTP on UDP ports 10000 to 20000 ([ports and firewall](https://docs.livekit.io/transport/self-hosting/ports-firewall)). With host networking, the lab container listened on 5060 UDP and TCP on every host interface. On a real host, allow 5060 only from your provider's IP ranges. Your SIP URI is then `<your-public-ip-or-host>:5060`.

<figure>
<svg viewBox="0 0 820 330" role="img" aria-labelledby="t-shsip d-shsip">
  <title id="t-shsip">A self-hosted SIP deployment</title>
  <desc id="d-shsip">A SIP provider on the internet reaches your host on port 5060 for signaling and on the RTP port range for audio. Both go to the livekit-sip service, which reads /sip/config.yaml. livekit-sip shares Redis with livekit-server and joins rooms on livekit-server over WebRTC. The agent server also connects to livekit-server.</desc>
  <defs><marker id="ah-shsip" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect class="box" x="200" y="16" width="610" height="300" rx="14" stroke-dasharray="6 5"/>
  <text x="215" y="38" font-size="13" font-weight="700">Your host (firewall: 5060 + RTP range, provider IPs only)</text>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="10" y="120" width="140" height="70" rx="10"/><text x="80" y="150">SIP provider</text><text x="80" y="170" font-size="12" class="small">public internet</text>
    <rect class="box" x="220" y="76" width="140" height="44" rx="8"/><text x="290" y="103" font-size="13">5060 UDP/TCP</text>
    <rect class="box" x="220" y="190" width="140" height="44" rx="8"/><text x="290" y="217" font-size="13">RTP 10000-20000</text>
    <rect class="box hot" x="400" y="110" width="150" height="90" rx="10"/><text x="475" y="148">livekit-sip</text><text x="475" y="170" font-size="12" class="small">/sip/config.yaml</text>
    <rect class="box" x="600" y="56" width="190" height="44" rx="8"/><text x="695" y="83">Redis (shared)</text>
    <rect class="box" x="600" y="150" width="190" height="50" rx="8"/><text x="695" y="180">livekit-server</text>
    <rect class="box" x="600" y="250" width="190" height="50" rx="8"/><text x="695" y="280">Agent server</text>
  </g>
  <g font-size="12" class="small" text-anchor="middle">
    <path class="arrow" stroke-dasharray="5 5" d="M150 138 L216 100" marker-start="url(#ah-shsip)" marker-end="url(#ah-shsip)"/><text x="160" y="100">SIP</text>
    <path class="arrow" stroke-width="3" d="M150 172 L216 210" marker-start="url(#ah-shsip)" marker-end="url(#ah-shsip)"/><text x="160" y="222">RTP</text>
    <path class="arrow" stroke-dasharray="5 5" d="M360 98 L396 128" marker-end="url(#ah-shsip)"/>
    <path class="arrow" stroke-width="3" d="M360 212 L396 182" marker-start="url(#ah-shsip)" marker-end="url(#ah-shsip)"/>
    <path class="arrow" stroke-dasharray="5 5" d="M550 130 L596 82" marker-start="url(#ah-shsip)" marker-end="url(#ah-shsip)"/>
    <path class="arrow" d="M554 175 H596" marker-start="url(#ah-shsip)" marker-end="url(#ah-shsip)"/><text x="575" y="194">WebRTC</text>
    <path class="arrow" stroke-dasharray="5 5" d="M695 100 V146" marker-start="url(#ah-shsip)" marker-end="url(#ah-shsip)"/>
    <path class="arrow" d="M695 200 V246" marker-start="url(#ah-shsip)" marker-end="url(#ah-shsip)"/><text x="735" y="228">WebRTC</text>
  </g>
</svg>
<figcaption>Only livekit-sip faces the phone network. It needs the public ports. Behind it, the caller is one more participant on livekit-server.</figcaption>
</figure>

:::warn The lab's SDP answer would give a real caller one-way audio
In [the last lesson](lesson:livekit/sip-fundamentals), LiveKit's `200 OK` said "send RTP to `10.148.102.64:10060`". That is a private address, because the lab has `use_external_ip: false`. On one machine it works. A provider on the internet can't reach a private IP, so the agent's audio may still reach the caller while the caller's audio never arrives. The troubleshooting page names this as the most common self-hosted cause of one-way audio, and the fix is `use_external_ip: true` ([troubleshooting](https://docs.livekit.io/reference/telephony/troubleshooting#one-way-audio)). Check the `c=` line of the SDP answer before anything else.
:::

## Inbound trunk: who may call in

An **inbound trunk** says which calls LiveKit accepts ([inbound trunk](https://docs.livekit.io/telephony/accepting-calls/inbound-trunk)). The fields in `CreateSIPInboundTrunk` ([SIP API](https://docs.livekit.io/reference/telephony/sip-api#createsipinboundtrunk)):

- `numbers`: the numbers dialed (your provider numbers). An empty list accepts any number, but then you must set auth or `allowed_addresses`.
- `allowed_addresses`: provider IPs or CIDR blocks. An empty list accepts any address.
- `allowed_numbers`: caller numbers allowed to dial in.
- `auth_username` / `auth_password`: digest auth, the 401/407 challenge. Support varies. The docs say Twilio Elastic SIP Trunking doesn't send credentials, though TwiML does.
- `headers`, `headers_to_attributes`, `include_headers`: map SIP `X-*` headers onto participant attributes.
- `ringing_timeout`, `ringing_timeout_status` (default `486 Busy Here`), `max_call_duration`, `media` (codecs, encryption, `media_timeout`), `metadata`, `krisp_enabled`.

The docs say to create a trunk once, usually one per number, and reuse it. LiveKit caches trunks, and making one per call "can degrade reliability at scale". The lab trunk, `code/livekit/sip/inbound-trunk.json`:

```json
{ "trunk": { "name": "lab inbound", "numbers": ["+15105550100"],
             "allowed_addresses": ["127.0.0.1/32"], "krisp_enabled": false } }
```

## Dispatch rule: which room

A **dispatch rule** turns an accepted call into a room ([dispatch rule](https://docs.livekit.io/telephony/accepting-calls/dispatch-rule)). There are three kinds:

- **Individual** (`dispatch_rule_individual`) gives each caller a new room named `<room_prefix>_<caller>_<random>`. Use it for agents. `no_randomness: true` drops the suffix, so repeat callers share a room.
- **Direct** (`dispatch_rule_direct`) sends every caller to one `room_name`, with an optional `pin` the caller types followed by `#`.
- **Callee** (`dispatch_rule_callee`) names the room after the number dialed. The docs contradict themselves on whether `randomize` defaults to true or false, so set it explicitly.

`room_config.agents` dispatches agents to each new room, with `metadata` that your agent reads as `ctx.job.metadata`. `trunk_ids` limits a rule to some trunks, and an empty list matches all of them. `hide_phone_number` gives the caller a random identity and drops `sip.phoneNumber`. To keep the number out of room names too, the docs use a callee rule with `randomize: false` and put a per-call ID in the SIP `To` user. The lab rule, `code/livekit/sip/dispatch-rule.json`:

```json
{ "dispatch_rule": {
    "name": "one room per caller, echo agent",
    "rule": { "dispatchRuleIndividual": { "roomPrefix": "call-" } },
    "roomConfig": { "agents": [ { "agentName": "echo", "metadata": "{\"delay_ms\": 300}" } ] } } }
```

It uses camelCase where the docs use snake_case (`dispatch_rule_individual`). Both are standard protobuf JSON names. The CLI took the camelCase file without complaint, and we didn't try the other spelling. The agent name must match `@server.rtc_session(agent_name="echo")`. If they differ, the troubleshooting page says the call "rings, but agent doesn't answer".

## Setting it up with lk

`code/livekit/sip_setup.sh` runs six `lk sip` commands against the lab: the three `create` commands and the three `list` commands. Real output, trimmed to the IDs and the rows that matter (`...` marks cuts):

```text
$ lk sip inbound create sip/inbound-trunk.json
Using url, api-key, api-secret from environment
SIPTrunkID: ST_dhoypENZSnpK
...
SIPDispatchRuleID: SDR_QBFWgicdUUyt
...
SIPTrunkID: ST_49VEgibd5SLk

$ lk sip dispatch list
...
│ SipDispatchRuleID │ Name                            │ SipTrunks │ Type                │ RoomName                │ Pin │ Attributes │ Agents │
...
│ SDR_QBFWgicdUUyt  │ one room per caller, echo agent │ <any>     │ Individual (Caller) │ call-_<caller>_<random> │     │ map[]      │ echo   │
...
$ lk sip outbound list
...
│ ST_49VEgibd5SLk │ lab outbound (nobody answers) │ 127.0.0.1:5099 │ UDP       │ +15105550100 │                │ DISABLE    │         │          │
```

Every command also printed "Using url, api-key, api-secret from environment", because `lab.env` sets them. The dispatch list shows the room pattern `call-_<caller>_<random>`. The `_` after our `call-` prefix is LiveKit's. The docs' pattern is `<room_prefix>_<caller_number>`, so a prefix of `call` should give `call_…`. `<any>` means the rule matches every trunk. `DISABLE` in the outbound row is the media encryption setting.

## Outbound: trunk and CreateSIPParticipant

An **outbound trunk** holds the provider `address` (a host or IP, not a `sip:` URI), `numbers` to call from, `transport`, auth, and `destination_country` ([outbound trunk](https://docs.livekit.io/telephony/making-calls/outbound-trunk)). The lab trunk points at `127.0.0.1:5099`, where nothing listens, so we can watch a call fail.

To dial, you create a **SIP participant** with `CreateSIPParticipant`: `sip_trunk_id` (or an inline `trunk`), `sip_call_to`, `room_name`, `participant_identity`, plus `wait_until_answered`, `ringing_timeout` ("the upper limit is 80 seconds"), `dtmf`, `play_dialtone`, `hide_phone_number`, `media` and `display_name` ([SIP API](https://docs.livekit.io/reference/telephony/sip-api#createsipparticipant)). With `wait_until_answered`, a 486/603 rejection, a 408/480 no-answer or a 5xx trunk failure raises `SipCallError`, which carries `sip_status_code` ([outbound calls](https://docs.livekit.io/telephony/making-calls/outbound-calls#call-outcomes)). Voicemail answers with `200 OK`, so it counts as success. `code/livekit/sip_outbound.py`:

```python
p = await lk.sip.create_sip_participant(api.CreateSIPParticipantRequest(
    sip_trunk_id=trunk.sip_trunk_id, sip_call_to="+15550002222", room_name="outbound-test",
    participant_identity="callee", wait_until_answered=True, ringing_timeout=Duration(seconds=8)))
...
except api.TwirpError as e:
    print(f"after {time.monotonic() - t0:.1f}s: TwirpError {e.code}: {e.message}")
    print("  sip status:", e.metadata.get("sip_status_code"), e.metadata.get("sip_status"))
```

Real output (`livekit-api` 1.2.2):

```text
after 8.2s: TwirpError canceled: sip request timed out
  sip status: None None
```

Why no status code? Nothing at 127.0.0.1:5099 ever answered, so no SIP response existed to copy. The server gave up at our 8 s ringing timeout. The Python SDK's own HTTP timeout is set to the ringing timeout plus 2 s (`livekit/api/_dial_timeout.py`), so it didn't cut the request short. In `sip_service.py`, `_as_sip_error` turns an error into `SipCallError` only when its metadata has `sip_status_code`. Here it had none, so we got a plain `ServerError`, which `TwirpError` is an alias for. If you catch only `SipCallError`, this failure gets past your handler. Catch `ServerError` as well. A real provider that rejects the call sends a code.

## Provider setup, self-hosted

Each provider guide ([providers](https://docs.livekit.io/telephony/start/providers)) has the same steps: create a trunk at the provider, restrict it, attach a number, add the LiveKit endpoint ([SIP trunk setup](https://docs.livekit.io/telephony/start/sip-trunk-setup)). Wherever a guide says `<subdomain>.sip.livekit.cloud`, use your own `<your-public-ip-or-host>:5060`. Some details from the guides:

- **Twilio:** the origination URI ends in `;transport=tcp`. Outbound uses a credential list whose username and password match your outbound trunk ([Twilio](https://docs.livekit.io/telephony/start/providers/twilio)).
- **Telnyx:** a leading `+` in `numbers` assumes the number's Destination Number Format is `+E.164`. The outbound `address` is `sip.telnyx.com`. With a subdomain added, calls fail with `503` ([troubleshooting](https://docs.livekit.io/reference/telephony/troubleshooting)).
- **Plivo, Wavix, Sinch, didlogic, DIDWW** have their own guides. They follow the same pattern.

:::note Self-hosted vs Cloud
The API reference marks `destination_country` as required on an outbound trunk. The lab created `ST_49VEgibd5SLk` without it on self-hosted v1.23.0. It drives region pinning, which is Cloud-only. `room_preset` is documented as "Only for LiveKit Cloud", and `krisp_enabled` needs Krisp, which is Cloud-only, so the lab leaves it off. The docs say `allowed_addresses` must be "enabled for your project", and until then it is "saved but not enforced". That note is written for Cloud. We don't know whether self-hosted v1.23.0 enforces it, so also firewall 5060 to your provider's IPs. Phone Numbers (`lk number`) are Cloud-only. Use a provider trunk.
:::

:::tip CLI
From the lab, quoted as run, plus the docs' telephony CLI page ([CLI: telephony](https://docs.livekit.io/reference/developer-tools/livekit-cli/telephony)):

- `lk sip inbound create sip/inbound-trunk.json`
- `lk sip dispatch create sip/dispatch-rule.json`
- `lk sip outbound create sip/outbound-trunk.json`
- `lk sip inbound list`, `lk sip dispatch list`, `lk sip outbound list`
- `lk sip inbound create inbound-trunk.json --auth-user <sip_trunk_username> --auth-pass <sip_trunk_password>`
- `lk sip dispatch create dispatch-rule.json --trunks <trunk-id>`
- `lk sip outbound create outbound-trunk.json --transport tls`
- `lk sip participant create sip-participant.json` (add `--wait` to wait for the answer, `--timeout` to change the default `1m20s` ring)
- `lk sip inbound delete TRUNK_ID`, `lk sip dispatch delete RULE_ID`
- Shared flags: `--media-enc`, `--codecs`, `--no-default-codecs`

`update` with a file replaces the whole resource. Fields you leave out are cleared.
:::

:::try
Change `allowed_addresses` in `sip/inbound-trunk.json` to `["192.0.2.0/24"]`, which excludes 127.0.0.1. Delete the old trunk with `lk sip inbound delete ST_…`, create the new one, and run `python sip_call.py`. Before you run it, predict whether you get a `200 OK` or a 4xx. Whichever happens, you now know whether this version enforces the list.
:::

:::note What we did not test
No real provider, no public IP, no `use_external_ip: true`, no TLS, no auth challenge. We did not try the direct or callee rules, `hide_phone_number`, or an outbound call that a real endpoint rejected. We don't know if `allowed_addresses` is enforced on self-hosted. The provider steps come from the docs only.
:::

:::say
Self-hosted SIP is one more service sharing your Redis, two public port ranges, `use_external_ip: true`, and three objects you create once: an inbound trunk, a dispatch rule and an outbound trunk.
:::

:::check Calls connect and the agent's greeting reaches the caller, but the agent never hears them. Where do you look first?
At the `c=` address in the SDP answer from livekit-sip. A private address means `use_external_ip` is off, so the provider can't send the caller's RTP to the server. Then check that the RTP range is open in the firewall.
:::

:::check Your outbound error handler catches `SipCallError`, but a call to a dead trunk crashes the job. Why?
With no SIP response, there is no `sip_status_code`. The SDK raises a plain `ServerError` (`TwirpError`), not a `SipCallError`. Catch `ServerError` too.
:::

Next: [Phone features](lesson:livekit/phone-features)
