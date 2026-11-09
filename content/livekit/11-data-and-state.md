---
title: Data and state
summary: Everything a room carries besides audio and video. Text and byte streams, RPC, data packets, data tracks, participant attributes and metadata, and room metadata, with their limits, the topics agents use, and two gotchas we hit on the lab.
time: 25 min
---

Your agent speaks. The web page should show the transcript as it goes, a "thinking" badge while the LLM runs, and a map when the agent asks "where are you?". None of that is audio. LiveKit gives you six ways to send it, and picking the wrong one gets you a message that late joiners never see, a 15 KiB wall, or an update that fails without telling you. This lesson goes through them on the lab: livekit-server v1.13.11 and the Python `livekit` SDK 1.2.0.

## Text streams and byte streams

A **text stream** sends a string of any length to other participants. The SDK cuts it into chunks and puts it back together. Each stream has a **topic**, a string name, and the receiver registers one handler per topic ([LiveKit: sending text](https://docs.livekit.io/transport/data/text-streams)). Use `send_text` when you have the whole string, or `stream_text` to write it piece by piece, as an LLM produces tokens.

A **byte stream** is the same idea for binary data: files, images, anything. It carries a name and a MIME type ([LiveKit: sending files & bytes](https://docs.livekit.io/transport/data/byte-streams)). Receivers refuse payloads over `max_payload_byte_length`, which defaults to 5 GB.

Both are reliable and both can go to everyone or only to `destination_identities`. Two limits to plan around:

- **Late joiners miss it.** Only participants connected when the stream opens receive it.
- **No persistence.** If you need chat history, store it yourself.

Agents use two reserved topics ([LiveKit: text & transcriptions](https://docs.livekit.io/agents/multimodality/text)). The agent publishes transcripts on **`lk.transcription`**, with attributes such as `lk.transcribed_track_id` and `lk.transcription_final`. It listens on **`lk.chat`** for text the user types, and it stops speaking to answer it.

## RPC

**RPC** (remote procedure call) lets one participant call a named method on another and wait for the reply. It suits "agent asks the browser for the user's location" ([LiveKit: RPC](https://docs.livekit.io/transport/data/rpc)). The limits:

- Method name: up to 64 bytes. Payload: a string up to 15 KiB, each way.
- Timeout: 10 s by default, covering the whole round trip, so the handler gets less than that.
- Errors: built-in codes 1400 to 1404 (method not supported, recipient not found, request too large, server or version unsupported) and 1500 to 1505 (application error, connection timeout, response timeout, recipient disconnected, response too large, send failed). Any other exception in a handler reaches the caller as 1500. Codes 1001 to 1999 are reserved for LiveKit.

## Data packets and data tracks

A **data packet** is the low-level API: one message, sent with `publish_data`, to the room or to `destination_identities`, tagged with a topic ([LiveKit: data packets](https://docs.livekit.io/transport/data/packets)).

- **Reliable**: in order, retransmitted, up to 15 KiB. It's still best effort. A participant who is disconnected at that moment never gets it, and the server doesn't buffer.
- **Lossy**: sent once, no ordering. Keep it under about 1300 bytes. A bigger packet is split, and losing any piece loses the whole thing.

A **data track** is a published track of lossy frames, for continuous data such as sensor readings or telemetry. Frames are sent once and put back in order on the subscriber. Publishing one needs the `canPublishData` grant. It supports E2EE, and unlike a stream it is visible to participants who join later, since it is a track ([LiveKit: data tracks](https://docs.livekit.io/transport/data/data-tracks)). For best reliability, keep each frame under 1200 bytes.

## State: attributes and metadata

Streams and packets are messages. **Participant attributes** and **metadata** are state: the server stores them and syncs them to everyone, including people who join later ([LiveKit: participant attributes and metadata](https://docs.livekit.io/transport/data/state/participant-attributes)).

- **Attributes**: a string key-value map, up to 64 KiB across all keys and values. Updating one key doesn't resend the others. Set a key to `""` to delete it.
- **Metadata**: one string, up to 512 KiB.
- **Room metadata**: one string for the whole room, up to 512 KiB. Only the server API can set it. Participants read it and get a `RoomMetadataChanged` event ([LiveKit: room metadata](https://docs.livekit.io/transport/data/state/room-metadata)).

All of these can start in the token. They are not for frequent updates. The docs say more than once every few seconds is too often, so use data packets for that. For anything bigger, such as a long system prompt, store it in your own database and put its ID in the metadata.

<figure>
<svg viewBox="0 0 860 380" role="img" aria-labelledby="data-t1 data-d1">
  <title id="data-t1">Choosing a data channel</title>
  <desc id="data-d1">A table comparing eight channels by delivery, size limit, audience and what late joiners see. Text stream: reliable, any length, listed identities or all, late joiners miss it. Byte stream: reliable, 5 GB receive cap, same audience, missed. RPC: request and reply, 15 KiB each way, one participant. Reliable data packet: 15 KiB, listed or all, missed. Lossy data packet: sent once, about 1300 bytes, missed. Data track: lossy and reordered, under 1200 bytes per frame is best, subscribers, late joiners see the track. Attributes: synced state, 64 KiB total, everyone, late joiners get the current value. Metadata: synced state, 512 KiB, everyone, current value.</desc>
  <g font-size="13" font-weight="700" text-anchor="start">
    <rect class="box hot" x="16" y="16" width="830" height="36" rx="6"/>
    <text x="28" y="39">Channel</text><text x="228" y="39">Delivery</text><text x="378" y="39">Size limit</text><text x="548" y="39">Goes to</text><text x="728" y="39">Late joiners</text>
  </g>
  <g font-size="12" text-anchor="start">
    <rect class="box" x="16" y="56" width="830" height="36" rx="6"/>
    <text x="28" y="79">Text stream</text><text x="228" y="79" class="small">reliable</text><text x="378" y="79" class="small">any length, chunked</text><text x="548" y="79" class="small">listed ids, or all</text><text x="728" y="79" class="small">miss it</text>
    <rect class="box" x="16" y="96" width="830" height="36" rx="6"/>
    <text x="28" y="119">Byte stream</text><text x="228" y="119" class="small">reliable</text><text x="378" y="119" class="small">5 GB receive cap</text><text x="548" y="119" class="small">listed ids, or all</text><text x="728" y="119" class="small">miss it</text>
    <rect class="box" x="16" y="136" width="830" height="36" rx="6"/>
    <text x="28" y="159">RPC</text><text x="228" y="159" class="small">request + reply</text><text x="378" y="159" class="small">15 KiB each way</text><text x="548" y="159" class="small">one participant</text><text x="728" y="159" class="small">n/a</text>
    <rect class="box" x="16" y="176" width="830" height="36" rx="6"/>
    <text x="28" y="199">Data packet, reliable</text><text x="228" y="199" class="small">ordered, resent</text><text x="378" y="199" class="small">15 KiB</text><text x="548" y="199" class="small">listed ids, or all</text><text x="728" y="199" class="small">miss it</text>
    <rect class="box" x="16" y="216" width="830" height="36" rx="6"/>
    <text x="28" y="239">Data packet, lossy</text><text x="228" y="239" class="small">sent once</text><text x="378" y="239" class="small">about 1300 B</text><text x="548" y="239" class="small">listed ids, or all</text><text x="728" y="239" class="small">miss it</text>
    <rect class="box" x="16" y="256" width="830" height="36" rx="6"/>
    <text x="28" y="279">Data track</text><text x="228" y="279" class="small">lossy, reordered</text><text x="378" y="279" class="small">under 1200 B a frame</text><text x="548" y="279" class="small">its subscribers</text><text x="728" y="279" class="small">see the track</text>
    <rect class="box" x="16" y="296" width="830" height="36" rx="6"/>
    <text x="28" y="319">Attributes</text><text x="228" y="319" class="small">synced state</text><text x="378" y="319" class="small">64 KiB total</text><text x="548" y="319" class="small">everyone</text><text x="728" y="319" class="small">get current</text>
    <rect class="box" x="16" y="336" width="830" height="36" rx="6"/>
    <text x="28" y="359">Metadata</text><text x="228" y="359" class="small">synced state</text><text x="378" y="359" class="small">512 KiB</text><text x="548" y="359" class="small">everyone</text><text x="728" y="359" class="small">get current</text>
  </g>
</svg>
<figcaption>Messages (the first five rows) reach only who is connected right now. State (the last two) is stored and synced, so late joiners get it.</figcaption>
</figure>

## On the lab

`code/livekit/data_rpc.py` joins an `agent` and a `ui` participant and tries each channel. The key lines:

```python
# handlers must be plain functions; start a task for the async read
ui.register_text_stream_handler("lk.transcription", lambda r, who: asyncio.create_task(on_text(r, who)))
await agent.local_participant.send_text("Hello, how can I help?", topic="lk.transcription")

w = await agent.local_participant.stream_bytes("receipt.txt", topic="files")
await w.write(b"x" * 50_000)
await w.aclose()

@ui.local_participant.register_rpc_method("get_location")
async def get_location(data: rtc.RpcInvocationData) -> str:
    return json.dumps({"city": "Pune", "asked_by": data.caller_identity})

await agent.local_participant.publish_data(b'{"cursor": [10, 20]}', reliable=False, topic="cursor")

try:
    await agent.local_participant.set_attributes({"state": "thinking"})   # no grant
except Exception as e:
    print(f"[agent] set_attributes without grant -> {type(e).__name__}: {e}")
...
agent2 = await join("agent2", ROOM, can_update_own_metadata=True)
await agent2.local_participant.set_attributes({"state": "thinking"})
```

Real output:

```text
[ui] text stream topic=lk.transcription from agent: 'Hello, how can I help?'
[ui] byte stream receipt.txt 50000 bytes from agent
[agent] rpc get_location -> {"city": "Pune", "asked_by": "agent"}
[agent] rpc no_such_method -> RpcError 1400: Method not supported at destination
[ui] data packet topic=cursor {"cursor": [10, 20]}
[ui] agent attributes, no grant: {}
[ui] agent2 attributes, with grant: {'state': 'thinking'}
```

The 50,000-byte stream arrived whole, well over the 15 KiB a single packet allows, because streams chunk for you. Calling a method nobody registered came back as code 1400. The lossy packet arrived, as you'd expect on one machine.

The last two lines show the first gotcha. The `except` never printed, so `set_attributes` raised nothing. Yet `ui` saw `{}`. Without the **`can_update_own_metadata`** grant the update is dropped and nothing tells you. With the grant, `agent2`'s attributes came through. The docs do say the grant is required ([LiveKit: participant attributes](https://docs.livekit.io/transport/data/state/participant-attributes#usage-from-livekit-sdks)), but the Python call won't remind you.

The other gotcha is in the first code line. In Python, stream handlers are plain functions, not `async def`. The handler starts a task, and the task does the async read. If the read fails inside that task and you don't catch `rtc.StreamError`, all you get is "Task exception was never retrieved" in the logs ([LiveKit: text streams, error handling](https://docs.livekit.io/transport/data/text-streams#error-handling)).

:::warn Attribute updates without the grant fail silently
`set_attributes` (and `set_metadata`) without `can_update_own_metadata` in the token raises no error and changes nothing. If your agent's "thinking" badge never shows, check the agent's token grants first. The reverse matters too: if attributes decide what a participant may do, don't give that participant the grant, or it can set its own permissions ([LiveKit: participant attributes, robotics](https://docs.livekit.io/robotics/media/data/participant-attributes)).
:::

The server side can write state too. From `room_admin.py` on the lab:

```text
UpdateRoomMetadata -> alice now sees {"stage":"live"}
UpdateParticipant  -> bob attributes={'role': 'listener'} can_publish=False
```

:::note Self-hosted vs Cloud
The docs mark none of these channels as Cloud-only, and all of them ran on the self-hosted lab except data tracks, which we didn't try. E2EE for data is free on both.
:::

:::tip CLI
- `lk room send-data --room my-room --topic chat '{"message": "Hello, everyone"}'` sends a data packet from the server (add `--identity ID` to target one participant)
- `lk room update --metadata '{"topic": "Weekly sync"}' my-room` sets room metadata
- `lk room participants update --room NAME [options] IDENTITY` with `--metadata METADATA` replaces a participant's metadata
- `lk room join --attribute KEY=VALUE` joins with an attribute. `--publish-data DATA` sends a data packet after joining

On the lab, `lk room send-data --room demo --topic chat {"message":"hello from the cli"}` printed "successfully sent data to room demo".
:::

:::try
In `data_rpc.py`, join a third participant `late` after `send_text` has run, and register a `lk.transcription` handler on it. Does it get the transcript? Does it see `agent2`'s attributes? Then make `get_location` sleep 12 seconds and see which RPC error code the caller gets.
:::

:::note What we did not test
We didn't publish or subscribe to a data track, use `stream_text` for token-by-token output, send a reliable packet near 15 KiB, or set room metadata from a token. We didn't test what lossy packets do on a lossy network. We read the agent topics `lk.transcription` and `lk.chat` from the docs. The lab sent its own text on `lk.transcription` and didn't run an agent here. The RPC timeout exercise is not something we ran.
:::

:::say
Streams and packets are messages for whoever is connected now, attributes and metadata are stored state for everyone, and an attribute update without `can_update_own_metadata` fails without a word.
:::

:::check The agent sends a summary as a 40 KiB JSON string with `publish_data`. What goes wrong, and what should it use?
A reliable data packet holds at most 15 KiB, so it's too big. Send it as a text stream, which chunks for you, or store it and send an ID.
:::

:::check A participant who joins mid-call should see that the agent is "thinking". Text stream or attribute?
An attribute. The server stores it and syncs it to late joiners. A text stream reaches only participants connected when it opened.
:::
