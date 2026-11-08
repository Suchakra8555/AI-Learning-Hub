"""Place an outbound call and handle failure. The lab's outbound trunk points at a port where nobody listens.

Run:  source lab.env && python sip_outbound.py
"""
import asyncio
import time

from google.protobuf.duration_pb2 import Duration
from livekit import api


async def main():
    async with api.LiveKitAPI() as lk:
        trunk = next(t for t in (await lk.sip.list_outbound_trunk(api.ListSIPOutboundTrunkRequest())).items
                     if t.name.startswith("lab outbound"))
        t0 = time.monotonic()
        try:
            p = await lk.sip.create_sip_participant(api.CreateSIPParticipantRequest(
                sip_trunk_id=trunk.sip_trunk_id, sip_call_to="+15550002222", room_name="outbound-test",
                participant_identity="callee", wait_until_answered=True, ringing_timeout=Duration(seconds=8)))
            print("answered:", p.participant_identity)
        except api.TwirpError as e:
            print(f"after {time.monotonic() - t0:.1f}s: TwirpError {e.code}: {e.message}")
            print("  sip status:", e.metadata.get("sip_status_code"), e.metadata.get("sip_status"))


asyncio.run(main())
