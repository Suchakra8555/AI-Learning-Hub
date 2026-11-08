---
title: Egress, recording a room
summary: How LiveKit records and streams rooms with a separate egress service, which of the three sources to pick, where the files go, and how to run livekit/egress yourself. With a real recording from the lab.
time: 25 min
---

Someone asks for the recording of yesterday's call with the agent. You open the LiveKit server and find no recording setting at all, because the server doesn't record. It forwards packets. Recording means decoding, mixing, encoding and uploading, so LiveKit puts that work in a separate service called **egress**: a worker that joins a room, captures its media, and writes it to a file or a stream ([egress overview](https://docs.livekit.io/transport/media/ingress-egress/egress)).

## Why recording is its own service

Egress uses **GStreamer** (a media pipeline library) to encode. For a layout of the whole room, it also runs a headless Chrome that renders a web page and records it ([egress overview](https://docs.livekit.io/transport/media/ingress-egress/egress#service-architecture)). The docs ask for at least 4 CPUs and 4 GB of memory per egress instance, and say a room composite can use 2 to 6 CPUs ([self-hosting egress](https://docs.livekit.io/transport/self-hosting/egress)). Running it inside the SFU would take CPU away from forwarding packets on time.

The server and the worker never call each other directly. Your backend asks the server for an egress, the server puts the job on Redis, and a free egress worker takes it. The worker joins the room as a participant of kind **EGRESS**, which other participants don't see in the UI, and subscribes only to the tracks it needs ([server-side subscription](https://docs.livekit.io/transport/media/ingress-egress/egress#server-side-subscription-management)). So egress must point at the **same Redis** as the server.

<figure>
<svg viewBox="0 0 880 300" role="img" aria-labelledby="t-eg-arch d-eg-arch">
  <title id="t-eg-arch">How an egress request becomes a file</title>
  <desc id="d-eg-arch">Your backend sends StartEgress to the LiveKit server. The server queues the job on Redis. An egress worker picks it up, joins the room as a hidden EGRESS participant and receives the tracks over WebRTC. GStreamer inside the worker encodes them, and the result is uploaded to storage.</desc>
  <defs><marker id="eg-ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="20" y="40" width="170" height="70" rx="10"/><text x="105" y="70">Your backend</text><text x="105" y="92" font-size="12" class="small">or lk egress start</text>
    <rect class="box hot" x="290" y="40" width="210" height="70" rx="10"/><text x="395" y="70">LiveKit server</text><text x="395" y="92" font-size="12" class="small">room "record-me"</text>
    <rect class="box" x="600" y="40" width="200" height="70" rx="10"/><text x="700" y="70">Redis</text><text x="700" y="92" font-size="12" class="small">job queue + status</text>
    <rect class="box" x="600" y="200" width="200" height="80" rx="10"/><text x="700" y="230">Egress worker</text><text x="700" y="252" font-size="12" class="small">joins as kind EGRESS</text><text x="700" y="268" font-size="12" class="small">hidden from the UI</text>
    <rect class="box" x="290" y="200" width="210" height="80" rx="10"/><text x="395" y="230">Encode (GStreamer)</text><text x="395" y="252" font-size="12" class="small">Opus, H.264, HLS</text><text x="395" y="268" font-size="12" class="small">Chrome only for layouts</text>
    <rect class="box" x="20" y="200" width="170" height="80" rx="10"/><text x="105" y="230">Storage</text><text x="105" y="252" font-size="12" class="small">S3, MinIO, GCS, Azure</text><text x="105" y="268" font-size="12" class="small">or a local folder</text>
  </g>
  <path class="arrow" d="M190 75 H286" marker-end="url(#eg-ah)"/>
  <path class="arrow" d="M500 75 H596" marker-end="url(#eg-ah)"/>
  <path class="arrow" d="M700 110 V196" marker-end="url(#eg-ah)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M470 112 L620 196" marker-end="url(#eg-ah)"/>
  <path class="arrow" d="M600 240 H504" marker-end="url(#eg-ah)"/>
  <path class="arrow" d="M290 240 H194" marker-end="url(#eg-ah)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="238" y="66">StartEgress</text>
    <text x="548" y="66">queue job</text>
    <text x="745" y="160">takes job</text>
    <text x="470" y="180">tracks over WebRTC</text>
    <text x="242" y="232">upload</text>
  </g>
</svg>
<figcaption>The server only queues the job. The worker does the joining, encoding and uploading.</figcaption>
</figure>

## One API, three sources

You start every egress with **StartEgress** and set exactly one source ([StartEgress](https://docs.livekit.io/reference/other/egress/api#startegress)). Self-hosted, it needs livekit-server v1.13.5 or later. The lab runs v1.13.11, with livekit/egress v1.15.0.

- **TemplateSource** records the whole room through a layout page. It stops when the room ends. It replaces `StartRoomCompositeEgress`.
- **WebSource** records any URL in a headless browser, tied to no room. It replaces `StartWebEgress`.
- **MediaSource** captures tracks straight through the SDK, with no browser. It replaces `StartParticipantEgress`, `StartTrackCompositeEgress` and `StartTrackEgress`.

Those five older calls are deprecated ([egress sources](https://docs.livekit.io/transport/media/ingress-egress/egress#egress-sources)). The CLI's `--type` flag, which reads the old request shapes, is deprecated too ([CLI egress](https://docs.livekit.io/reference/developer-tools/livekit-cli/egress-ingress)).

For a voice agent, two options matter. A TemplateSource with `audio_only: true` gives one mixed file of the call. Leave `layout` and `custom_base_url` unset: with all three conditions met, "the service captures the room directly instead of starting a browser" ([TemplateSource](https://docs.livekit.io/reference/other/egress/api#templatesource)). A MediaSource with an **AudioConfig** puts each speaker on their own channel. Its routes match by track ID, identity or participant kind, so you can send kind `AGENT` to the left channel and everyone else to the right. That replaces the old `DUAL_CHANNEL_AGENT` mixing mode ([AudioConfig](https://docs.livekit.io/reference/other/egress/api#audioconfig)). Egress always re-encodes audio as stereo Opus. A mono source still gives a two-channel file ([track egress](https://docs.livekit.io/transport/media/ingress-egress/egress/track)).

<figure>
<svg viewBox="0 0 880 250" role="img" aria-labelledby="t-eg-pick d-eg-pick">
  <title id="t-eg-pick">Pick the egress source by what you want</title>
  <desc id="d-eg-pick">Four goals, each with its source. One mixed audio file: TemplateSource with audio_only true, no browser. A video of the room with a layout: TemplateSource with a layout, rendered in Chrome. Any web page: WebSource, Chrome. Each speaker apart, or one track: MediaSource with audio routes, no browser.</desc>
  <defs><marker id="eg-ah2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="13" text-anchor="middle">
    <rect class="box" x="20" y="20" width="192" height="50" rx="8"/><text x="116" y="50">One mixed audio file</text>
    <rect class="box" x="236" y="20" width="192" height="50" rx="8"/><text x="332" y="50">Room video, a layout</text>
    <rect class="box" x="452" y="20" width="192" height="50" rx="8"/><text x="548" y="50">Record any web page</text>
    <rect class="box" x="668" y="20" width="192" height="50" rx="8"/><text x="764" y="50">Each speaker apart</text>
    <rect class="box hot" x="20" y="110" width="192" height="64" rx="8"/><text x="116" y="136">TemplateSource</text><text x="116" y="157" font-size="12" class="small">audio_only: true</text>
    <rect class="box" x="236" y="110" width="192" height="64" rx="8"/><text x="332" y="136">TemplateSource</text><text x="332" y="157" font-size="12" class="small">layout or custom URL</text>
    <rect class="box" x="452" y="110" width="192" height="64" rx="8"/><text x="548" y="136">WebSource</text><text x="548" y="157" font-size="12" class="small">url, no room needed</text>
    <rect class="box hot" x="668" y="110" width="192" height="64" rx="8"/><text x="764" y="136">MediaSource</text><text x="764" y="157" font-size="12" class="small">audio routes, track IDs</text>
  </g>
  <path class="arrow" d="M116 70 V106" marker-end="url(#eg-ah2)"/>
  <path class="arrow" d="M332 70 V106" marker-end="url(#eg-ah2)"/>
  <path class="arrow" d="M548 70 V106" marker-end="url(#eg-ah2)"/>
  <path class="arrow" d="M764 70 V106" marker-end="url(#eg-ah2)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="116" y="200">no browser</text><text x="116" y="218">what the lab ran</text>
    <text x="332" y="200">headless Chrome</text><text x="332" y="218">2 to 6 CPUs</text>
    <text x="548" y="200">headless Chrome</text><text x="548" y="218">any http(s) page</text>
    <text x="764" y="200">no browser</text><text x="764" y="218">agent left, caller right</text>
  </g>
</svg>
<figcaption>The two highlighted sources are the ones a voice agent usually needs. Neither starts a browser.</figcaption>
</figure>

## Outputs, file names and storage

One egress can write several outputs at once: a **file** (MP4, OGG), **HLS segments**, an **RTMP or SRT stream**, and **images** (thumbnails every N seconds). A MediaSource can also stream raw audio to a **WebSocket** as `pcm_s16le` ([outputs](https://docs.livekit.io/transport/media/ingress-egress/egress/outputs), [WebSocket](https://docs.livekit.io/transport/media/ingress-egress/egress/track#stream-audio-to-websocket)). Each type allows one item: a file plus HLS works, two files don't. **Presets** pick the encoding. The default is `H264_720P_30` (1280×720, 3000 kbps), and `PASSTHROUGH` writes one video track without re-encoding ([presets](https://docs.livekit.io/reference/other/egress/api#encodingoptionspreset)).

File paths take templates such as `{room_name}`, `{room_id}`, `{time}`, `{publisher_identity}` and `{track_id}`. With no path you get `{room_name}-{time}` ([filename templating](https://docs.livekit.io/transport/media/ingress-egress/egress/outputs#filename-templating)).

Storage can be S3 or anything S3-compatible such as MinIO (set `force_path_style: true` there, and note that `endpoint` must start with `https://`), Google Cloud Storage, or Azure. Storage on the output wins over storage on the request, which wins over the worker's config ([cloud storage](https://docs.livekit.io/transport/media/ingress-egress/egress/outputs#cloud-storage-configurations)). With none of those set, a self-hosted worker writes to its own disk. That is what the lab does.

**Auto egress** starts recording when a room is created, from the `egress` field of `CreateRoom` or of a **RoomConfiguration** ([auto egress](https://docs.livekit.io/transport/media/ingress-egress/egress/autoegress), [RoomConfiguration](https://docs.livekit.io/reference/other/roomservice-api#roomconfiguration)). Its `room` field still takes the old `RoomCompositeEgressRequest` shape. For your own look, a **custom template** is a web page that reads the `url`, `token` and `layout` query parameters and logs `START_RECORDING` and `END_RECORDING` to the console ([custom templates](https://docs.livekit.io/transport/media/ingress-egress/egress/custom-template)).

## Record a room on the lab

`code/livekit/lab/egress.yaml` is the worker's config. The part that matters is the shared Redis:

```yaml
api_key: lab-key
api_secret: lab-secret-change-me-it-must-be-at-least-32-chars
ws_url: ws://127.0.0.1:7880
insecure: true
redis:
  address: 127.0.0.1:6379  # same Redis as the server: that is how the server hands it work
health_port: 8090
```

On start, the worker logged "cpu available: 12 max cost: 4" and "service ready". The request is `code/livekit/egress/room-audio.json`, a StartEgress body with an audio-only TemplateSource:

```json
{
  "room_name": "record-me",
  "template": { "audio_only": true },
  "outputs": [ { "file": { "filepath": "/out/{room_name}-{time}.ogg" } } ]
}
```

`code/livekit/record_room.sh` publishes 20 s of a 440 Hz tone from a CLI participant, then records:

```bash
chmod a+w lab/recordings   # the egress container writes the file as root
ffmpeg -nostdin -loglevel error -y -f lavfi -i sine=frequency=440:duration=20 -c:a libopus /tmp/tone.ogg
lk room join --identity speaker --publish /tmp/tone.ogg record-me >/tmp/lk-speaker.log 2>&1 &
SPEAKER=$!
sleep 3

step lk egress start egress/room-audio.json | tee /tmp/egress-start.txt
EGRESS_ID=$(grep -o 'EG_[A-Za-z0-9]*' /tmp/egress-start.txt | head -1)
sleep 10
step lk egress list --room record-me
step lk egress stop --id "$EGRESS_ID"
```

Real output, `out/record_room.txt`:

```text
$ lk egress start egress/room-audio.json
EgressID: EG_jZw5xZbYCBqk Status: EGRESS_STARTING

$ lk egress list --room record-me
┌─────────────────┬───────────────┬──────┬────────┬─────────────────────────────────────────┬───────┐
│ EgressID        │ Status        │ Type │ Source │ Started At                              │ Error │
├─────────────────┼───────────────┼──────┼────────┼─────────────────────────────────────────┼───────┤
│ EG_jZw5xZbYCBqk │ EGRESS_ACTIVE │      │        │ 2026-11-08 15:24:44.262978026 +0530 IST │       │
└─────────────────┴───────────────┴──────┴────────┴─────────────────────────────────────────┴───────┘

$ lk egress stop --id EG_jZw5xZbYCBqk
Stopping Egress EG_jZw5xZbYCBqk

$ ls -la lab/recordings/
...
-rw-r--r-- 1 user root             260 Nov  8 15:24 EG_jZw5xZbYCBqk.json
-rw-r--r-- 1 user root          152928 Nov  8 15:24 record-me-2026-11-08T095444.ogg

$ ffprobe -v error -show_entries format=duration:stream=codec_name,sample_rate,channels -of default=nw=1 lab/recordings/record-me-2026-11-08T095444.ogg
codec_name=opus
sample_rate=48000
channels=2
duration=9.366500
```

The tone lasted 20 s, but the file is 9.37 s, because a recording covers start to stop and the script stopped it about 10 s in. The tone was mono and the file has 2 channels, as the docs say. `{time}` became `095444` while the list shows 15:24:44 IST, so file names use UTC. The `Type` and `Source` columns came back empty for this StartEgress job. The JSON beside the file is a manifest:

```text
{"egress_id":"EG_jZw5xZbYCBqk","room_id":"RM_WYLDoESiwwzj","room_name":"record-me","started_at":1794131684262978026,"ended_at":1794131694588544484,"files":[{"filename":"/out/record-me-2026-11-08T095444.ogg","location":"/out/record-me-2026-11-08T095444.ogg"}]}
```

## Running livekit/egress

The worker reads YAML from `EGRESS_CONFIG_FILE` or `EGRESS_CONFIG_BODY`. It needs `api_key`, `api_secret`, `ws_url` and the server's `redis` block. Optional keys include `health_port`, `template_port` (7980), `prometheus_port`, and one `s3`, `azure` or `gcp` block ([self-hosting egress](https://docs.livekit.io/transport/self-hosting/egress)). Note that egress still uses the flat `prometheus_port`, unlike the server.

For layouts and web pages, Chrome runs with its sandbox off by default, because Docker's default seccomp profile blocks the namespace calls it needs. To turn it on, set `enable_chrome_sandbox: true` and start the container with `--security-opt seccomp=chrome-sandboxing-seccomp-profile.json`, which allows `clone` and `unshare`. The lab's compose file takes a shortcut and gives the container `cap_add: [SYS_ADMIN]`, which grants far more. The docs never mention that option.

To scale, each worker exports **`livekit_egress_available`**, worked out from its own CPU. Alert or autoscale on it, for example `sum(livekit_egress_available) > 3`. The Helm chart (`livekit/egress`) supports CPU, memory or a custom metric ([ensuring availability](https://docs.livekit.io/transport/self-hosting/egress#ensuring-availability)).

:::note Self-hosted vs Cloud
On Cloud, egress comes with every project. Self-hosted, you deploy and scale `livekit/egress` yourself. Local-folder output only works self-hosted, because on Cloud a request with no storage fails. If you would use Cloud's agent observability recordings, the self-hosted alternative is an egress recording per call ([self-hosting overview](https://docs.livekit.io/transport/self-hosting)).
:::

:::tip CLI
`lk egress start <request.json>`, `lk egress list --room <room> --active`, `lk egress stop --id <EG_id>`, `lk egress update-layout --id <EG_id> --layout grid`, `lk egress update-stream --id <EG_id> --add-urls <rtmp-url>`, `lk egress test-template --base-url <url> --publishers 4`, and `lk room create --room-egress-file <json> <room>` for auto egress ([CLI egress](https://docs.livekit.io/reference/developer-tools/livekit-cli/egress-ingress)).
:::

:::try
In `room-audio.json`, change the path to `/out/{room_name}/{time}.ogg`, and in `record_room.sh` change `sleep 10` to `sleep 15`. Before you run it, predict the new path and the ffprobe duration. Then predict what `channels` will say, and why it won't change.
:::

:::warn The file name can leak a phone number
Templates copy names into storage keys. A SIP dispatch rule names rooms like `call-_<caller>_<random>`, so `{room_name}` puts the caller's number into every object key and every bucket listing. Use `{room_id}` or your own call ID in the path. A recording is also a copy of someone's voice, so check consent before the egress starts. See [secrets, recordings and privacy](lesson:voice-prod/secrets-recordings-and-privacy).
:::

:::note What we did not test
Only one egress ran: an audio-only TemplateSource to a local folder. That path skips Chrome, so the sandbox setting was never exercised, and we don't know whether the lab even needs `SYS_ADMIN`. We didn't try S3 or MinIO, MediaSource routes, auto egress, RTMP, HLS, images or WebSocket output. We didn't scrape the egress health port, and `prometheus_port` isn't set in `lab/egress.yaml`.
:::

:::say
Recording is a separate worker that takes jobs from the server's Redis, joins the room as a hidden participant and encodes what it hears, so you size, scale and secure it on its own.
:::

:::check You want the agent on the left channel and the caller on the right. Which source, and why not TemplateSource?
A MediaSource with an AudioConfig whose routes send participant kind `AGENT` to the left channel and the rest to the right. TemplateSource with `audio_only` gives one mix, and StartEgress has no field for dual-channel mixing on it.
:::

:::check The egress container logs "service ready", but no worker ever takes your StartEgress jobs. What do you check first?
That the worker's `redis.address` is the same Redis the server uses. The server hands jobs over through Redis, so a worker on another Redis never sees them.
:::

Next: [Ingress](lesson:livekit/ingress)
