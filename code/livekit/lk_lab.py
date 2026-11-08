"""Tiny helpers shared by the lab scripts. Reads LIVEKIT_* from the environment (source lab.env)."""
import logging
import math
import os

from livekit import api, rtc

URL = os.environ["LIVEKIT_URL"]
logging.getLogger("livekit").setLevel(logging.CRITICAL)  # the SDK logs its own errors loudly


def token(identity, room, **grants):
    g = api.VideoGrants(room_join=True, room=room, **grants)
    return api.AccessToken().with_identity(identity).with_name(identity).with_grants(g).to_jwt()


async def join(identity, room, **grants) -> rtc.Room:
    r = rtc.Room()
    await r.connect(URL, token(identity, room, **grants))
    return r


def tone(source_rate=48000, hz=440, ms=10, amp=8000, start=0):
    """One frame of a sine wave, as an rtc.AudioFrame."""
    n = source_rate * ms // 1000
    frame = rtc.AudioFrame.create(source_rate, 1, n)
    data = frame.data
    for i in range(n):
        data[i] = int(amp * math.sin(2 * math.pi * hz * (start + i) / source_rate))
    return frame
