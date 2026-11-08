"""Talk to the echo agent and time how long your voice takes to come back.

Run:  source lab.env && python echo_check.py      (echo_agent.py must be running and dispatched to echo-test)
"""
import asyncio
import math
import struct
import time

from livekit import rtc

from lk_lab import URL, token, tone

ROOM = "echo-test"


async def main():
    room = rtc.Room()
    agent_track = asyncio.get_running_loop().create_future()
    room.on("track_subscribed", lambda t, pub, p: p.identity.startswith("agent") and not agent_track.done() and agent_track.set_result((t, p)))
    await room.connect(URL, token("caller", ROOM))
    for p in room.remote_participants.values():
        print(f"in the room: {p.identity} kind={rtc.ParticipantKind.Name(p.kind)}")
    src = rtc.AudioSource(48000, 1)
    await room.local_participant.publish_track(rtc.LocalAudioTrack.create_audio_track("mic", src))
    track, agent = await agent_track
    print(f"subscribed to {agent.identity}'s track")

    async def speak():                      # 1 s of tone, then silence
        for i in range(300):
            loud = i < 100
            await src.capture_frame(tone(48000, ms=10, amp=8000 if loud else 0, start=i * 480))

    t0 = time.monotonic()
    task = asyncio.create_task(speak())
    async for ev in rtc.AudioStream(track, sample_rate=48000, num_channels=1):
        s = struct.unpack(f"<{len(ev.frame.data)}h", bytes(ev.frame.data))
        if math.sqrt(sum(x * x for x in s) / len(s)) > 1000:
            print(f"heard my own tone back after {time.monotonic() - t0:.2f} s")
            break
    await task
    await room.disconnect()


asyncio.run(main())
