---
title: Transports and serializers: one brain, many doors
summary: A transport moves audio in and out. A serializer translates a carrier's wire format into frames. This is what lets Dograh run one pipeline for a browser and for eight phone carriers.
time: 20 min
---

Your pipeline should not know whether the caller is in a browser or on a phone. Pipecat splits that out into two layers.

## Layer 1: the transport

`BaseTransport` has two abstract methods, `input()` and `output()`. Each returns a processor. You put `transport.input()` first in the pipeline and `transport.output()` near the end. The transport object itself owns the connection and fires events such as `on_client_connected`.

Implementations in `src/pipecat/transports/`:

| Transport | Use |
|---|---|
| `daily/` | Daily's WebRTC rooms, with SIP dial-in and dial-out |
| `livekit/` | LiveKit rooms (`LiveKitTransport`) |
| `smallwebrtc/` | Peer-to-peer WebRTC with `aiortc`, no media server |
| `websocket/` | `FastAPIWebsocketTransport` and others: the door for phone carriers |
| `local/` | Microphone and speaker on your own machine |
| `whatsapp/`, `vonage/`, `moq/`, avatar transports | More specialised doors |

So Pipecat can run **on top of LiveKit** as a transport. Dograh does not. It uses `SmallWebRTCTransport` for browser tests and `FastAPIWebsocketTransport` for phone carriers. The [Voice in production track](lesson:voice-prod/how-the-platform-rides-livekit) covers a different platform that rides LiveKit.

## What the transport does with audio

`TransportParams` has the settings that matter for latency and phone audio (defaults from `base_transport.py`):

- `audio_in_sample_rate` and `audio_out_sample_rate`: `None` means "use the pipeline's", which defaults to 16,000 in and 24,000 out.
- `audio_out_10ms_chunks=4`: send audio in 40 ms pieces.
- `audio_out_end_silence_secs=2`: after an `EndFrame`, send two seconds of silence so the last word is not clipped.
- `bot_vad_stop_secs=3.0` (a Dograh-fork addition, upstream used a constant): how long with no audio before the transport decides the bot stopped speaking. This matters for realtime models, which do not send a "TTS stopped" frame. Dograh sets it to 0.5 for those.
- `audio_out_mixer`: a mixer that blends background sound into the output. Dograh uses it for ambient office noise.
- `audio_in_filter`: a noise filter on the input (RNNoise, Krisp and others exist in `audio/filters/`).

The input transport does **not** run VAD in this version. It forwards `InputAudioRawFrame` and lets the user aggregator decide.

## Layer 2: the serializer

Phone carriers do not speak Pipecat frames. They send JSON messages with base64 audio. A **serializer** converts both ways:

```python
class FrameSerializer(BaseObject):
    async def serialize(self, frame: Frame) -> str | bytes | None   # frame -> carrier message
    async def deserialize(self, data: str | bytes) -> Frame | None   # carrier message -> frame
```

You hand it to the websocket transport:

```python
FastAPIWebsocketTransport(websocket=ws, params=FastAPIWebsocketParams(
    serializer=TwilioFrameSerializer(...), audio_in_enabled=True, audio_out_enabled=True))
```

Upstream has serializers for Twilio, Telnyx, Plivo, Exotel, Vonage, Genesys and Jambonz. Dograh's fork adds **Asterisk**, **Vobiz** and **Cloudonix**. The Cloudonix one is a 64-line subclass of the Twilio serializer that renames three fields, because Cloudonix speaks Twilio's media-stream protocol.

:::note Phone audio details
Carrier audio is usually 8 kHz. Dograh's registry lists Twilio, Plivo, Telnyx, Vobiz, Exotel, Cloudonix and Asterisk at 8,000 Hz and Vonage and WhatsApp at 16,000. The earlier track [phone audio is different](lesson:voice-prod/phone-audio-is-different) explains why that matters. We did not read the Twilio serializer's byte handling, so we do not describe the codec here.
:::

## Where Dograh bent this layer

Two examples from the fork diff, both small:

- **Strategies.** The fork added `serializers/call_strategies.py` with `TransferStrategy` and `HangupStrategy`. When the pipeline ends with the reason `TRANSFER_CALL`, the serializer asks the injected transfer strategy to do the carrier call. Any other end runs the hang-up strategy. The carrier REST calls live in Dograh's backend, not in Pipecat.
- **Asterisk.** Its serializer sends raw binary mu-law frames with no JSON, treats text frames as control events, and returns nothing on an interruption because Asterisk has no "clear buffer" command. The code comment says the transport stops sending audio instead.

:::warn A side effect
In the same change, Dograh deleted Telnyx's built-in hang-up code. With no hang-up strategy configured, the Telnyx serializer only logs "No hangup strategy configured". That is fine inside Dograh and a regression for anyone else using the fork. It is a good example of why a fork is not a library.
:::

:::check Where does the code that knows Twilio's message format live, the transport or the serializer?
The serializer. The transport only moves bytes over a websocket. Swapping carriers means swapping the serializer.
:::

:::check Why does Dograh lower bot_vad_stop_secs to 0.5 for realtime models?
Realtime models do not emit a "TTS stopped" frame, so the transport guesses the bot stopped from silence. The default guess is 3 seconds, which would make "bot stopped speaking" fire far too late.
:::
