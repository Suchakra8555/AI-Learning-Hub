"""The server API: what your backend can do to rooms and participants.

Run:  source lab.env && python room_admin.py

Every call here is an HTTP POST to /twirp/livekit.RoomService/<Method>,
signed with a short-lived admin token minted from your API key and secret.
"""
import asyncio
import json

from livekit import api

from lk_lab import join

ROOM = "lesson-admin"


async def main():
    async with api.LiveKitAPI() as lk:           # reads LIVEKIT_URL / _API_KEY / _API_SECRET
        room = await lk.room.create_room(api.CreateRoomRequest(
            name=ROOM, empty_timeout=60, departure_timeout=10, max_participants=5,
            metadata=json.dumps({"purpose": "lesson"})))
        print(f"CreateRoom         -> {room.name} sid={room.sid} max_participants={room.max_participants}")

        alice = await join("alice", ROOM)
        await join("bob", ROOM)
        await asyncio.sleep(1)

        rooms = await lk.room.list_rooms(api.ListRoomsRequest())
        print("ListRooms          ->", [(r.name, r.num_participants) for r in rooms.rooms])
        parts = await lk.room.list_participants(api.ListParticipantsRequest(room=ROOM))
        print("ListParticipants   ->", [(p.identity, api.ParticipantInfo.State.Name(p.state)) for p in parts.participants])

        await lk.room.update_room_metadata(api.UpdateRoomMetadataRequest(room=ROOM, metadata='{"stage":"live"}'))
        await asyncio.sleep(0.5)
        print("UpdateRoomMetadata -> alice now sees", alice.metadata)

        p = await lk.room.update_participant(api.UpdateParticipantRequest(
            room=ROOM, identity="bob", attributes={"role": "listener"},
            permission=api.ParticipantPermission(can_subscribe=True, can_publish=False)))
        print(f"UpdateParticipant  -> bob attributes={dict(p.attributes)} can_publish={p.permission.can_publish}")

        await lk.room.remove_participant(api.RoomParticipantIdentity(room=ROOM, identity="bob"))
        parts = await lk.room.list_participants(api.ListParticipantsRequest(room=ROOM))
        print("RemoveParticipant  -> left:", [p.identity for p in parts.participants])

        try:
            await lk.room.move_participant(api.MoveParticipantRequest(room=ROOM, identity="alice", destination_room="elsewhere"))
            print("MoveParticipant    -> moved")
        except api.TwirpError as e:
            print(f"MoveParticipant    -> {e.code}: {e.message}  (Cloud-only)")

        await lk.room.delete_room(api.DeleteRoomRequest(room=ROOM))
        await asyncio.sleep(0.5)
        print("DeleteRoom         -> alice connected:", alice.isconnected())


asyncio.run(main())
