"""Rooms, participants and tracks, watched from the inside.

Run:  source lab.env && python two_participants.py

Alice joins and publishes a microphone track. Bob joins later and is
auto-subscribed. Then a second "alice" joins, and the server kicks the first.
"""
import asyncio

from livekit import rtc

from lk_lab import join, tone

ROOM = "lesson-rpt"


def watch(room: rtc.Room, who: str):
    room.on("participant_connected", lambda p: print(f"[{who}] participant_connected {p.identity} kind={rtc.ParticipantKind.Name(p.kind)}"))
    room.on("participant_disconnected", lambda p: print(f"[{who}] participant_disconnected {p.identity}"))
    room.on("track_published", lambda pub, p: print(f"[{who}] track_published {p.identity}/{pub.name} (a publication: metadata only)"))
    room.on("track_subscribed", lambda t, pub, p: print(f"[{who}] track_subscribed {p.identity}/{pub.name} kind={rtc.TrackKind.Name(t.kind)} (now media flows)"))
    room.on("disconnected", lambda reason: print(f"[{who}] disconnected reason={rtc.DisconnectReason.Name(reason)}"))


async def main():
    alice = await join("alice", ROOM)
    watch(alice, "alice")
    src = rtc.AudioSource(48000, 1)
    pub = await alice.local_participant.publish_track(
        rtc.LocalAudioTrack.create_audio_track("mic", src),
        rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
    print(f"[alice] published track sid={pub.sid} source={rtc.TrackSource.Name(pub.source)}")

    async def feed():
        i = 0
        while True:
            await src.capture_frame(tone(start=i))
            i += 480

    pump = asyncio.create_task(feed())

    await asyncio.sleep(1)
    bob = rtc.Room()
    watch(bob, "bob")
    from lk_lab import URL, token
    await bob.connect(URL, token("bob", ROOM))       # auto_subscribe defaults to True
    await asyncio.sleep(2)
    for p in bob.remote_participants.values():
        for t in p.track_publications.values():
            print(f"[bob] sees {p.identity}/{t.name} subscribed={t.subscribed}")

    print("\n-- a second 'alice' joins with the same identity --")
    alice2 = await join("alice", ROOM)
    await asyncio.sleep(2)
    print(f"[alice2] connected={alice2.isconnected()}  [alice] connected={alice.isconnected()}")

    pump.cancel()
    for r in (alice2, bob):
        await r.disconnect()


asyncio.run(main())
