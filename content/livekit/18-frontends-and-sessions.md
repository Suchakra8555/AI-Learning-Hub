---
title: Frontends and sessions
summary: How a browser, phone app or small device reaches your agent on a self-hosted server. Token sources, the standard token endpoint, Session and agent states, the text topics, RPC to the UI, the starter apps and hardware, with a token endpoint that dispatched the lab's echo agent.
time: 25 min
---

Your agent answers in the terminal. Now a web page has to talk to it. The page needs a token, and a token needs your API secret, which must never reach the browser. The page also has to make the agent join, show whether the agent is listening or thinking, and print what was said. This lesson covers each of those pieces on a self-hosted server.

## Where the token comes from

A frontend connects with a JWT **access token** that names the room, the identity, the grants and, for agents, which agent to dispatch ([Tokens and grants](lesson:livekit/tokens-and-grants) covers the claims). Only a backend that holds the API secret can sign one ([Authentication](https://docs.livekit.io/frontends/build/authentication)).

The client SDKs wrap this in a **TokenSource**: an object that fetches a token, caches it and refetches it when it expires. There are four kinds ([Authentication](https://docs.livekit.io/frontends/build/authentication)):

| TokenSource | What it does | Self-hosted? |
|---|---|---|
| Token server (`TokenSource.sandboxTokenServer(...)`) | LiveKit Cloud signs tokens for you. Development only. | No |
| Endpoint (`TokenSource.endpoint(url, init)`) | POSTs to your backend in a standard format | Yes |
| Custom (`TokenSource.custom(async (options) => ...)`) | Calls your own async function, with caching and refresh | Yes |
| Literal (`TokenSource.literal({ serverUrl, participantToken })`) | You already have a token. No caching. | Yes |

The docs now call the Cloud option the "development token server". LiveKit Sandbox is gone, but some SDK names still say `Sandbox` ([Development token server](https://docs.livekit.io/frontends/build/authentication/development-token-server)).

## The standard token endpoint

The endpoint format is the same for every client SDK ([Token endpoints](https://docs.livekit.io/frontends/build/authentication/endpoint)). The client sends a `POST` with a JSON body. Every field is optional:

- `room_name`, `participant_identity`, `participant_name`
- `participant_metadata`, `participant_attributes`
- `room_config`, a **RoomConfiguration** that holds the agent dispatch. The client SDK fills it from the `agentName` you give the session.

The endpoint answers `201 Created` with `{"server_url": ..., "participant_token": ...}`. If a client sends a field it may not set, the docs say to return a 4xx. You add the auth: `TokenSource.endpoint` takes a second `RequestInit` argument for an `Authorization` header.

The lab version is `code/livekit/token_endpoint.py`, about 40 lines with only the standard library and `livekit-api`:

```python
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
```

We POSTed `{"room_name":"web-1","participant_identity":"u1"}`, decoded the token, and joined with it while the echo agent's server was running. Real output (`out/token_endpoint.txt`):

```text
server_url: ws://127.0.0.1:7880
claims: {
 "name": "u1",
 "video": {
  "roomJoin": true,
  "room": "web-1",
  "canPublish": true,
  "canSubscribe": true,
  "canPublishData": true
 },
 "roomConfig": {
  "agents": [
   {
    "agentName": "echo"
   }
  ]
 },
 "sub": "u1",
 "iss": "lab-key",
 "nbf": 1794130575,
 "exp": 1794131475
}
joined web-1 as u1 | others: [('agent-AJ_ymXHYAYbbQDP', 'PARTICIPANT_KIND_AGENT')]
```

`exp − nbf` is 900 seconds, the 15-minute TTL. `canPublishData` is there even though the code never set it, so the Python `VideoGrants` must turn it on by default. The last line shows the dispatch worked. No `lk dispatch create` was run, yet the room already held an agent when `u1` arrived. The `roomConfig` claim told the server to dispatch `echo` when it created `web-1` ([Agent dispatch](https://docs.livekit.io/agents/server/agent-dispatch)).

<figure>
<svg viewBox="0 0 800 340" role="img" aria-labelledby="t-fe-flow d-fe-flow">
  <title id="t-fe-flow">From a browser to a dispatched agent</title>
  <desc id="d-fe-flow">The browser POSTs a room name and identity to your token endpoint, which holds the API secret and replies 201 with a server URL and a participant token. The browser connects to the LiveKit server with that token. The server reads the room configuration in the token and dispatches a job to the agent server registered as echo. The agent joins the room, and audio, transcriptions and RPC then flow between browser and agent through the server.</desc>
  <defs><marker id="ah-fe" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="20" y="12" width="160" height="56" rx="10"/><text x="100" y="36">Browser</text><text x="100" y="56" font-size="12" class="small">TokenSource.endpoint</text>
    <rect class="box hot" x="220" y="12" width="160" height="56" rx="10"/><text x="300" y="36">Your token endpoint</text><text x="300" y="56" font-size="12" class="small">holds the API secret</text>
    <rect class="box" x="420" y="12" width="160" height="56" rx="10"/><text x="500" y="36">LiveKit server</text><text x="500" y="56" font-size="12" class="small">ws://127.0.0.1:7880</text>
    <rect class="box" x="620" y="12" width="160" height="56" rx="10"/><text x="700" y="36">Agent server</text><text x="700" y="56" font-size="12" class="small">agent_name="echo"</text>
  </g>
  <path class="arrow" stroke-dasharray="3 5" d="M100 68 V328"/>
  <path class="arrow" stroke-dasharray="3 5" d="M300 68 V328"/>
  <path class="arrow" stroke-dasharray="3 5" d="M500 68 V328"/>
  <path class="arrow" stroke-dasharray="3 5" d="M700 68 V328"/>
  <g font-size="12" class="small" text-anchor="middle">
    <path class="arrow" d="M100 100 H296" marker-end="url(#ah-fe)"/><text x="200" y="94">1. POST room_name, identity</text>
    <path class="arrow" d="M300 140 H104" marker-end="url(#ah-fe)"/><text x="200" y="134">2. 201 server_url, token</text>
    <path class="arrow" d="M100 180 H496" marker-end="url(#ah-fe)"/><text x="300" y="174">3. connect with participant_token</text>
    <path class="arrow" d="M500 220 H696" marker-end="url(#ah-fe)"/><text x="600" y="214">4. dispatch job: echo</text>
    <path class="arrow" d="M700 260 H504" marker-end="url(#ah-fe)"/><text x="600" y="254">5. agent joins the room</text>
    <path class="arrow" stroke-dasharray="5 5" d="M104 305 H696" marker-start="url(#ah-fe)" marker-end="url(#ah-fe)"/><text x="400" y="299">6. audio, lk.transcription, lk.chat, RPC over WebRTC</text>
  </g>
</svg>
<figcaption>The secret never leaves your endpoint. The token carries the dispatch, so the agent is already joining by the time the browser has connected.</figcaption>
</figure>

Two shortcuts in the lab script are worth fixing in a real endpoint. It has no auth at all, so anyone who can reach it gets a token. And it hard-codes the agent and ignores the `room_config` that the client sends. The docs' examples pass `room_config` straight to the token builder. Hard-coding is safer if you don't want callers to pick any agent by name. Pass-through is easier if one frontend talks to several agents. The docs use `/getToken`. The path is up to you.

On a self-hosted server, `server_url` is your own address. The lab returns `ws://127.0.0.1:7880`. In production it must be `wss://` on a domain with a certificate from a trusted CA, since self-signed certificates don't work ([Deployment](https://docs.livekit.io/transport/self-hosting/deployment)).

## Session and agent state

**Session** wraps token fetching, `Room.connect`, agent dispatch and cleanup into `start()` and `end()`. It exists on Web, Swift, Kotlin, Flutter and React Native ([Session management](https://docs.livekit.io/frontends/build/sessions)). In React:

```tsx
const tokenSource = TokenSource.endpoint("https://api.example.com/token", {
  headers: { Authorization: `Bearer ${userJwt}` },
});
const session = useSession(tokenSource, { agentName: "echo" });
useEffect(() => { session.start(); return () => { session.end(); }; }, []);
```

The agent publishes its state as the participant attribute `lk.agent.state` ([Agent state](https://docs.livekit.io/frontends/build/agent-state)). The states are `connecting`, `pre-connect-buffering`, `initializing`, `idle`, `listening`, `thinking`, `speaking`, `disconnected` and `failed`. `disconnected` is a clean end. `failed` is an error, and the reasons are in `failureReasons`. The docs ask you to drive the UI from **state getters**, booleans that stay correct when new states are added:

- `canListen`: the user can talk (pre-connect-buffering, listening, thinking, speaking)
- `isConnected`: listening, thinking or speaking
- `isPending`: connecting, initializing or idle
- `isFinished`: disconnected or failed

## Text, transcripts and RPC to the UI

Text rides on text streams, the same mechanism tested in [Data and state](lesson:livekit/data-and-state) ([Text and transcriptions](https://docs.livekit.io/agents/multimodality/text)):

- **`lk.transcription`**: the agent publishes transcripts of both sides here. Interim and final chunks share a `segment_id`. Use the `lk.transcription_final` attribute to replace interim text with the final version.
- **`lk.chat`**: the agent listens for typed user messages here. A message interrupts the agent's speech. Send with `room.localParticipant.sendText(text, { topic: 'lk.chat' })`, or turn it off with `text_input=False` in `RoomOptions`.

Session's messages API merges both into one list you can render ([Session management](https://docs.livekit.io/frontends/build/sessions)).

The agent can also call the frontend. A tool calls `room.local_participant.perform_rpc(destination_identity=..., method="getUserLocation", payload=..., response_timeout=5.0)` and returns what the browser answers ([Forwarding to the frontend](https://docs.livekit.io/agents/logic/tools/forwarding)). The frontend registers that method name. If it doesn't, the call fails with `RpcError 1400: Method not supported at destination`, as the lab showed in [Data and state](lesson:livekit/data-and-state).

## Starter apps, Agents UI and hardware

- **Starter apps**, MIT-licensed: Next.js, SwiftUI, Android, Flutter, React Native, a web embed and Unity ([Starter apps](https://docs.livekit.io/frontends/start/starter-apps)). The docs say the mobile apps need a hosted token server. Self-hosted, point them at your endpoint.
- **Agents UI**: shadcn components (control bar, chat transcript, audio visualizers). Install them with `npx shadcn@latest registry add @agents-ui` and they land as source in `components/agents-ui` ([Agents UI](https://docs.livekit.io/frontends/agents-ui)). They need `AgentSessionProvider` as an ancestor.
- **Hardware**: on embedded Linux, use the Python or Rust SDK. Both support echo cancellation ([Hardware](https://docs.livekit.io/frontends/build/hardware)). The ESP32 SDK supports only ESP32-S3 and ESP32-P4. It publishes one audio and one video track (Opus, H.264), subscribes to one audio track and no video, and supports RPC ([ESP32](https://docs.livekit.io/frontends/build/hardware/esp32)).

:::note Self-hosted vs Cloud
The development token server is Cloud-only. Self-hosted, write an endpoint like the one above. Token revocation is also Cloud-only ([Tokens and grants](https://docs.livekit.io/frontends/reference/tokens-grants)). On your own server, removing a participant doesn't invalidate their token, so keep TTLs short (the lab uses 15 minutes). The session's `deployment` option targets LiveKit Cloud agent deployments. Leave it empty when you run your own agent servers.
:::

:::tip CLI
Make a token that dispatches an agent, without writing an endpoint (`--agent` needs `--join`; [CLI rooms reference](https://docs.livekit.io/reference/developer-tools/livekit-cli/rooms)):

```bash
lk token create --join --room web-2 --identity u2 --agent echo --valid-for 15m
lk room participants list web-2
lk dispatch list web-2
```
:::

:::try
With the lab up and `echo_agent.py start` running, start `python code/livekit/token_endpoint.py` and run the `curl` from its docstring with a new room name. Join with the token, then run `lk dispatch list` for that room. Change `agent_name` to `"nobody"` and do it again. What does the room hold now, and what does the list show?
:::

:::warn An open token endpoint is an open door
Anyone who can POST to `token_endpoint.py` gets a token that can join any room it names and start an agent, which spends your LLM and TTS budget. Check the user's own session before you sign anything. Choose the room and identity on the server, and return 4xx for fields the client may not set.
:::

:::note What we did not test
We tested the endpoint from Python, not from a browser with `TokenSource.endpoint`. We didn't run any starter app, Agents UI, the Session API, agent state getters, the ESP32 SDK or the `lk token create --agent` command above. Those come from the docs pages linked here. Versions: livekit-server v1.13.11, `livekit-api` 1.2.2, `livekit-agents` 1.8.11.
:::

:::say
The browser gets a short-lived token from your endpoint, the token's room config brings the agent in, and the UI follows `lk.agent.state` and the `lk.transcription` and `lk.chat` topics.
:::

:::check Why does the browser call your endpoint instead of signing the token itself?
Signing needs the API secret. Any code in the browser can be read, so the secret would leak, and anyone could mint tokens for any room with any grants. The endpoint keeps the secret and decides who gets which room.
:::

:::check The token from your endpoint has no roomConfig, and the agent never joins. What else could bring it in?
An explicit dispatch through the API (`lk dispatch create --room ... --agent-name ...`). Or an agent server registered with no `agent_name`, which is sent to every new room. The docs advise against that for most apps ([Agent dispatch](https://docs.livekit.io/agents/server/agent-dispatch)).
:::

Next: [Testing and observability](lesson:livekit/testing-and-observability)
