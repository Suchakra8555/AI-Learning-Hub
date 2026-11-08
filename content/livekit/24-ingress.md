---
title: Ingress, bringing outside streams in
summary: How LiveKit's ingress service turns RTMP, WHIP and media URLs into a room participant, how to run livekit/ingress yourself, and the cpu_cost setting that stops it taking any work. With a real ffmpeg push on the lab.
time: 20 min
---

Your agent should play hold music while it looks something up, or a recorded legal notice at the start of every call. The audio exists as an MP3 on a web server. Or marketing wants to stream a demo from OBS into a room. None of these tools speak WebRTC. OBS and ffmpeg push RTMP, and the MP3 just sits at a URL. LiveKit's answer is **ingress**: a service that takes a non-WebRTC stream, transcodes it, and publishes it into a room as an ordinary participant ([ingress overview](https://docs.livekit.io/transport/media/ingress-egress/ingress)).

## Three kinds of input

You create an ingress with the `CreateIngress` API and pick an `input_type` ([ingress API](https://docs.livekit.io/reference/other/ingress/api)):

- **RTMP_INPUT** is a push. The API returns a URL and a **stream key** (a secret that names this ingress). You paste both into OBS or ffmpeg. RTMPS works too.
- **WHIP_INPUT** is a push over WebRTC. **WHIP** (WebRTC-HTTP ingestion protocol) is a simple HTTP handshake that starts a WebRTC publish.
- **URL_INPUT** is a pull. The service fetches HLS, MP4, MOV, MKV/WebM, OGG, MP3 or M4A from an HTTP server, or a stream from an SRT server. It starts as soon as you create it ([supported sources](https://docs.livekit.io/transport/media/ingress-egress/ingress#supported-sources)).

Transcoding is "the only supported behavior for RTMP and URL inputs". WHIP isn't transcoded by default, and you turn it on with `enable_transcoding` ([transcoding](https://docs.livekit.io/transport/media/ingress-egress/ingress/transcode)). Without transcoding, a WHIP stream is forwarded as is and costs very little.

RTMP and WHIP ingresses are **reusable**. When the encoder disconnects, the ingress stays valid, and the same stream key works again later. `UpdateIngress` can point it at another room. A URL ingress can't be reused: when the file ends, the participant leaves ([ingress workflow](https://docs.livekit.io/transport/media/ingress-egress/ingress#workflow)).

**Presets** set the output encoding. Audio has `OPUS_STEREO_96KBPS` and `OPUS_MONO_64KBS`. Video presets run from `H264_540P_25FPS_2_LAYERS` up to `H264_1080P_30FPS_3_LAYERS`, where layers are simulcast layers ([presets](https://docs.livekit.io/reference/other/ingress/api)).

<figure>
<svg viewBox="0 0 880 270" role="img" aria-labelledby="t-in-flow d-in-flow">
  <title id="t-in-flow">An RTMP stream becoming a room participant</title>
  <desc id="d-in-flow">Your backend calls CreateIngress on the LiveKit server and gets back a URL and stream key, which you paste into OBS or ffmpeg. The encoder pushes RTMP to the ingress service on port 1935. The ingress service transcodes the stream with GStreamer and publishes it to the LiveKit server over WebRTC as participant obs. Everyone in the room, including an agent, can subscribe to it.</desc>
  <defs><marker id="in-ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="540" y="20" width="170" height="50" rx="10"/><text x="625" y="50">Your backend</text>
    <rect class="box" x="20" y="150" width="150" height="80" rx="10"/><text x="95" y="182">OBS or ffmpeg</text><text x="95" y="204" font-size="12" class="small">H.264 + AAC in FLV</text>
    <rect class="box hot" x="250" y="150" width="210" height="80" rx="10"/><text x="355" y="178">Ingress service</text><text x="355" y="198" font-size="12" class="small">transcodes (GStreamer)</text><text x="355" y="216" font-size="12" class="small">needs cpu_cost set</text>
    <rect class="box" x="540" y="150" width="170" height="80" rx="10"/><text x="625" y="182">LiveKit server</text><text x="625" y="204" font-size="12" class="small">room ingress-test</text>
    <rect class="box" x="760" y="150" width="110" height="80" rx="10"/><text x="815" y="182">Subscribers</text><text x="815" y="204" font-size="12" class="small">agent, callers</text>
  </g>
  <path class="arrow" d="M625 70 V146" marker-end="url(#in-ah)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M540 45 H95 V146" marker-end="url(#in-ah)"/>
  <path class="arrow" d="M170 190 H246" marker-end="url(#in-ah)"/>
  <path class="arrow" d="M460 190 H536" marker-end="url(#in-ah)"/>
  <path class="arrow" d="M710 190 H756" marker-end="url(#in-ah)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="320" y="37">URL + stream key, pasted into the encoder</text>
    <text x="680" y="112">CreateIngress</text>
    <text x="210" y="182">RTMP</text><text x="210" y="212">:1935</text>
    <text x="498" y="182">WebRTC</text><text x="498" y="212">as "obs"</text>
  </g>
</svg>
<figcaption>The server hands out the URL and key. The ingress service does the transcoding and joins the room like any other participant.</figcaption>
</figure>

## Running livekit/ingress

The service reads YAML from `INGRESS_CONFIG_FILE` or `INGRESS_CONFIG_BODY`. Like egress, it needs the server's keys, `ws_url` and the **same Redis** ([self-hosting ingress](https://docs.livekit.io/transport/self-hosting/ingress)). It listens on:

- `rtmp_port` 1935 (TCP) for RTMP
- `whip_port` 8080 (TCP) for WHIP
- `http_relay_port` 9090 (TCP), between its own processes on localhost only, so keep it off the firewall
- `rtc_config.udp_port` 7885 (UDP) for WHIP's WebRTC media

The docs ask for 4 CPUs and 4 GB per instance, and a transcoding ingress can use 2 to 6 cores. Behind more than one instance, put a TCP load balancer (or an HTTP reverse proxy for WHIP). It ends TLS and health-checks the workers on `/` and `/availability` of `health_port`. Each instance exports `livekit_ingress_available` for autoscaling.

The server needs to know where ingress lives, because the server, not the ingress service, answers `CreateIngress` and builds the URL. That is the `ingress` block in `code/livekit/lab/livekit.yaml`:

```yaml
ingress:
  rtmp_base_url: rtmp://127.0.0.1:1935/live
  whip_base_url: http://127.0.0.1:8080/w
```

And the part of `code/livekit/lab/ingress.yaml` that matters most:

```yaml
rtc_config:
  udp_port: 7885
  use_external_ip: false
cpu_cost:                  # how many CPU cores each job reserves; with 0 the service warns and refuses work
  rtmp_cpu_cost: 2.0
  whip_cpu_cost: 2.0
  whip_bypass_transcoding_cpu_cost: 0.1
  url_cpu_cost: 2.0
```

## Push a test stream on the lab

`code/livekit/ingress/rtmp-ingress.json` asks for an RTMP ingress into room `ingress-test`, as participant `obs`:

```json
{
  "input_type": "RTMP_INPUT",
  "name": "lab camera",
  "room_name": "ingress-test",
  "participant_identity": "obs",
  "participant_name": "Test pattern"
}
```

```bash
lk ingress create ingress/rtmp-ingress.json
ffmpeg -re -f lavfi -i testsrc=size=640x360:rate=30 -f lavfi -i sine=frequency=440 \
  -c:v libx264 -preset veryfast -tune zerolatency -c:a aac \
  -f flv rtmp://127.0.0.1:1935/live/<stream-key>
lk ingress list
lk room participants list ingress-test
```

Real output, `out/ingress.txt`. The first two lines came from `create`, before ffmpeg started. The list ran while ffmpeg was pushing:

```text
IngressID: IN_FLado2xFeSSX Status: ENDPOINT_INACTIVE
URL: rtmp://127.0.0.1:1935/live Stream Key: vwMrBBex53aj
$ lk ingress list
┌─────────────────┬────────────┬──────────────┬──────────────┬────────────────────────────┬─────────────────────┬───────┐
│ IngressID       │ Name       │ Room         │ StreamKey    │ URL                        │ Status              │ Error │
├─────────────────┼────────────┼──────────────┼──────────────┼────────────────────────────┼─────────────────────┼───────┤
│ IN_FLado2xFeSSX │ lab camera │ ingress-test │ vwMrBBex53aj │ rtmp://127.0.0.1:1935/live │ ENDPOINT_PUBLISHING │       │
└─────────────────┴────────────┴──────────────┴──────────────┴────────────────────────────┴─────────────────────┴───────┘
$ lk room participants list ingress-test
obs (ACTIVE)	 tracks: 2
```

The ingress went from `ENDPOINT_INACTIVE` to `ENDPOINT_PUBLISHING` once ffmpeg connected. The URL is exactly `rtmp_base_url` from the server config. `obs` shows two tracks, one video and one audio, which other participants subscribe to like any others.

## Hold music and announcements

For a voice agent, a URL ingress fits short audio jobs. Create a `URL_INPUT` pointing at an MP3 or OGG of hold music with `room_name` set to the call's room. The service fetches and publishes it, and leaves when the file ends. It can't be reused, so create one per playback. Two things to plan for. The agent subscribes to every track by default, so it will hear the music too unless you limit what it listens to. And each URL job reserves whatever you set as `url_cpu_cost` (2.0 on the lab), which is a lot for one MP3.

:::note Self-hosted vs Cloud
On Cloud, ingress is ready with every project. Self-hosted, you run `livekit/ingress` as its own service, set `ingress.rtmp_base_url` and `whip_base_url` on the server, and put a TLS load balancer in front of it if you want RTMPS or HTTPS for WHIP ([self-hosting ingress](https://docs.livekit.io/transport/self-hosting/ingress)).
:::

:::tip CLI
`lk ingress create <request.json>`, `lk ingress list [--room <room>] [--id <IN_id>] [--json]`, `lk ingress update <json-with-ingress_id>`, `lk ingress delete <IN_id>` ([CLI ingress](https://docs.livekit.io/reference/developer-tools/livekit-cli/egress-ingress#ingress-commands)).
:::

:::try
Stop ffmpeg and run `lk ingress list` again. Predict the status. Then start the same ffmpeg command with the same stream key and check that `obs` comes back. Finally, run `lk ingress update '{"ingress_id": "<your IN_id>", "room_name": "another-room"}'`, push again, and find out which room `obs` joins.
:::

:::warn Leave cpu_cost unset and ingress takes no work
`cpu_cost` is how much CPU each job reserves, "in fraction of core count" per the docs. With it unset, the lab's ingress logged "max cost: 0.000000" and warned that every input's requirement was too low. The fix was to set `rtmp_cpu_cost`, `whip_cpu_cost` and `url_cpu_cost` to 2.0 and `whip_bypass_transcoding_cpu_cost` to 0.1. The docs' config sample lists the first three keys but not `url_cpu_cost`. Size the values to your machines; we didn't test how many jobs a given value admits.
:::

:::note What we did not test
Only RTMP ran. We didn't try WHIP, a URL input, SRT, RTMPS, `enable_transcoding`, presets or `UpdateIngress`. The hold-music use is a design from the docs, not something we ran. We didn't call the health or availability endpoints or run more than one ingress worker.
:::

:::say
Ingress is a separate service that turns RTMP, WHIP or a media URL into one more room participant, and it only takes work once you tell it how much CPU each job costs.
:::

:::check `lk ingress create` printed a URL of `rtmp://127.0.0.1:1935/live`, but your encoder runs on another machine. What do you change?
The server's `ingress.rtmp_base_url`. The server builds the URL from that key, so set it to a public host name (behind TLS for RTMPS) and open port 1935 to the encoder.
:::

:::check Why does an RTMP ingress stay listed after the stream stops, while a URL ingress is gone when its file ends?
RTMP and WHIP ingresses are reusable: the stream key stays valid and the ingress waits in a disconnected state. A URL ingress is a one-time pull. It starts at creation and leaves when the media is consumed.
:::

Next: [Production deployment](lesson:livekit/production-deployment)
