---
title: Tokens and grants
summary: How LiveKit decides who may join which room and do what. The JWT claims, every video grant, the SIP grant, room configuration in a token, and how refresh and revocation work on a self-hosted server. With real rejections from the lab.
time: 22 min
---

Your frontend needs to join a room. It can't hold your API secret, because anything shipped to a browser or phone is public. Your agent workers and your backend also call LiveKit, with far more power than a caller should have. All of that hangs on one small string. An **access token** says who you are, which room you may enter, and what you may do there. The server has no other way to know who a participant is.

The lab runs livekit-server v1.13.11, `lk` v2.19.3, and the Python packages `livekit` 1.2.0 and `livekit-api` 1.2.2.

## What a token is

A LiveKit access token is a **JWT** (JSON Web Token): a base64 JSON header, a base64 JSON payload, and a signature. Your backend signs it with the **API secret**, and the server checks the signature with the same secret ([tokens & grants](https://docs.livekit.io/frontends/reference/tokens-grants)). Anyone can read the payload, but nobody without the secret can change it.

<figure>
<svg viewBox="0 0 820 300" role="img" aria-labelledby="t-tok-flow d-tok-flow">
  <title id="t-tok-flow">Who signs a token and who checks it</title>
  <desc id="d-tok-flow">The client asks your backend for a token. Your backend, which holds the API secret, signs a JWT and returns it. The client connects to the LiveKit server with the token. The server checks the signature, the time window and the grants, then puts the client in the room the token names. While connected, the server pushes refreshed tokens to the client.</desc>
  <defs><marker id="ah-tok-flow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g text-anchor="middle">
    <rect class="box hot" x="20" y="70" width="180" height="110" rx="10"/>
    <text x="110" y="100" font-size="15">Your backend</text>
    <text x="110" y="124" font-size="12" class="small">holds API key + secret</text>
    <text x="110" y="142" font-size="12" class="small">checks your own login</text>
    <text x="110" y="160" font-size="12" class="small">signs the JWT (HS256)</text>
    <rect class="box" x="320" y="70" width="180" height="110" rx="10"/>
    <text x="410" y="100" font-size="15">Client</text>
    <text x="410" y="124" font-size="12" class="small">browser, app, agent</text>
    <text x="410" y="142" font-size="12" class="small">never sees the secret</text>
    <rect class="box" x="620" y="70" width="180" height="110" rx="10"/>
    <text x="710" y="100" font-size="15">LiveKit server</text>
    <text x="710" y="124" font-size="12" class="small">1. signature valid?</text>
    <text x="710" y="142" font-size="12" class="small">2. now within nbf..exp?</text>
    <text x="710" y="160" font-size="12" class="small">3. grants allow it?</text>
  </g>
  <path class="arrow" d="M320 95 H204" marker-end="url(#ah-tok-flow)"/>
  <path class="arrow" d="M200 150 H316" marker-end="url(#ah-tok-flow)"/>
  <path class="arrow" d="M500 125 H616" marker-end="url(#ah-tok-flow)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M710 180 V230 H410 V184" marker-end="url(#ah-tok-flow)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="260" y="88">ask for a token</text>
    <text x="260" y="168">signed JWT</text>
    <text x="560" y="118">connect + JWT</text>
    <text x="560" y="250">while connected: refreshed tokens pushed down</text>
    <text x="410" y="285">Fail any check: 401, "token signature is invalid" or "token is expired".</text>
  </g>
</svg>
<figcaption>The secret stays on your backend. The client carries a token it can read but can't change, and the server checks it on connect.</figcaption>
</figure>

## The claims

| Claim | Meaning |
|---|---|
| `exp` | When the token expires |
| `iss` | The API key that issued it |
| `sub` | The participant's identity |
| `nbf` | When it becomes valid ("not before") |
| `video` | The video grant: the room and the permissions |
| `metadata` | Participant metadata |
| `attributes` | Participant attributes, a map of string to string |
| `sip` | The SIP grant |
| `roomConfig` | Room settings to apply if this join creates the room |

`lk token create --join --room demo --identity alice --valid-for 1h` signs locally and prints the grants. Real output (token trimmed):

```text
Using url, api-key, api-secret from environment
valid for (mins): 60
Token grants:
{
  "identity": "alice",
  "name": "alice",
  "video": {
    "roomJoin": true,
    "room": "demo"
  }
}

Project URL: ws://127.0.0.1:7880
Access token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJsYWIta2V5Iiwic3ViIjoiYWxpY2Ui...
```

We base64-decoded the payload of that token. It reads `{"iss":"lab-key","sub":"alice","exp":1794133650,"nbf":1794130050,"iat":1794130050,"identity":"alice","name":"alice","video":{"roomJoin":true,"room":"demo"}}`. `exp` minus `nbf` is 3600 seconds, the hour we asked for. The CLI also writes `iat`, `identity` and `name`, which the docs' claim table leaves out.

## Every video grant

From the docs' video grant table ([video grant](https://docs.livekit.io/frontends/reference/tokens-grants#video-grant)):

| Field | Type | What it allows |
|---|---|---|
| `roomCreate` | boolean | Create or delete rooms |
| `roomList` | boolean | List rooms |
| `roomJoin` | boolean | Join a room |
| `roomAdmin` | boolean | Moderate a room |
| `roomRecord` | boolean | Use the Egress service |
| `ingressAdmin` | boolean | Use the Ingress service |
| `room` | string | The room name; required if join or admin is set |
| `canPublish` | boolean | Publish tracks |
| `canPublishData` | boolean | Publish data to the room |
| `canPublishSources` | string | Only these sources may be published (camera, microphone, screen_share, screen_share_audio); needs `canPublish` |
| `canSubscribe` | boolean | Subscribe to tracks |
| `canUpdateOwnMetadata` | boolean | Update its own metadata |
| `hidden` | boolean | Hidden from others in the room |
| `kind` | string | Participant kind (standard, ingress, egress, sip, agent, connector); usually set by LiveKit itself |
| `destinationRoom` | string | A room this participant may be forwarded to |

The Python `VideoGrants` class in `livekit-api` 1.2.2 has a few more fields the table doesn't list: `agent`, `can_manage_agent_session`, `can_subscribe_metrics` and a deprecated `recorder`. It also defaults `can_publish`, `can_subscribe` and `can_publish_data` to `True`. That's why the tokens below carry all three even though the script only set one.

The **SIP grant** sits in the `sip` claim. It has two fields: `admin` to manage trunks and dispatch rules, and `call` to place calls with `CreateSIPParticipant`.

## Room configuration in a token

A token can carry a `RoomConfiguration`: timeouts, `max_participants`, auto-egress, and agents to dispatch. The docs say it is "applied only when the room is first created. If the room already exists, LiveKit ignores the configuration in the token" ([room configuration](https://docs.livekit.io/frontends/reference/tokens-grants#room-configuration)). On the lab, a token with `RoomConfiguration(agents=[RoomAgentDispatch(agent_name="echo")])` decoded to `"roomConfig": {"agents": [{"agentName": "echo"}]}` and brought the echo agent in when the room was created. That's covered in the agent lessons.

## On the lab

`code/livekit/tokens.py` mints tokens and tries to join with each one:

```python
def token(identity, room, ttl=timedelta(minutes=10), **grants):
    g = api.VideoGrants(room_join=True, room=room, **grants)
    return api.AccessToken().with_identity(identity).with_grants(g).with_ttl(ttl).to_jwt()
...
    jwt = token("alice", "lesson-tokens", can_publish=False)
    alice = await try_join("good token", jwt)
    other = await try_join("token naming another room", token("mallory", "other-room"))
    forged = jwt[:-4] + ("AAAA" if not jwt.endswith("AAAA") else "BBBB")
    await try_join("tampered signature", forged)
    await try_join("expired token", token("late", "lesson-tokens", ttl=timedelta(seconds=-60)))
    bad = api.AccessToken(os.environ["LIVEKIT_API_KEY"], "x" * 40).with_identity("eve") \
        .with_grants(api.VideoGrants(room_join=True, room="lesson-tokens")).to_jwt()
    await try_join("signed with the wrong secret", bad)
```

Real output:

```text
decoded claims: {"iss": "lab-key", "sub": "alice", "video": {"roomJoin": true, "room": "lesson-tokens", "canPublish": false, "canSubscribe": true, "canPublishData": true}}
valid for 600 s

good token                     -> joined room 'lesson-tokens' as alice
token naming another room      -> joined room 'other-room' as mallory
tampered signature             -> rejected (401): token signature is invalid: signature is invalid
expired token                  -> rejected (401): token has invalid claims: token is expired
signed with the wrong secret   -> rejected (401): token signature is invalid: signature is invalid
publish, can_publish=False     -> failed: engine: internal error: track publication timed out, no response received from the server
```

The second line matters most. Every join used the same server URL, and mallory landed in `other-room` because her token said so. The token picks the room, so your backend must decide the room before it signs. Tampering with the signature and signing with the wrong secret give the same 401.

## Refresh and expiry

Expiry only counts at the first connect. Reconnects don't check it. While a participant is connected, the server keeps pushing it refreshed tokens. Each one lasts 10 minutes or the remaining life of the original, whichever is longer. A change to the participant's name, permissions or metadata also triggers a refresh ([token refresh](https://docs.livekit.io/frontends/reference/tokens-grants#token-refresh)). So a short TTL doesn't cut off a call that is already running.

If you set no TTL, most server SDKs default to 6 hours (Ruby uses 10 minutes). `DEFAULT_TTL` in the Python package is `timedelta(hours=6)`. `lk token create` defaults to 5 minutes ([CLI reference](https://docs.livekit.io/reference/developer-tools/livekit-cli/rooms#create-a-token)).

:::note Self-hosted vs Cloud
**Token revocation** is Cloud-only. On LiveKit Cloud, `RemoveParticipant` or a permission change marks old tokens as rejected for 10 minutes. On a self-hosted server, removing a participant or changing their permissions "doesn't invalidate the participant's existing token". The docs' advice for self-hosted: issue tokens with a short TTL, and after you remove someone, don't mint them a new token ([token revocation](https://docs.livekit.io/frontends/reference/tokens-grants#token-revocation)). The Cloud development token server doesn't exist either. You write your own token endpoint.
:::

:::tip CLI
- `lk token create --join --room demo --identity alice --valid-for 1h`
- `lk token create --join --room my-room --identity viewer --grant '{"canPublish": false, "canPublishData": false}' --token-only`
- `lk token create --join --room support-%t --identity customer --agent my-agent`

Flags include `--admin`, `--create`, `--list`, `--egress`, `--ingress`, `--allow-update-metadata`, `--allow-source`, `--metadata`, `--attribute` and `--valid-for` ([CLI reference](https://docs.livekit.io/reference/developer-tools/livekit-cli/rooms#token-commands)). Tokens are signed locally, so no server is needed.
:::

:::try
Mint a token with `lk token create --join --room demo --identity alice --valid-for 2m --token-only`. Decode the middle part with `cut -d. -f2 | tr '_-' '/+' | base64 -d` (it may warn about missing `=` padding) and predict `exp - nbf` before you look. Then wait three minutes and connect with it. Which error do you expect, and would it still fail if the participant were already connected and only reconnecting?
:::

:::warn A missing grant looks like a timeout
With `can_publish=False`, `publish_track` didn't fail with "permission denied". It hung, then failed with "track publication timed out, no response received from the server". The whole script took 10.8 s to run. If publishing times out on a server that is otherwise healthy, decode the token and check `canPublish` and `canPublishSources` before you debug the network.
:::

:::note What we did not test
We didn't test the SIP grant, `roomRecord`, `ingressAdmin`, `hidden`, `canPublishSources`, a future `nbf`, or the server's token refresh. We didn't check how a self-hosted server handles a reconnect after `RemoveParticipant`. The refresh, revocation and TTL facts come from the docs and the package source.
:::

:::say
A token is a note signed by your backend that names one identity, one room and what it may do there, and the server takes the room from the token alone.
:::

:::check A client connects to `wss://lk.example.com` with a token whose `video.room` is `call-7`, but your frontend thinks it is joining `call-8`. Where does it end up?
In `call-7`. The server reads the room from the signed token, not from the URL or anything else the client says. On the lab, a token naming `other-room` joined `other-room`.
:::

:::check On self-hosted LiveKit you remove an abusive participant. What stops them coming back?
Nothing in the server revokes their token, since revocation is Cloud-only. Their old token works until it expires, so keep TTLs short, and make sure your backend won't mint them a new one.
:::

Next: [The server API](lesson:livekit/the-server-api)
