"""Everything that is not media: text streams, bytes, RPC, packets, attributes, metadata.

Run:  source lab.env && python data_rpc.py
"""
import asyncio
import json

from livekit import rtc

from lk_lab import join

ROOM = "lesson-data"


async def main():
    agent = await join("agent", ROOM)
    ui = await join("ui", ROOM)
    await asyncio.sleep(1)

    # 1. Text stream on a topic (how agents send transcripts: topic lk.transcription)
    async def on_text(reader: rtc.TextStreamReader, sender: str):
        print(f"[ui] text stream topic={reader.info.topic} from {sender}: {await reader.read_all()!r}")
    # handlers must be plain functions; start a task for the async read
    ui.register_text_stream_handler("lk.transcription", lambda r, who: asyncio.create_task(on_text(r, who)))
    await agent.local_participant.send_text("Hello, how can I help?", topic="lk.transcription")

    # 2. Byte stream (files, images)
    async def on_bytes(reader: rtc.ByteStreamReader, sender: str):
        data = b"".join([c async for c in reader])
        print(f"[ui] byte stream {reader.info.name} {len(data)} bytes from {sender}")
    ui.register_byte_stream_handler("files", lambda r, who: asyncio.create_task(on_bytes(r, who)))
    w = await agent.local_participant.stream_bytes("receipt.txt", topic="files")
    await w.write(b"x" * 50_000)
    await w.aclose()

    # 3. RPC: the agent asks the UI something and waits for the answer
    @ui.local_participant.register_rpc_method("get_location")
    async def get_location(data: rtc.RpcInvocationData) -> str:
        return json.dumps({"city": "Pune", "asked_by": data.caller_identity})
    print("[agent] rpc get_location ->", await agent.local_participant.perform_rpc(
        destination_identity="ui", method="get_location", payload="{}"))
    try:
        await agent.local_participant.perform_rpc(destination_identity="ui", method="no_such_method", payload="")
    except rtc.RpcError as e:
        print(f"[agent] rpc no_such_method -> RpcError {e.code}: {e.message}")

    # 4. Data packet, lossy (UDP-like, keep under ~1300 bytes)
    ui.on("data_received", lambda p: print(f"[ui] data packet topic={p.topic} {p.data.decode()}"))
    await agent.local_participant.publish_data(b'{"cursor": [10, 20]}', reliable=False, topic="cursor")

    # 5. Attributes: small key/value state, synced to everyone
    #    Needs the can_update_own_metadata grant. Without it the call fails quietly.
    try:
        await agent.local_participant.set_attributes({"state": "thinking"})
    except Exception as e:
        print(f"[agent] set_attributes without grant -> {type(e).__name__}: {e}")
    await asyncio.sleep(2)
    print("[ui] agent attributes, no grant:", dict(ui.remote_participants["agent"].attributes))
    agent2 = await join("agent2", ROOM, can_update_own_metadata=True)
    await agent2.local_participant.set_attributes({"state": "thinking"})
    await asyncio.sleep(2)
    print("[ui] agent2 attributes, with grant:", dict(ui.remote_participants["agent2"].attributes))
    await agent2.disconnect()
    await ui.disconnect()
    await agent.disconnect()


asyncio.run(main())
