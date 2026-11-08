---
title: Media in depth
summary: What the SDK does between your PCM frames and the other side's ears. AudioSource and AudioStream, Opus with RED and DTX, video codecs and simulcast, playout delay, noise cancellation on a self-hosted server, raw and pre-encoded media, and end-to-end encryption.
time: 25 min
---

Your phone bridge hands you 8 kHz audio. Your speech-to-text model wants 16 kHz. Between the two sits a WebRTC stack you never configured, and somehow it works. Then a caller complains about echo, or someone asks whether the media is encrypted end to end, and you realize you don't know what the SDK does with your frames. This lesson goes through it, using a lab script that publishes a tone and subscribes to it.

The lab uses livekit-server v1.13.11 and the Python `livekit` SDK 1.2.0.

## Publishing raw audio: AudioSource

To publish audio from code, you create an **AudioSource**, a buffer you push PCM frames into, and publish a track made from it ([LiveKit: processing raw tracks](https://docs.livekit.io/transport/media/raw-tracks)). **PCM** is plain uncompressed samples, here 16-bit integers. In the installed SDK its signature is:

```python
rtc.AudioSource(sample_rate, num_channels, queue_size_ms=1000)
```

You call `await source.capture_frame(frame)` once per frame. `queue_size_ms` is how much audio the source will hold before `capture_frame` makes you wait. That wait is what paces you. If you push frames faster than real time, the queue fills and `capture_frame` blocks until there's room. `code/livekit/audio_pubsub.py` pushes 300 frames of 10 ms in a plain loop, with no `sleep`, and still sends them at the right speed:

```python
src = rtc.AudioSource(PUB_RATE, 1)                    # PUB_RATE = 8000
await talker.local_participant.publish_track(
    rtc.LocalAudioTrack.create_audio_track("tone", src),
    rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))

async def speak(seconds=3):
    n = PUB_RATE // 100                                # 80 samples = 10 ms
    for i in range(seconds * 100):
        await src.capture_frame(tone(PUB_RATE, hz=440, ms=10, start=i * n))
```

## Subscribing to raw audio: AudioStream

On the other side, an **AudioStream** turns a remote track into an async iterator of PCM frames:

```python
rtc.AudioStream(track, sample_rate=48000, num_channels=1,
                frame_size_ms=None, noise_cancellation=None)
```

Those are the defaults in the installed SDK. You ask for the rate and channel count you want, and the SDK resamples for you. The docs put it this way: "When subscribing to a participant track, LiveKit automatically handles any required resampling" ([LiveKit: processing raw tracks](https://docs.livekit.io/transport/media/raw-tracks#publishing-local-audio-files)). Reading from a file is different: there, resampling is your job. `noise_cancellation` takes a filter that runs on each frame. The Krisp filters behind it need LiveKit Cloud (more below).

<figure>
<svg viewBox="0 0 860 290" role="img" aria-labelledby="med-t1 med-d1">
  <title id="med-t1">The audio path from AudioSource to AudioStream</title>
  <desc id="med-d1">On the publisher, your code pushes 10 ms PCM frames at 8 kHz into an AudioSource. The SDK encodes them with Opus and sends RTP to the LiveKit SFU, which forwards the packets without decoding them. On the subscriber, the SDK decodes Opus, resamples to the 16 kHz you asked for, and an AudioStream yields 10 ms frames of 160 samples to your code.</desc>
  <defs><marker id="med-ah1" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="13" font-weight="700" text-anchor="start">
    <text x="16" y="30">Publisher</text>
    <text x="16" y="276">Subscriber</text>
  </g>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="16" y="44" width="170" height="60" rx="10"/><text x="101" y="70">PCM, 8 kHz</text><text x="101" y="90" font-size="12" class="small">10 ms frames, your code</text>
    <rect class="box" x="226" y="44" width="170" height="60" rx="10"/><text x="311" y="70">AudioSource</text><text x="311" y="90" font-size="12" class="small">queue paces you</text>
    <rect class="box" x="436" y="44" width="170" height="60" rx="10"/><text x="521" y="70">Opus + RTP</text><text x="521" y="90" font-size="12" class="small">inside the SDK</text>
    <rect class="box hot" x="666" y="44" width="178" height="200" rx="10"/><text x="755" y="136">LiveKit SFU</text><text x="755" y="158" font-size="12" class="small">forwards packets,</text><text x="755" y="174" font-size="12" class="small">no decoding</text>
    <rect class="box" x="436" y="184" width="170" height="60" rx="10"/><text x="521" y="210">Opus decode</text><text x="521" y="230" font-size="12" class="small">inside the SDK</text>
    <rect class="box" x="226" y="184" width="170" height="60" rx="10"/><text x="311" y="210">Resample</text><text x="311" y="230" font-size="12" class="small">to 16 kHz, as asked</text>
    <rect class="box" x="16" y="184" width="170" height="60" rx="10"/><text x="101" y="210">AudioStream</text><text x="101" y="230" font-size="12" class="small">160 samples / 10 ms</text>
  </g>
  <path class="arrow" d="M186 74 H222" marker-end="url(#med-ah1)"/>
  <path class="arrow" d="M396 74 H432" marker-end="url(#med-ah1)"/>
  <path class="arrow" d="M606 74 H662" marker-end="url(#med-ah1)"/>
  <path class="arrow" d="M666 214 H610" marker-end="url(#med-ah1)"/>
  <path class="arrow" d="M436 214 H400" marker-end="url(#med-ah1)"/>
  <path class="arrow" d="M226 214 H190" marker-end="url(#med-ah1)"/>
</svg>
<figcaption>Your code only touches PCM at each end. The codec and the resampler live in the SDK, and the SFU never decodes the audio.</figcaption>
</figure>

The script subscribes at 16 kHz and measures what comes out. Real output:

```text
published at 8000 Hz, subscribed at 16000 Hz
frames received: 301, (rate, samples per frame): [(16000, 160)]
first loud frame after 0.04 s; loud frames: 297
rms of loud frames ~ 5644 (a sine of amplitude 8000 has rms 5657)
```

Every frame came out at 16000 Hz with 160 samples, which is 10 ms. The tone went in at 8 kHz, so the SDK resampled it. **RMS** (root mean square, the average loudness) was 5644 against a theoretical 5657 for that sine, so the level survived Opus and resampling almost unchanged. The first loud frame showed up 0.04 s after the stream started. That is a same-machine number and says nothing about a real network.

## Audio codec options

The lab server's room info lists these enabled codecs: PCMU, PCMA, opus, red, VP8, H264, VP9, AV1, H265 and rtx. **rtx** isn't a codec. It is the RTP retransmission format, used to resend lost packets ([RFC 4588](https://datatracker.ietf.org/doc/html/rfc4588)). Opus is the audio codec WebRTC participants use ([WebRTC from the wire up](lesson:livekit/webrtc-from-the-wire-up)). PCMU and PCMA are the G.711 phone codecs.

Three knobs matter for voice ([LiveKit: codecs and more](https://docs.livekit.io/transport/media/advanced)):

- **RED** (redundant encoding) sends each audio frame again inside later packets, so a lost packet can be rebuilt from the next one. It costs bandwidth. LiveKit recommends leaving it on, "because audio glitches are so distracting". You can turn it off with `red=False` in `TrackPublishOptions`.
- **DTX** (discontinuous transmission) sends almost nothing during silence. The hi-fi examples turn it off with `dtx=False`. Both `dtx` and `red` are fields of the Python `TrackPublishOptions`.
- **Audio presets** set bitrate and channels. The docs show `AudioPresets.musicHighQualityStereo` (in Rust, `MUSIC_HIGH_QUALITY_STEREO`) for music, and up to 510 kbps stereo. A voice agent doesn't need any of this. Leave the defaults.

## Video: codecs, simulcast, dynacast, adaptive stream

Most voice agents publish no video. You'll still meet these terms. The docs list H.264, VP8, VP9 and AV1 ([LiveKit: video codec support](https://docs.livekit.io/transport/media/advanced#video-codec-support)). The lab server also enabled H265, which that list doesn't name. VP9 and AV1 use **SVC** (scalable video coding): one stream holds several resolution and frame-rate layers. LiveKit turns it on with the `L3T3_KEY` scalability mode, which means three spatial and three temporal layers.

- **Simulcast**: the publisher sends the same video at several sizes, and the SFU forwards each subscriber the one it can handle. It's on by default in all SDKs ([LiveKit: video simulcast](https://docs.livekit.io/transport/media/advanced#video-simulcast)).
- **Dynacast**: the SFU tells the publisher to pause layers nobody is watching. You turn it on per room connection. In the Python SDK `RoomOptions` it defaults to `dynacast=False`. With SVC codecs it can only pause the whole stream ([LiveKit: dynacast](https://docs.livekit.io/transport/media/advanced#dynacast)).
- **Adaptive stream**: the client SDK watches the size and visibility of the element showing a video and asks the server for the layer that fits. It pauses tracks whose element is hidden. In JavaScript you must use `Track.attach()` for it to work ([LiveKit: adaptive stream](https://docs.livekit.io/transport/media/subscribe#adaptive-stream)).

<figure>
<svg viewBox="0 0 860 280" role="img" aria-labelledby="med-t2 med-d2">
  <title id="med-t2">Simulcast layers and dynacast</title>
  <desc id="med-d2">A publisher sends three simulcast layers to the SFU: 1280 by 720, 640 by 360 and 320 by 180. The SFU forwards 720p to a subscriber showing a big tile and 180p to a subscriber with a small tile or a weak network. Nobody wants the 360p layer, so dynacast has the publisher pause it.</desc>
  <defs><marker id="med-ah2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="16" y="90" width="150" height="110" rx="10"/><text x="91" y="140">Publisher</text><text x="91" y="160" font-size="12" class="small">camera, simulcast</text>
    <rect class="box hot" x="380" y="70" width="160" height="150" rx="10"/><text x="460" y="140">SFU</text><text x="460" y="160" font-size="12" class="small">one layer per</text><text x="460" y="176" font-size="12" class="small">subscriber</text>
    <rect class="box" x="674" y="50" width="170" height="64" rx="10"/><text x="759" y="78">Big tile</text><text x="759" y="98" font-size="12" class="small">gets 1280×720</text>
    <rect class="box" x="674" y="176" width="170" height="64" rx="10"/><text x="759" y="204">Small tile</text><text x="759" y="224" font-size="12" class="small">or weak network: 320×180</text>
  </g>
  <g font-size="12" class="small" text-anchor="middle">
    <path class="arrow" d="M166 104 H376" marker-end="url(#med-ah2)"/><text x="271" y="96">1280×720</text>
    <path class="arrow" stroke-dasharray="4 6" d="M166 145 H376"/><text x="271" y="137">640×360: paused (dynacast)</text>
    <path class="arrow" d="M166 186 H376" marker-end="url(#med-ah2)"/><text x="271" y="178">320×180</text>
    <path class="arrow" d="M540 90 H670" marker-end="url(#med-ah2)"/>
    <path class="arrow" d="M540 208 H670" marker-end="url(#med-ah2)"/>
    <text x="460" y="262">Adaptive stream reports each tile's size, so the SFU knows which layer to send.</text>
  </g>
</svg>
<figcaption>Simulcast gives the SFU choices. Dynacast stops the publisher from encoding a layer nobody watches.</figcaption>
</figure>

## Playout delay

**Playout delay** is how long a subscriber buffers before playing. You can set a minimum and maximum, in ms, when you create a room: `min_playout_delay` and `max_playout_delay` on `CreateRoomRequest`, both default 0 ([LiveKit: room service API](https://docs.livekit.io/reference/other/roomservice-api)). For rooms created on join, put the same fields in the token's room configuration. They apply only when the room is first created. Values apply in 10 ms steps and to every subscriber in the room ([LiveKit: playout delay hints](https://docs.livekit.io/robotics/media/performance/low-latency/playout-delay)).

For a voice agent, the part that matters is that these hints apply to **video only**. "Audio buffering is automatic and doesn't change." Setting them won't make your agent sound faster.

## Noise and echo cancellation

The WebRTC built-ins, `echoCancellation` and `noiseSuppression`, work in any deployment, self-hosted included. They run in the client during capture, set through `AudioCaptureOptions`, and the docs strongly recommend leaving them on when you don't use an enhanced model ([LiveKit: noise & echo cancellation](https://docs.livekit.io/transport/media/noise-cancellation#webrtc-noise-and-echo-cancellation)).

The enhanced models run on the agent side, on inbound audio. These are Krisp voice isolation, Krisp background voice cancellation (BVC, with `BVCTelephony()` for SIP callers) and ai-coustics. By default all of them go through LiveKit Cloud. The ai-coustics plugin has a way out: pass your own license key with `auth=Auth.ai_coustics_api(license_key=...)`, and ai-coustics bills you directly ([LiveKit: ai-coustics self-hosted authentication](https://docs.livekit.io/transport/media/noise-cancellation#self-hosted-authentication-ai-coustics)). Don't stack them. If the agent runs a noise model, turn off noise models in the frontend. WebRTC's standard noise suppression and echo cancellation can stay on.

:::note Self-hosted vs Cloud
WebRTC echo cancellation and noise suppression: everywhere. Krisp and BVC: Cloud only. ai-coustics: self-hosted works if you bring your own ai-coustics license key. E2EE: free on both.
:::

:::warn Phone callers get no client-side noise suppression
WebRTC noise suppression runs in a browser or app client. A SIP caller or a WebSocket phone bridge has no such client, so on a self-hosted server that audio reaches your agent's STT and VAD with all its background noise. The docs say to use the Cloud models for agents and telephony. Self-hosted, your options are ai-coustics with your own key, or a filter you run yourself on the `AudioStream` frames.
:::

## Raw tracks and pre-encoded media

The raw-track pattern is the one above: iterate an `AudioStream` or `VideoStream`, process each frame, push the result into a source and publish it, or write it to a file ([LiveKit: processing raw tracks](https://docs.livekit.io/transport/media/raw-tracks)). The docs point to the Agents framework for running this kind of processing as a participant that gets dispatched to rooms.

If your device already encodes video, **pre-encoded publishing** sends its frames without decoding and re-encoding them. The docs list it for Rust, C++ and the Go server SDK only, and for H.264, H.265, VP8, VP9 and AV1 ([LiveKit: pre-encoded video](https://docs.livekit.io/transport/media/pre-encoded)). Python isn't listed.

## End-to-end encryption

WebRTC media is always encrypted on the wire (DTLS-SRTP), but the SFU holds the keys for that leg. **E2EE** (end-to-end encryption) adds a layer the server can't read. It covers media tracks and, with the `encryption` room option, text streams, byte streams and data packets. It is free on both self-hosted and Cloud ([LiveKit: encryption](https://docs.livekit.io/transport/encryption)). Three things to know:

- **You distribute the keys.** "LiveKit does not (and cannot) store or transport encryption keys for you." The usual way is to make a shared key when you create the room and hand it out along with the token.
- **Signaling isn't covered.** Signaling messages and API calls are encrypted with TLS, but the server can read them.
- **Use `encryption`, not `e2ee`.** The old field is deprecated. Without `encryption`, data messages aren't encrypted.

An agent is just another participant, so it needs the key too. Connect with it before you start the session ([LiveKit: E2EE with agents](https://docs.livekit.io/transport/encryption/agents)):

```python
await ctx.connect(
    encryption=rtc.E2EEOptions(
        key_provider_options=rtc.KeyProviderOptions(
            shared_key=os.environ["LIVEKIT_E2EE_KEY"].encode(),
        ),
    ),
)
```

If the key is missing or wrong, the agent joins but can't decrypt. STT never produces text, and the agent never speaks.

:::tip CLI
- `lk room create --name my-robot --min-playout-delay 0 --max-playout-delay 10` sets video playout delay
- `lk room join --identity bot_user --publish-demo test_room` publishes a looping demo video
- `lk room join --identity publisher --publish video.h264 --publish audio.ogg --fps 30 --exit-after-publish my-room` publishes files (`.h264`, `.ivf` or `.ogg`)
- `lk room mute-track --room my-room --identity alice --mute TR_AMkSxxxxxx`
:::

:::try
In `audio_pubsub.py`, change `SUB_RATE` to 48000 and predict the samples per frame before you run it. Then set `PUB_RATE` to 16000 and `SUB_RATE` to 8000. Does the RMS still come out near 5657? Last, add `queue_size_ms=50` to the `AudioSource` and check whether the 3-second loop still takes 3 seconds.
:::

:::note What we did not test
We didn't turn RED or DTX on and off, publish video, or test simulcast, dynacast, adaptive stream or playout delay. We ran no noise cancellation model, Krisp or ai-coustics, and no E2EE. The docs show only `musicHighQualityStereo` among the audio presets, and we didn't check the full list. The 0.04 s first-frame time was measured with both sides on one machine.
:::

:::say
Push PCM into an AudioSource and read PCM from an AudioStream at the rate you want. The SDK does Opus and resampling, the SFU never decodes, and noise suppression for phone audio is your problem when self-hosted.
:::

:::check You set `max_playout_delay=10` to cut your agent's response latency. Why didn't anything change?
Playout delay hints apply only to video. Audio buffering is automatic and isn't affected.
:::

:::check The publisher sends 8 kHz and the subscriber asks for 16 kHz. Who resamples, and when would you have to do it yourself?
The SDK, on the subscribing side, when `AudioStream` delivers frames at the rate you asked for. You have to resample yourself when you read audio from a file and push it into a source at a different rate.
:::

Next: [Data and state](lesson:livekit/data-and-state)
