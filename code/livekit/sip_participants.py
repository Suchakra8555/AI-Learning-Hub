"""List everyone in live call rooms, with their kind and attributes. Run it while sip_call.py is on a call.

Run:  source lab.env && python sip_participants.py
"""
import asyncio

from livekit import api


async def main():
    async with api.LiveKitAPI() as lk:
        rooms = (await lk.room.list_rooms(api.ListRoomsRequest())).rooms
        for r in [r for r in rooms if r.name.startswith("call-")]:
            for p in (await lk.room.list_participants(api.ListParticipantsRequest(room=r.name))).participants:
                print(r.name, p.identity, api.ParticipantInfo.Kind.Name(p.kind))
                if p.attributes:
                    print("  attributes:", dict(sorted(p.attributes.items())))


asyncio.run(main())
