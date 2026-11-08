"""Access tokens: what is inside one, and what the server does with it.

Run:  source lab.env && python tokens.py      (lab must be running)

A token is a JWT signed with your API secret. The server checks the signature,
the time window and the grants. Nothing else proves who a participant is.
"""
import asyncio
import base64
import json
import logging
import os
from datetime import timedelta

from livekit import api, rtc

URL = os.environ["LIVEKIT_URL"]
logging.getLogger("livekit").setLevel(logging.CRITICAL)  # hide the SDK's own error logs


def payload(jwt: str) -> dict:
    body = jwt.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))


def token(identity, room, ttl=timedelta(minutes=10), **grants):
    g = api.VideoGrants(room_join=True, room=room, **grants)
    return api.AccessToken().with_identity(identity).with_grants(g).with_ttl(ttl).to_jwt()


async def try_join(label, jwt):
    room = rtc.Room()
    try:
        await room.connect(URL, jwt)
        print(f"{label:30} -> joined room '{room.name}' as {room.local_participant.identity}")
        return room
    except Exception as e:
        reason = str(e).split("invalid authorization token: ")[-1]
        print(f"{label:30} -> rejected (401): {reason}")
        return None


async def main():
    jwt = token("alice", "lesson-tokens", can_publish=False)
    claims = payload(jwt)
    print("decoded claims:", json.dumps({k: claims[k] for k in ("iss", "sub", "video")}))
    print(f"valid for {claims['exp'] - claims['nbf']} s\n")

    alice = await try_join("good token", jwt)
    other = await try_join("token naming another room", token("mallory", "other-room"))
    await other.disconnect()  # the token, not the URL, decides the room
    forged = jwt[:-4] + ("AAAA" if not jwt.endswith("AAAA") else "BBBB")
    await try_join("tampered signature", forged)
    await try_join("expired token", token("late", "lesson-tokens", ttl=timedelta(seconds=-60)))
    bad = api.AccessToken(os.environ["LIVEKIT_API_KEY"], "x" * 40).with_identity("eve") \
        .with_grants(api.VideoGrants(room_join=True, room="lesson-tokens")).to_jwt()
    await try_join("signed with the wrong secret", bad)

    # Grants are enforced after joining too: alice has can_publish=False.
    src = rtc.AudioSource(48000, 1)
    try:
        await alice.local_participant.publish_track(rtc.LocalAudioTrack.create_audio_track("mic", src))
        print(f"{'publish, can_publish=False':30} -> published (unexpected)")
    except Exception as e:
        print(f"{'publish, can_publish=False':30} -> failed: {str(e).split('error ')[-1]}")
    await alice.disconnect()


asyncio.run(main())
