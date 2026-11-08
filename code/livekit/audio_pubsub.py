"""Raw audio in and out: publish a tone, subscribe to it, see what arrives.

Run:  source lab.env && python audio_pubsub.py

The publisher hands the SDK 10 ms frames of PCM at 8 kHz (phone rate). The SDK
encodes Opus and sends RTP. The subscriber asks for 16 kHz, the usual STT rate,
and the SDK resamples for it. Nobody in this script touches a codec.
"""
import asyncio
import math
import struct
import time

from livekit import rtc

from lk_lab import join, tone

ROOM, PUB_RATE, SUB_RATE = "lesson-media", 8000, 16000


async def main():
    talker = await join("talker", ROOM)
    src = rtc.AudioSource(PUB_RATE, 1)                    # what we push in
    await talker.local_participant.publish_track(
        rtc.LocalAudioTrack.create_audio_track("tone", src),
        rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))

    listener = rtc.Room()
    got = asyncio.get_running_loop().create_future()
    listener.on("track_subscribed", lambda t, *_: got.done() or got.set_result(t))
    from lk_lab import URL, token
    await listener.connect(URL, token("listener", ROOM))

    async def speak(seconds=3):
        n = PUB_RATE // 100
        for i in range(seconds * 100):
            await src.capture_frame(tone(PUB_RATE, hz=440, ms=10, start=i * n))  # paced by the source queue

    pump = asyncio.create_task(speak())
    track = await got
    stream = rtc.AudioStream(track, sample_rate=SUB_RATE, num_channels=1)
    frames, first, start = 0, None, time.monotonic()
    rms_vals, sizes = [], set()
    async for ev in stream:
        f = ev.frame
        frames += 1
        sizes.add((f.sample_rate, f.samples_per_channel))
        s = struct.unpack(f"<{len(f.data)}h", bytes(f.data))
        r = math.sqrt(sum(x * x for x in s) / len(s))
        rms_vals.append(r)
        if first is None and r > 1000:
            first = time.monotonic() - start
        if time.monotonic() - start > 3:
            break
    pump.cancel()
    loud = [r for r in rms_vals if r > 1000]
    print(f"published at {PUB_RATE} Hz, subscribed at {SUB_RATE} Hz")
    print(f"frames received: {frames}, (rate, samples per frame): {sorted(sizes)}")
    print(f"first loud frame after {first:.2f} s; loud frames: {len(loud)}")
    print(f"rms of loud frames ~ {sum(loud)/len(loud):.0f} (a sine of amplitude 8000 has rms {8000/math.sqrt(2):.0f})")
    await listener.disconnect()
    await talker.disconnect()


asyncio.run(main())
