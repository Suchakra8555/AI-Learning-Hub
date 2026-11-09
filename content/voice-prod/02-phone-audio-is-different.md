---
title: Phone audio is different
summary: Phone carriers send 8 kHz µ-law in 20 ms frames. Your media stack wants PCM16 in its own frame size. Learn the conversion, what it costs, and the one step we chose not to do.
time: 20 min
---

You wire a phone number to your agent, and the first test call sounds like static. Or the agent hears the caller fine, but the caller hears clicks. The cause is nearly always the same. Phone audio arrives in a format your media stack does not use, cut into frames of a size it does not use either.

## Two separate questions: codec and sample rate

People mix these up. Keep them apart.

- **Sample rate** is how many times per second the sound is measured. Phone calls use 8,000 (8 kHz). WebRTC audio with **Opus**, the codec WebRTC rooms use, runs at a 48 kHz clock ([RFC 7587](https://datatracker.ietf.org/doc/html/rfc7587)).
- **Codec** is how each measurement is written down. **PCM16** writes each sample as a signed 16-bit number, 2 bytes. **µ-law** (G.711) squeezes each sample into 1 byte, spending more precision on quiet sounds than on loud ones ([ITU-T G.711](https://www.itu.int/rec/T-REC-G.711)).

So changing µ-law to PCM16 is a codec change. Going from 8 kHz to 48 kHz is a rate change. They are different jobs and they can live in different places.

## What one frame looks like

A **frame** is a fixed slice of audio sent as one unit. Twilio and Vobiz both send one JSON message per 20 ms, with the audio as base64 µ-law at 8 kHz ([Twilio](https://www.twilio.com/docs/voice/media-streams/websocket-messages), [Vobiz](https://www.vobiz.ai/docs/xml/stream/stream-events)). 20 ms at 8 kHz is 160 samples, so 160 bytes of µ-law.

<figure>
<svg viewBox="0 0 900 250" role="img" aria-labelledby="t-frame d-frame">
  <title id="t-frame">One phone frame on its way in and out</title>
  <desc id="d-frame">Inbound: a carrier JSON message with 216 base64 characters decodes to 160 bytes of mu-law, then 320 bytes of PCM16 at 8 kHz, which goes to LiveKit as a 160-sample frame, and the SDK resamples it for the room. Outbound: the room gives 10 ms frames of 160 bytes, a chunker joins two into 320 bytes, that becomes 160 bytes of mu-law and goes back in a JSON message.</desc>
  <defs><marker id="ah-frame" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="10" y="20" font-size="14" font-weight="700">Caller to agent, every 20 ms</text>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="10" y="30" width="150" height="60" rx="10"/><text x="85" y="56">Carrier JSON</text><text x="85" y="76" font-size="12" class="small">216 base64 chars</text>
    <rect class="box" x="192" y="30" width="150" height="60" rx="10"/><text x="267" y="56">µ-law</text><text x="267" y="76" font-size="12" class="small">160 bytes</text>
    <rect class="box hot" x="374" y="30" width="150" height="60" rx="10"/><text x="449" y="56">PCM16, 8 kHz</text><text x="449" y="76" font-size="12" class="small">320 bytes</text>
    <rect class="box" x="556" y="30" width="150" height="60" rx="10"/><text x="631" y="56">LiveKit frame</text><text x="631" y="76" font-size="12" class="small">160 samples</text>
    <rect class="box" x="738" y="30" width="150" height="60" rx="10"/><text x="813" y="56">Room</text><text x="813" y="76" font-size="12" class="small">SDK resamples</text>
  </g>
  <path class="arrow" d="M160 60 H188" marker-end="url(#ah-frame)"/>
  <path class="arrow" d="M342 60 H370" marker-end="url(#ah-frame)"/>
  <path class="arrow" d="M524 60 H552" marker-end="url(#ah-frame)"/>
  <path class="arrow" d="M706 60 H734" marker-end="url(#ah-frame)"/>
  <text x="10" y="140" font-size="14" font-weight="700">Agent to caller</text>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="10" y="150" width="150" height="60" rx="10"/><text x="85" y="176">Carrier JSON</text><text x="85" y="196" font-size="12" class="small">one per 20 ms</text>
    <rect class="box" x="192" y="150" width="150" height="60" rx="10"/><text x="267" y="176">µ-law</text><text x="267" y="196" font-size="12" class="small">160 bytes</text>
    <rect class="box hot" x="374" y="150" width="150" height="60" rx="10"/><text x="449" y="176">Chunker</text><text x="449" y="196" font-size="12" class="small">2 in, 320 B out</text>
    <rect class="box" x="556" y="150" width="150" height="60" rx="10"/><text x="631" y="176">PCM16, 8 kHz</text><text x="631" y="196" font-size="12" class="small">10 ms = 160 B</text>
    <rect class="box" x="738" y="150" width="150" height="60" rx="10"/><text x="813" y="176">Room</text><text x="813" y="196" font-size="12" class="small">agent speaks</text>
  </g>
  <path class="arrow" d="M738 180 H710" marker-end="url(#ah-frame)"/>
  <path class="arrow" d="M556 180 H528" marker-end="url(#ah-frame)"/>
  <path class="arrow" d="M374 180 H346" marker-end="url(#ah-frame)"/>
  <path class="arrow" d="M192 180 H164" marker-end="url(#ah-frame)"/>
  <text x="449" y="238" font-size="12" class="small" text-anchor="middle">The bridge changes the codec and the frame size. It never changes the sample rate.</text>
</svg>
<figcaption>One 20 ms frame, with byte sizes. The highlighted step is where the size doubles or the frame count halves.</figcaption>
</figure>

Base64 turns every 3 bytes into 4 characters, so 160 bytes become 216 characters. The JSON wrapper adds more. You send about twice the bytes you need, 50 times a second, per call.

## The conversion, by hand

`code/voice-prod/mulaw.py` does the whole thing with the standard library. Encoding takes the sign, adds a bias, finds which of 8 loudness segments the sample falls in, and keeps 4 bits of detail inside it. Decoding runs this backwards. Since there are only 256 possible bytes, decoding is a table lookup:

```python
def encode_sample(s):
    """One signed 16-bit sample -> one mu-law byte (the G.711 algorithm)."""
    sign = 0x80 if s < 0 else 0
    s = min(abs(s), CLIP) + BIAS
    exp = max(0, s.bit_length() - 8)          # which of 8 segments
    mant = (s >> (exp + 3)) & 0x0F
    return ~(sign | (exp << 4) | mant) & 0xFF

DECODE = [decode_byte(b) for b in range(256)]
```

A **frame chunker** fixes the size mismatch. It collects bytes of any length and hands out only whole frames, keeping the leftover for next time. Run `python3 code/voice-prod/mulaw.py`:

```text
20 ms at 8 kHz: 160 samples, PCM16 320 bytes, mu-law 160 bytes
round trip worst error: 125 (of peak 8000) -> lossy, but fine for speech
one minute of call audio: mu-law 480 KB, PCM16 960 KB
5 x 10 ms in -> frames out: [160, 160], left in buffer: 80 bytes
```

Five 10 ms pieces made two 20 ms frames, and half a frame waits in the buffer. Without the chunker you would send 10 ms frames to a carrier that expects 20 ms ones.

## What the platform did

The media bridge converts the codec and nothing else. It decodes with a 256-entry numpy lookup table and encodes with a vectorized version of the same G.711 math. It does not use Python's `audioop`, which did this job for years: it was deprecated in 3.11 and removed in 3.13 ([PEP 594](https://peps.python.org/pep-0594/)).

It never resamples. The bridge publishes the caller's track to LiveKit at 8 kHz and asks for the agent's audio at 8 kHz. The LiveKit SDK converts to and from the room's 48 kHz, so our code has one less step to get wrong.

On the way back, LiveKit hands the bridge 10 ms frames. The chunker joins them into the 20 ms frames Twilio and Vobiz expect. The platform runs its chunker on PCM16 (320 bytes per 20 ms), while the lab chunks µ-law (160 bytes). Both hand out whole 20 ms frames.

:::warn Gotcha from the platform
There is almost no backpressure. Caller audio goes straight into the room as it arrives. If the room or the network stalls, nothing slows the carrier down or drops old frames on purpose. On a busy host this would show up as growing delay, not as an error. We have not seen it yet. We have not tested for it either.
:::

:::try
Copy `mulaw.py` and change the tone's peak from `8000` to `30000`, then to `200`. Before you run it, guess: does the worst round-trip error stay at 125? We got 503 and 8 (the label still says "of peak 8000", since it's hard-coded). The error grows with loudness, which is the whole point of µ-law. Quiet sounds keep their detail.
:::

:::note What we did not test
The lab's output is real. The claims about the bridge and the LiveKit SDK's resampling come from reading the platform's code and comments. We did not measure the bridge's CPU per call or listen for resampling artifacts.
:::

:::say
On a phone leg, convert the codec and re-cut the frames yourself, and let the media SDK change the sample rate.
:::

:::check A carrier sends 20 ms µ-law frames at 8 kHz. How many bytes of PCM16 does one frame become?
320. That's 160 samples, 2 bytes each.
:::

:::check Why can decoding µ-law be a lookup table while encoding PCM16 usually isn't?
A µ-law byte has only 256 values, so you can precompute every answer. A 16-bit sample has 65,536 values. You could build that table too, but people compute the encode instead.
:::
