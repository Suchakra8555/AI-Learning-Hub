---
title: The server API
summary: How your backend creates and deletes rooms, lists and removes participants, changes permissions and mutes tracks, with no audio involved. Twirp over HTTP, every RoomService method and which ones work self-hosted, the Python LiveKitAPI client, and the participant count that lags.
time: 20 min
---

A call is running and your backend has to act on it. A supervisor wants a list of who is in the call. A caller is abusive and has to go. A call is over and the room should close now, not after a timeout. None of this needs audio, and your backend shouldn't join the room to do it. LiveKit has two kinds of SDK for this split. The **realtime SDK** (`rtc` in Python) joins a room as a participant and moves media. The **server API** is plain HTTP calls that manage rooms and participants from outside.

The lab runs livekit-server v1.13.11, `lk` v2.19.3, and the Python packages `livekit` 1.2.0 and `livekit-api` 1.2.2.

## Twirp: JSON over HTTP POST

The server API is built on **Twirp**, an RPC framework that runs over plain HTTP. Every call is a `POST` of a JSON body to `/twirp/livekit.RoomService/<MethodName>`, with `Authorization: Bearer <token>`. Methods that take no arguments get `{}`. Keys can be `snake_case` or `camelCase` ([RoomService API](https://docs.livekit.io/reference/other/roomservice-api)). Any server node can answer for any room, so in a multi-node setup it doesn't matter which one you call.

`lk room list --curl` prints the request it is about to send. Real output:

```text
Using url, api-key, api-secret from environment
curl -X POST \
	-H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJsYWIta2V5IiwiZXhwIjoxNzk0MTUxNjUwLCJuYmYiOjE3OTQxMzAwNTAsImlhdCI6MTc5NDEzMDA1MCwidmlkZW8iOnsicm9vbUxpc3QiOnRydWV9fQ.2bVW8H0W6XV1lEuFCyW42SzG7jTQ7QgWmxjUz6yqb6c' \
	-H 'X-Livekit-Request-Id: fcd17f33-e2c0-4b55-adab-46519b697608' \
	-H 'Content-Type: application/json' \
	--data '{}' \
	http://127.0.0.1:7880/twirp/livekit.RoomService/ListRooms
...
```

That bearer token is an ordinary access token, as in [the last lesson](lesson:livekit/tokens-and-grants). Decoded, its payload is `{"iss":"lab-key","exp":1794151650,"nbf":1794130050,"iat":1794130050,"video":{"roomList":true}}`. It has no `sub`, because no participant is involved. It has one grant, `roomList`, and lasts 21,600 seconds (6 hours). The Python client works the same way: for every call it mints a fresh token holding only the grant that method needs (`_auth_header` in `livekit/api/_service.py`).

<figure>
<svg viewBox="0 0 820 290" role="img" aria-labelledby="t-api-flow d-api-flow">
  <title id="t-api-flow">A server API call from your backend</title>
  <desc id="d-api-flow">Your backend signs an admin token and sends an HTTP POST with a JSON body to the Twirp endpoint on the LiveKit server. The server replies with JSON and applies the change to the room. Participants in the room then get events: a metadata change, a permission change, or a disconnect.</desc>
  <defs><marker id="ah-api-flow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g text-anchor="middle">
    <rect class="box" x="20" y="60" width="190" height="110" rx="10"/>
    <text x="115" y="92" font-size="15">Your backend</text>
    <text x="115" y="116" font-size="12" class="small">LiveKitAPI or curl</text>
    <text x="115" y="134" font-size="12" class="small">signs an admin token</text>
    <text x="115" y="152" font-size="12" class="small">no media, no room join</text>
    <rect class="box hot" x="330" y="60" width="190" height="110" rx="10"/>
    <text x="425" y="92" font-size="15">LiveKit server</text>
    <text x="425" y="116" font-size="12" class="small">/twirp/livekit.</text>
    <text x="425" y="134" font-size="12" class="small">RoomService/&lt;Method&gt;</text>
    <text x="425" y="152" font-size="12" class="small">checks the grant</text>
    <rect class="box" x="640" y="40" width="160" height="44" rx="10"/><text x="720" y="67" font-size="14">caller</text>
    <rect class="box" x="640" y="94" width="160" height="44" rx="10"/><text x="720" y="121" font-size="14">agent</text>
    <rect class="box" x="640" y="148" width="160" height="44" rx="10"/><text x="720" y="175" font-size="14">recorder</text>
  </g>
  <path class="arrow" d="M210 95 H326" marker-end="url(#ah-api-flow)"/>
  <path class="arrow" d="M330 140 H214" marker-end="url(#ah-api-flow)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M520 100 L636 62" marker-end="url(#ah-api-flow)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M520 116 H636" marker-end="url(#ah-api-flow)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M520 132 L636 170" marker-end="url(#ah-api-flow)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="270" y="86">POST JSON</text>
    <text x="270" y="158">JSON reply</text>
    <text x="420" y="225">Participants never see the HTTP call. They see its effect as SDK events:</text>
    <text x="420" y="245">metadata changed, permissions changed, or disconnected with a reason.</text>
  </g>
</svg>
<figcaption>The backend talks HTTP to the server. The server turns each call into a change in the room, which participants see as ordinary events.</figcaption>
</figure>

## Every RoomService method

| Method | What it does | Grant the SDK sends | Self-hosted |
|---|---|---|---|
| `CreateRoom` | Create a room with timeouts, `max_participants`, metadata, auto-egress | `roomCreate` | Yes |
| `ListRooms` | List open rooms, optionally by name | `roomList` | Yes |
| `DeleteRoom` | Close a room and disconnect everyone in it | `roomCreate` | Yes |
| `UpdateRoomMetadata` | Set room metadata; every participant is told | `roomAdmin` | Yes |
| `ListParticipants` | List participants with state, tracks, permissions | `roomAdmin` | Yes |
| `GetParticipant` | One participant's details, including track sids | `roomAdmin` | Yes |
| `RemoveParticipant` | Disconnect a participant | `roomAdmin` | Yes, without token revocation |
| `UpdateParticipant` | Change metadata, name, attributes or permissions | `roomAdmin` | Yes |
| `MutePublishedTrack` | Mute or unmute a participant's track | `roomAdmin` | Yes |
| `UpdateSubscriptions` | Subscribe or unsubscribe a participant to track sids | `roomAdmin` | Yes |
| `SendData` | Send a data packet to some or all participants | `roomAdmin` | Yes |
| `MoveParticipant` | Move a participant to another room | `roomAdmin` + `destinationRoom` | No, Cloud-only |
| `ForwardParticipant` | Share a participant's tracks into other rooms | `roomAdmin` + `destinationRoom` | No, Cloud-only |

Methods and descriptions come from the [RoomService API](https://docs.livekit.io/reference/other/roomservice-api) and [participant management](https://docs.livekit.io/intro/basics/rooms-participants-tracks/participants) pages. The grant column is what `livekit/api/room_service.py` puts in each request's token. `CreateRoom` is optional, since the first join creates a room anyway. Remote unmute is off by default for privacy. `MutePublishedTrack` with `muted=false` needs `enable_remote_unmute` in the server config.

## The Python client

`api.LiveKitAPI()` is the single entry point. With no arguments it reads `LIVEKIT_URL`, `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` from the environment ([room management](https://docs.livekit.io/intro/basics/rooms-participants-tracks/rooms#initialize-livekitapi)). It has six sub-clients: `room`, `egress`, `ingress`, `sip`, `agent_dispatch` and `connector`. A failed call raises an error carrying a code and a message. In `livekit-api` 1.2.2 each request times out after 10 seconds by default.

`code/livekit/room_admin.py` walks through most of the room methods:

```python
async with api.LiveKitAPI() as lk:           # reads LIVEKIT_URL / _API_KEY / _API_SECRET
    room = await lk.room.create_room(api.CreateRoomRequest(
        name=ROOM, empty_timeout=60, departure_timeout=10, max_participants=5,
        metadata=json.dumps({"purpose": "lesson"})))
    alice = await join("alice", ROOM)
    await join("bob", ROOM)
    await asyncio.sleep(1)
    rooms = await lk.room.list_rooms(api.ListRoomsRequest())
    parts = await lk.room.list_participants(api.ListParticipantsRequest(room=ROOM))
    await lk.room.update_room_metadata(api.UpdateRoomMetadataRequest(room=ROOM, metadata='{"stage":"live"}'))
    p = await lk.room.update_participant(api.UpdateParticipantRequest(
        room=ROOM, identity="bob", attributes={"role": "listener"},
        permission=api.ParticipantPermission(can_subscribe=True, can_publish=False)))
    await lk.room.remove_participant(api.RoomParticipantIdentity(room=ROOM, identity="bob"))
    try:
        await lk.room.move_participant(api.MoveParticipantRequest(room=ROOM, identity="alice", destination_room="elsewhere"))
    except api.TwirpError as e:
        print(f"MoveParticipant    -> {e.code}: {e.message}  (Cloud-only)")
    await lk.room.delete_room(api.DeleteRoomRequest(room=ROOM))
```

Real output:

```text
CreateRoom         -> lesson-admin sid=RM_8XZDpoF5GKtA max_participants=5
ListRooms          -> [('lesson-rpt', 0), ('lesson-admin', 0)]
ListParticipants   -> [('alice', 'ACTIVE'), ('bob', 'ACTIVE')]
UpdateRoomMetadata -> alice now sees {"stage":"live"}
UpdateParticipant  -> bob attributes={'role': 'listener'} can_publish=False
RemoveParticipant  -> left: ['alice']
MoveParticipant    -> unknown: not implemented  (Cloud-only)
DeleteRoom         -> alice connected: False
```

Look at the second and third lines together. One second after both joined, `ListRooms` said `lesson-admin` had 0 participants, while `ListParticipants` returned alice and bob, both ACTIVE. The CLI tour showed the same lag: `lk room list` printed 0 participants for `demo` while `lk room participants list demo` printed `bot (ACTIVE)`, and the next `lk room update` returned `"numParticipants": 1`. The room's count is updated lazily. The docs don't say when it catches up, so we can't give you a delay. `ListRooms` also still listed `lesson-rpt`, the room from the earlier participants script, with a count of 0.

The rest worked as documented. Alice saw the new room metadata within half a second. `DeleteRoom` disconnected her. `MoveParticipant` came back with `unknown: not implemented`.

:::note Self-hosted vs Cloud
`MoveParticipant` and `ForwardParticipant` are LiveKit Cloud features. On the lab, `MoveParticipant` returned `unknown: not implemented`. We didn't call `ForwardParticipant`. The docs mark it Cloud-only too. `RemoveParticipant` works self-hosted, but only Cloud also revokes the removed participant's token, and `revoke_token_ts` is Cloud-only ([remove participant](https://docs.livekit.io/intro/basics/rooms-participants-tracks/participants#removeparticipant)). Self-hosted, to move someone, remove them and give them a token for the new room. To stop them coming back, keep TTLs short and don't re-issue.
:::

:::tip CLI
- `lk room list --curl` (prints the raw Twirp request)
- `lk room create --empty-timeout 120 --departure-timeout 10 demo`
- `lk room update --metadata '{"topic": "Weekly sync"}' my-room`
- `lk room delete ROOM_NAME`
- `lk room participants list ROOM_NAME`
- `lk room participants get --room NAME IDENTITY`
- `lk room participants remove --room NAME IDENTITY`
- `lk room participants update --room my-room --permissions '{"can_publish": true}' alice`
- `lk room send-data --room my-room --topic chat '{"message": "Hello, everyone"}'`

From the [CLI reference](https://docs.livekit.io/reference/developer-tools/livekit-cli/rooms). `lk room participants move` and `forward` exist, but they need Cloud.
:::

:::try
Copy the curl command from `lk room list --curl`. Change the path to `/twirp/livekit.RoomService/ListParticipants` and the body to `{"room": "demo"}`, and send it. Predict the result before you run it. (The token only has `roomList`, so expect a permission error. Then mint one with `lk token create --admin --room demo --token-only` and try again.)
:::

:::warn Don't trust `num_participants`
`ListRooms` reported 0 participants in a room where two were ACTIVE. If your backend uses that number to decide whether a call is empty, whether to bill, or whether to close the room, it will be wrong for a while after joins and leaves. Use `ListParticipants` for the real list, or count participant webhooks. Also note that `num_participants` leaves out hidden participants by design.
:::

:::note What we did not test
We didn't call `MutePublishedTrack`, `UpdateSubscriptions`, `ForwardParticipant` or `SendData` from Python. (`lk room send-data` did report success on the lab.) We didn't try the curl request by hand, and didn't measure how long `num_participants` takes to catch up. The grant per method comes from the Python SDK source.
:::

:::say
The server API is plain HTTP POSTs to Twirp endpoints, signed with an admin token. It manages rooms and participants from outside, and on self-hosted LiveKit everything works except moving and forwarding participants.
:::

:::check Your billing job calls `ListRooms` and charges for rooms where `num_participants > 0`. What goes wrong, and what should it call instead?
The count is updated lazily. On the lab it read 0 with two participants ACTIVE, so short calls could be missed or counted late. Call `ListParticipants` per room, or build usage from `participant_joined` and `participant_left` webhooks.
:::

:::check How do you move a caller from one room to another on self-hosted LiveKit?
`MoveParticipant` isn't implemented there. Remove the caller with `RemoveParticipant` and give their client a token for the new room.
:::

Next: [Webhooks and events](lesson:livekit/webhooks-and-events)
