---
title: Webhooks and events
summary: How your backend finds out that a room started, a caller joined or a recording finished. The webhook config, the signed request, every event, delivery and retries, the SDK events on the client side, and when to poll instead. With real output from a small receiver.
time: 20 min
---

A call ends. Your backend has to mark the call row finished, bill the minutes and fetch the recording. How does it know? You could poll the server API every few seconds, but on our lab `ListRooms` reported `num_participants=0` while two participants were ACTIVE ([the server API](lesson:livekit/the-server-api)). Polled counts lag. You could ask the agent to tell you, but the agent may have crashed, and that is exactly when you need to know. LiveKit's answer is the **webhook**: an HTTP POST the server sends to your backend when something happens in a room ([LiveKit: webhooks & events](https://docs.livekit.io/intro/basics/rooms-participants-tracks/webhooks-events)).

The lab runs livekit-server v1.13.11 and the Python `livekit-api` 1.2.2.

## Turning webhooks on

On a self-hosted server you add a `webhook:` block to `livekit.yaml`. The lab's (`code/livekit/lab/livekit.yaml`):

```yaml
keys:
  lab-key: lab-secret-change-me-it-must-be-at-least-32-chars   # API key: API secret
webhook:
  api_key: lab-key         # must be one of the keys above; LiveKit signs each webhook with its secret
  urls:
    - http://127.0.0.1:8099/webhook
```

