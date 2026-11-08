"""Receive and verify LiveKit webhooks with nothing but the standard library HTTP server.

Run:  source lab.env && python webhook_receiver.py
      (then, in another terminal:  python two_participants.py)

lab/livekit.yaml sends webhooks to http://127.0.0.1:8099/webhook. Each POST carries
a JWT in the Authorization header, signed with your API secret, holding a sha256
of the body. WebhookReceiver checks both, so a forged or edited body is rejected.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer

from livekit import api

receiver = api.WebhookReceiver(api.TokenVerifier())   # reads LIVEKIT_API_KEY / _SECRET
seen = set()                                           # shortcut: real code keeps this in a database


class Hook(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"])).decode()
        try:
            ev = receiver.receive(body, self.headers.get("Authorization", ""))
        except Exception as e:
            print(f"REJECTED  {type(e).__name__}: {e}")
            self.send_response(401)
            self.end_headers()
            return
        dup = " (duplicate, skipped)" if ev.id in seen else ""
        seen.add(ev.id)
        who = ev.participant.identity or ev.egress_info.egress_id or ev.ingress_info.ingress_id
        track = f" track={ev.track.name}" if ev.track.sid else ""
        print(f"{ev.event:24} room={ev.room.name:14} {who}{track}{dup}")
        self.send_response(200)          # answer fast; do slow work after, from a queue
        self.end_headers()

    def log_message(self, *args):        # silence the default access log
        pass


if __name__ == "__main__":
    print("listening on :8099 ...")
    HTTPServer(("127.0.0.1", 8099), Hook).serve_forever()
