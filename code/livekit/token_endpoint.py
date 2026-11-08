"""A token endpoint for frontends, using LiveKit's standard request and response shape.

Run:  source lab.env && python token_endpoint.py
Try:  curl -s -X POST localhost:8098/token -d '{"room_name":"web-1","participant_identity":"u1"}'

A frontend's TokenSource.endpoint(url) POSTs here and gets back server_url and
participant_token. The token also asks LiveKit to dispatch the "echo" agent when
the room is first created. Your API secret never leaves the server.
"""
import json
import os
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

from livekit import api


class Token(BaseHTTPRequestHandler):
    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or "{}")
        # shortcut: no auth. A real endpoint checks the user's session before minting anything.
        room = req.get("room_name") or f"web-{uuid.uuid4().hex[:6]}"
        identity = req.get("participant_identity") or f"user-{uuid.uuid4().hex[:6]}"
        jwt = (api.AccessToken()
               .with_identity(identity)
               .with_name(req.get("participant_name", identity))
               .with_ttl(__import__("datetime").timedelta(minutes=15))   # short: self-hosted has no revocation
               .with_grants(api.VideoGrants(room_join=True, room=room, can_publish=True, can_subscribe=True))
               .with_room_config(api.RoomConfiguration(agents=[api.RoomAgentDispatch(agent_name="echo")]))
               .to_jwt())
        body = json.dumps({"server_url": os.environ["LIVEKIT_URL"], "participant_token": jwt}).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("token endpoint on :8098/token")
    HTTPServer(("127.0.0.1", 8098), Token).serve_forever()