`api_key` must match one of the keys the server is configured with ([LiveKit: webhooks & events](https://docs.livekit.io/intro/basics/rooms-participants-tracks/webhooks-events#self-hosted-deployments)). Its secret signs every request. `urls` is a list, so you can send events to more than one service.

:::note Self-hosted vs Cloud
On Cloud you create webhooks in the dashboard and can send a test event from there. Self-hosted has no test button and no dashboard: the `webhook:` block is the whole setup. Leave it out and you get no error, just no events. A production voice platform lost every call row that way ([how the platform rides LiveKit](lesson:voice-prod/how-the-platform-rides-livekit)).
:::

## What arrives at your URL

Each webhook is an HTTP POST. The body is a `WebhookEvent` encoded as JSON, and the `Content-Type` is `application/webhook+json`, so some frameworks won't parse it unless you tell them to. The `Authorization` header holds a JWT signed with your API secret, and the JWT carries a sha256 hash of the body ([LiveKit: receiving webhooks](https://docs.livekit.io/intro/basics/rooms-participants-tracks/webhooks-events#receiving-webhooks)). So a valid header proves two things: LiveKit sent it, and nobody changed the body on the way. To check the hash, your code needs the raw body string, not a parsed object.

Every event carries `id` (a UUID for this event), `createdAt` (UNIX seconds) and `event` (its name). The rest depends on the event ([LiveKit: webhook events](https://docs.livekit.io/intro/basics/rooms-participants-tracks/webhooks-events#webhook-events)):

| Event | Fires when | Payload |
|---|---|---|
| `room_started` | The first participant joins an empty room | room |
| `room_finished` | The room closes: deleted, or empty after its timeout | room |
| `participant_joined` | A participant's media connection is up (state `active`) | room, participant |
| `participant_left` | A participant left and cleanup is complete | room, participant |
| `participant_connection_aborted` | Signaling connected, but the media connection failed | room, participant |
| `track_published` | A participant publishes a track | room, participant (SID, name, identity only), track |
| `track_unpublished` | A participant unpublishes a track | same as above |
| `egress_started` / `egress_updated` / `egress_ended` | A recording or stream starts, changes (for example, file size), ends | egressInfo |
| `ingress_started` / `ingress_ended` | An external stream starts or ends | ingressInfo |

That's twelve events. For a voice backend the usual set is `room_started` and `room_finished` for the call row, `participant_joined` and `participant_left` for who was on it, and `egress_ended` for the recording.

## Delivery: retried, sequenced, not guaranteed

Webhooks are pushed, so "there are no guarantees around delivery". LiveKit retries a failed request several times before giving up. When several events are queued, it sends newer ones only after older ones are delivered or abandoned ([LiveKit: delivery and retries](https://docs.livekit.io/intro/basics/rooms-participants-tracks/webhooks-events#delivery-and-retries)).

Two rules follow:

1. **Make handlers idempotent.** **Idempotent** means running it twice has the same effect as running it once. A retry after a timeout can deliver an event you already handled. Keep the `id` of each event you've handled, and skip repeats.
2. **Answer fast.** If your handler fetches a recording before it replies, the request can time out, and the retry arrives while the first attempt is still working. Verify, record the id, answer 200, then do the slow work from a queue.

<figure>
<svg viewBox="0 0 860 300" role="img" aria-labelledby="wh-t1 wh-d1">
  <title id="wh-t1">How a webhook should be handled</title>
  <desc id="wh-d1">The LiveKit server sends a signed POST to your receiver. The receiver first verifies the JWT and body hash and answers 401 if they fail. It then checks whether it has seen the event id before; if it has, it answers 200 and skips. Otherwise it answers 200 at once and puts the slow work on a queue. If the server gets no answer, it retries later.</desc>
  <defs><marker id="wh-ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <path class="arrow" stroke-dasharray="6 5" d="M262 30 H846 V288 H262 Z"/>
  <text x="554" y="54" font-size="14" font-weight="700" text-anchor="middle">Your receiver</text>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="16" y="106" width="150" height="64" rx="10"/><text x="91" y="134">LiveKit server</text><text x="91" y="154" font-size="12" class="small">webhook: urls</text>
    <rect class="box" x="280" y="106" width="150" height="64" rx="10"/><text x="355" y="134">1. Verify</text><text x="355" y="154" font-size="12" class="small">JWT + body hash</text>
    <rect class="box" x="470" y="106" width="150" height="64" rx="10"/><text x="545" y="134">2. Dedupe</text><text x="545" y="154" font-size="12" class="small">seen this event.id?</text>
    <rect class="box hot" x="660" y="106" width="170" height="64" rx="10"/><text x="745" y="134">3. Answer 200</text><text x="745" y="154" font-size="12" class="small">before any slow work</text>
    <rect class="box" x="280" y="218" width="150" height="50" rx="10"/><text x="355" y="248">401, drop it</text>
    <rect class="box" x="470" y="218" width="150" height="50" rx="10"/><text x="545" y="248">200, skip</text>
    <rect class="box" x="660" y="218" width="170" height="50" rx="10"/><text x="745" y="248">4. Queue the work</text>
  </g>
  <g font-size="12" class="small" text-anchor="middle">
    <path class="arrow" d="M166 126 H276" marker-end="url(#wh-ah)"/><text x="216" y="118">signed POST</text>
    <path class="arrow" stroke-dasharray="5 5" d="M276 154 H170" marker-end="url(#wh-ah)"/><text x="216" y="174">no reply:</text><text x="216" y="190">retry later</text>
    <path class="arrow" d="M430 138 H466" marker-end="url(#wh-ah)"/>
    <path class="arrow" d="M620 138 H656" marker-end="url(#wh-ah)"/>
    <path class="arrow" d="M355 170 V214" marker-end="url(#wh-ah)"/><text x="362" y="198" text-anchor="start">bad</text>
    <path class="arrow" d="M545 170 V214" marker-end="url(#wh-ah)"/><text x="552" y="198" text-anchor="start">seen</text>
    <path class="arrow" d="M745 170 V214" marker-end="url(#wh-ah)"/><text x="752" y="198" text-anchor="start">then</text>
  </g>
</svg>
<figcaption>Verify first, dedupe by event id, answer before doing anything slow. A retry of an event you already handled then costs nothing.</figcaption>
</figure>

## A receiver in 30 lines

`code/livekit/webhook_receiver.py` uses only the standard library HTTP server and the `livekit-api` package. `WebhookReceiver` checks the JWT signature and the body hash, then decodes the event:

```python
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
        ...
        self.send_response(200)          # answer fast; do slow work after, from a queue
```

Real output, after starting the receiver and then running the participant scripts, with one forged POST at the end:

```text
listening on :8099 ...
track_published          room=lesson-rpt     alice track=mic
room_finished            room=lesson-rpt     
room_started             room=lesson-rpt     
participant_joined       room=lesson-rpt     alice
track_published          room=lesson-rpt     alice track=mic
participant_joined       room=lesson-admin   alice
participant_joined       room=lesson-admin   bob
participant_left         room=lesson-admin   bob
participant_left         room=lesson-admin   alice
room_finished            room=lesson-admin   
participant_joined       room=lesson-rpt     bob
...
participant_left         room=lesson-rpt     bob
room_finished            room=lesson-rpt     
REJECTED  DecodeError: Not enough segments
```

In the first two lines, a `room_finished` arrives before the `room_started` for the same room, which can't be the live run. Earlier runs of `two_participants.py` and `room_admin.py` happened while nothing listened on port 8099. The server kept those events and retried them. When the receiver came up, the retries landed in the middle of the live run's events. The `lesson-admin` block is most likely the same thing, left over from `room_admin.py`. Each queue stays in order, but your receiver sees several of them draining at once. So don't treat arrival order as a timeline. Use `createdAt` and your own state.

No line says `(duplicate, skipped)`, so nothing arrived twice this time. The dedupe is there for the run where it does.

The last line is a POST we sent by hand with an `Authorization` value that isn't a JWT. "Not enough segments" comes from the JWT decoder: a JWT has three parts separated by dots, and this one didn't. The request was refused before any body hash was compared. The code then sends a 401.

:::warn Late events from rooms that are long gone
Retries mean a `room_finished` can reach you after your app has moved on, and after a restart you can get a burst of events from rooms that ended minutes ago. A handler that assumes "this event is about a live call" will reopen closed rows or start duplicate jobs. Dedupe by `event.id`, and check state before acting: if the call row is already finished, a second `room_finished` does nothing.
:::

## Per-egress webhooks

An egress request can carry its own `webhooks` list of `WebhookConfig` entries, each a `url` and a `signing_key`. LiveKit calls them for that egress's lifecycle events, in addition to the project webhooks. The signing key must be one the server knows ([LiveKit: egress API, WebhookConfig](https://docs.livekit.io/reference/other/egress/api#webhookconfig)). Use this when a recording service should hear about its own recordings without seeing every room event.

## SDK events: the client side

Webhooks go to your backend. **SDK events** are the other half: callbacks inside each participant's SDK, such as `room.on("track_subscribed", ...)` in Python. They fire on the `Room` and on each `Participant` ([LiveKit: SDK events](https://docs.livekit.io/intro/basics/rooms-participants-tracks/webhooks-events#sdk-events)). The common set across SDKs:

- **Participants:** `ParticipantConnected`, `ParticipantActive` (JavaScript only), `ParticipantDisconnected`
- **Connection:** `Reconnecting`, `Reconnected`, `Disconnected`, `ConnectionQualityChanged`
- **Tracks:** `TrackPublished`, `TrackUnpublished`, `TrackSubscribed`, `TrackUnsubscribed`, `TrackMuted`, `TrackUnmuted`, `LocalTrackPublished`, `LocalTrackUnpublished`, `TrackStreamStateChanged`, `TrackSubscriptionPermissionChanged`
- **Speech:** `ActiveSpeakersChanged`, `IsSpeakingChanged`
- **State and data:** `ParticipantAttributesChanged`, `ParticipantMetadataChanged`, `ParticipantNameChanged`, `RoomMetadataChanged`, `DataReceived`, `ParticipantPermissionsChanged`

Names don't line up with webhooks one to one. `ParticipantConnected` fires when the signaling connection is up. The `participant_joined` webhook fires later, when media is up and the state is `active` ([LiveKit: connection events](https://docs.livekit.io/intro/basics/rooms-participants-tracks/webhooks-events#connection-events)). Our lab saw the same: a participant is announced to others only once it is ACTIVE.

## Which one to use

| You need | Use | Why |
|---|---|---|
| Durable records: call rows, billing, recordings | Webhooks | Your backend hears about it even if every client crashed |
| UI and agent reactions: show a speaker, start listening | SDK events | They fire inside the process that has to react, with no extra hop |
| The current state right now, for a dashboard or a check | Server API (`ListParticipants`) | Ask when you need it. Prefer `ListParticipants` to the room counts, which update lazily |
| Catching up after your receiver was down | Server API, then webhooks | Retries are not guaranteed, so reconcile against the API |

:::tip CLI
There is no `lk` command for webhooks. They are server config. To make events happen while you watch a receiver:

- `lk room create --empty-timeout 120 --departure-timeout 10 demo`
- `lk room join --identity bot_user --publish-demo test_room`
- `lk room participants list demo`
- `lk room delete demo`
:::

:::try
Stop `webhook_receiver.py`. Run `python two_participants.py` with `lab.env` sourced. Wait a few seconds, then start the receiver again. Do the events show up, and in what order? Then make the receiver call `time.sleep(15)` before `send_response(200)` and run the script once more. Do you get any `(duplicate, skipped)` lines?
:::

:::note What we did not test
We didn't measure how many times LiveKit retries, how long it waits between tries, or what timeout it uses, and the docs don't say. We didn't check whether a 401 or a 500 is retried. We didn't run per-egress webhooks or see `participant_connection_aborted` fire. The forged request tested a malformed header, not a validly formed JWT signed with the wrong secret.
:::

:::say
Webhooks are signed, retried and not guaranteed, so verify each one, dedupe by `event.id`, answer 200 fast, and reconcile against the server API.
:::

:::check Your receiver got a `room_finished` for a room whose `room_started` it hasn't seen yet. What happened, and what should the handler do?
Most likely an older event that was retried after your receiver was down, arriving among newer events from other queues. The handler should dedupe by `event.id` and act on stored state: if the room has no open call row, create or close it in a way that is safe to repeat, and don't assume arrival order is time order.
:::

:::check Why use the `participant_joined` webhook, not the client's `ParticipantConnected` event, to start billing a call?
`ParticipantConnected` fires inside a client when signaling is up, before media works, and only if that client is running. `participant_joined` is sent to your backend when the participant is `active`, meaning media is flowing.
:::
