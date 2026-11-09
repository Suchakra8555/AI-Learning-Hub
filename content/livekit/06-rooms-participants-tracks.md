---
title: Rooms, participants and tracks
summary: The three nouns every LiveKit app is built from. When a room exists, who counts as a participant and in what state, the difference between a track and a track publication, and what the SDK tells you as each one changes. With real output from two participants on the lab.
time: 25 min
---

Your agent joins a room and waits for audio, and none comes. Or a test script reconnects with the same name as the agent, and the agent drops off the call with no error in its logs. Both come from the object model you skipped. LiveKit has three nouns: rooms, participants and tracks. Each one has rules about when it exists and what you get told about it ([overview](https://docs.livekit.io/intro/basics/rooms-participants-tracks)).

The lab runs livekit-server v1.13.11, `lk` v2.19.3, and the Python packages `livekit` 1.2.0 and `livekit-api` 1.2.2.

## Rooms

A **room** is the container for one session. Everyone in it gets told when anyone else joins, leaves, publishes or mutes. You can create a room with the server API, but you don't have to. A room is also created automatically when the first participant joins it ([room management](https://docs.livekit.io/intro/basics/rooms-participants-tracks/rooms)).

A room closes on its own, and two timers decide when ([RoomService API](https://docs.livekit.io/reference/other/roomservice-api)):

- **`empty_timeout`**: how long a room stays open if nobody joins. The default is 300 seconds.
- **`departure_timeout`**: how long it stays open after the last participant leaves. The default is 20 seconds.

`max_participants` caps the head count, and 0 means no limit. Room **metadata** is a free-form string, opaque to LiveKit. When you update it, every participant gets the change. `DeleteRoom` disconnects everyone at once.

## Participants

A **participant** is anything that joins a room: a browser, a phone caller, an agent, a recorder. Each one has an **identity** that you choose and a **sid** that the server generates. The identity is unique per room. If a second participant joins with the same identity, the server keeps the newest one and disconnects the others ([participant management](https://docs.livekit.io/intro/basics/rooms-participants-tracks/participants)).

In the SDK you are the **LocalParticipant**, and everyone else is a **RemoteParticipant**. The `kind` field says what sort of participant it is:

| Kind | What it is |
|---|---|
| `STANDARD` | A regular end user, such as a web or mobile client |
| `AGENT` | An agent started by the Agents framework |
| `SIP` | A phone caller who came in through SIP |
| `CONNECTOR` | A user who came in through a connector such as WhatsApp or Twilio |
| `EGRESS` | A server process recording the session |
| `INGRESS` | A server process bringing media into the session |

Besides `kind`, a participant carries a display `name`, a `metadata` string, `attributes` (a map of string to string), and a `permission` block. The permission fields are `can_subscribe`, `can_publish`, `can_publish_data`, `can_publish_sources`, `hidden`, `can_update_metadata` and `can_subscribe_metrics` ([ParticipantPermission](https://docs.livekit.io/reference/other/roomservice-api#participantpermission)). They start from the token's grants, and the server API can change them mid-call. A **hidden** participant is in the room, but the other participants can't see it. A recorder or a silent supervisor is a typical example.

### Participant states

Each participant moves through four states: `JOINING`, `JOINED`, `ACTIVE` and `DISCONNECTED`. The docs list the names but don't explain them. The comments in LiveKit's protocol file do ([livekit_models.proto](https://github.com/livekit/protocol/blob/main/protobufs/livekit_models.proto)): JOINING means the WebSocket is connected but no offer has been sent, JOINED means the server has the client's offer, ACTIVE means ICE connectivity is established, and DISCONNECTED means the WebSocket is gone.

<figure>
<svg viewBox="0 0 800 250" role="img" aria-labelledby="t-rpt-state d-rpt-state">
  <title id="t-rpt-state">The four participant states</title>
  <desc id="d-rpt-state">A participant goes from JOINING (WebSocket open, no offer yet) to JOINED (server has the SDP offer) to ACTIVE (ICE connected, other participants are told) to DISCONNECTED. Disconnect reasons include duplicate identity, participant removed, room deleted and room closed. An app killed without disconnecting disappears after about 15 seconds.</desc>
  <defs><marker id="ah-rpt-state" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g text-anchor="middle">
    <rect class="box" x="20" y="40" width="170" height="70" rx="10"/><text x="105" y="66" font-size="15">JOINING</text><text x="105" y="86" font-size="12" class="small">WebSocket open,</text><text x="105" y="101" font-size="12" class="small">no offer yet</text>
    <rect class="box" x="220" y="40" width="170" height="70" rx="10"/><text x="305" y="66" font-size="15">JOINED</text><text x="305" y="86" font-size="12" class="small">server has the</text><text x="305" y="101" font-size="12" class="small">client's SDP offer</text>
    <rect class="box hot" x="420" y="40" width="170" height="70" rx="10"/><text x="505" y="66" font-size="15">ACTIVE</text><text x="505" y="86" font-size="12" class="small">ICE connected;</text><text x="505" y="101" font-size="12" class="small">others are told now</text>
    <rect class="box" x="620" y="40" width="170" height="70" rx="10"/><text x="705" y="66" font-size="15">DISCONNECTED</text><text x="705" y="86" font-size="12" class="small">left, removed,</text><text x="705" y="101" font-size="12" class="small">replaced or timed out</text>
  </g>
  <path class="arrow" d="M190 75 H216" marker-end="url(#ah-rpt-state)"/>
  <path class="arrow" d="M390 75 H416" marker-end="url(#ah-rpt-state)"/>
  <path class="arrow" d="M590 75 H616" marker-end="url(#ah-rpt-state)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M305 110 V140 H705 V114" marker-end="url(#ah-rpt-state)"/>
  <text x="505" y="158" font-size="12" class="small" text-anchor="middle">JOIN_FAILURE: a join can fail before ACTIVE</text>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="400" y="200">Other reasons: DUPLICATE_IDENTITY, PARTICIPANT_REMOVED, ROOM_DELETED, ROOM_CLOSED</text>
    <text x="400" y="222">An app killed without calling disconnect() is dropped after about 15 s.</text>
  </g>
</svg>
<figcaption>Other participants only hear about you once you reach ACTIVE. The disconnect reason tells you why you left.</figcaption>
</figure>

A clean exit calls `Room.disconnect()`. If the app dies without calling it, the participant stays in the room for about 15 seconds before the server drops it. When the server ends a session, the `disconnected` event carries a reason such as `DUPLICATE_IDENTITY` or `ROOM_DELETED` ([connecting](https://docs.livekit.io/intro/basics/connect)).

## Tracks and track publications

A **track** is one media stream: a microphone, a camera, a screen share. LiveKit models it with two objects ([track management](https://docs.livekit.io/intro/basics/rooms-participants-tracks/tracks)):

- A **TrackPublication** is the server's record that the track exists. It holds the sid, kind, **source** (camera, microphone, screen share or screen share audio), name, `muted` and `subscribed`. You always get the publication, even for tracks you never receive.
- A **Track** is the playable media. A publication only has a `.track` once you subscribe.

To **subscribe** is to ask the server to forward a track's media to you. **`autoSubscribe`** is on by default, so a participant is subscribed to every existing track and every future one. Turn it off and you get **selective subscription**: you pick tracks yourself, from the client or with the server's `UpdateSubscriptions` call ([subscribing](https://docs.livekit.io/transport/media/subscribe#selective-subscription)). From the docs, in Python:

```python
await room.connect(url, token, rtc.RoomOptions(auto_subscribe=False))
# Also subscribe to tracks published before participant joined
for p in room.remote_participants.values():
  for pub in p.track_publications.values():
    pub.set_subscribed(True)
```

A publisher can also limit who may subscribe to its tracks with `set_track_subscription_permissions` ([track permissions](https://docs.livekit.io/transport/media/publish#track-permissions)). The docs also say to mute or unsubscribe rather than unpublish, because publishing again means another negotiation and a slower first byte.

<figure>
<svg viewBox="0 0 760 300" role="img" aria-labelledby="t-rpt-model d-rpt-model">
  <title id="t-rpt-model">Room, participants, track and publication on the lab</title>
  <desc id="d-rpt-model">Room lesson-rpt holds two participants. Alice publishes a track named mic with source microphone. The SFU forwards it. Bob holds a publication for alice's mic, and because bob is subscribed, the publication has a track with the media.</desc>
  <defs><marker id="ah-rpt-model" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect class="box" x="16" y="30" width="728" height="236" rx="12" stroke-dasharray="6 4"/>
  <text x="32" y="54" font-size="15" font-weight="700">Room lesson-rpt</text>
  <g text-anchor="middle">
    <rect class="box" x="40" y="70" width="220" height="170" rx="10"/>
    <text x="150" y="94" font-size="15">Participant alice</text>
    <text x="150" y="114" font-size="13" class="small">kind STANDARD (local)</text>
    <rect class="box hot" x="60" y="130" width="180" height="50" rx="8"/>
    <text x="150" y="152" font-size="14">Track: mic</text>
    <text x="150" y="170" font-size="12" class="small">source MICROPHONE</text>
    <text x="150" y="222" font-size="13" class="small">publishes</text>
    <rect class="box" x="300" y="110" width="160" height="120" rx="10"/>
    <text x="380" y="150" font-size="15">SFU</text>
    <text x="380" y="176" font-size="12" class="small">forwards to each</text>
    <text x="380" y="192" font-size="12" class="small">subscriber</text>
    <rect class="box" x="500" y="70" width="220" height="170" rx="10"/>
    <text x="610" y="94" font-size="15">Participant bob</text>
    <text x="610" y="114" font-size="13" class="small">kind STANDARD (remote)</text>
    <rect class="box" x="520" y="130" width="180" height="50" rx="8"/>
    <text x="610" y="152" font-size="14">Publication alice/mic</text>
    <text x="610" y="170" font-size="12" class="small">subscribed: has .track</text>
    <text x="610" y="222" font-size="13" class="small">auto-subscribed</text>
  </g>
  <path class="arrow" d="M240 155 H296" marker-end="url(#ah-rpt-model)"/>
  <path class="arrow" d="M460 155 H516" marker-end="url(#ah-rpt-model)"/>
  <text x="380" y="290" font-size="13" class="small" text-anchor="middle">Bob always gets the publication. He only gets the Track (the media) once he subscribes.</text>
</svg>
<figcaption>The same room the lab script builds. A publication is metadata about a track. The Track object only exists for subscribers.</figcaption>
</figure>

## What the SDK tells you

The Python `rtc.Room` emits events as the room changes. The ones you will use most are `participant_connected`, `participant_disconnected`, `track_published`, `track_subscribed`, `track_unsubscribed`, `track_muted`, `participant_attributes_changed`, `room_metadata_changed`, `token_refreshed` and `disconnected` (the `EventTypes` list in the installed package; see also [handling events](https://docs.livekit.io/intro/basics/rooms-participants-tracks/webhooks-events#handling-events)). `track_published` means a track exists. `track_subscribed` means its media is now reaching you. Code that wants audio waits for the second one.

## On the lab

`code/livekit/two_participants.py` has alice join and publish a microphone track. One second later bob joins with default options, and after that a second "alice" joins:

```python
def watch(room: rtc.Room, who: str):
    room.on("participant_connected", lambda p: print(f"[{who}] participant_connected {p.identity} kind={rtc.ParticipantKind.Name(p.kind)}"))
    room.on("track_published", lambda pub, p: print(f"[{who}] track_published {p.identity}/{pub.name} (a publication: metadata only)"))
    room.on("track_subscribed", lambda t, pub, p: print(f"[{who}] track_subscribed {p.identity}/{pub.name} kind={rtc.TrackKind.Name(t.kind)} (now media flows)"))
    room.on("disconnected", lambda reason: print(f"[{who}] disconnected reason={rtc.DisconnectReason.Name(reason)}"))
...
    bob = rtc.Room()
    watch(bob, "bob")
    await bob.connect(URL, token("bob", ROOM))       # auto_subscribe defaults to True
...
    alice2 = await join("alice", ROOM)
```

Real output:

```text
[alice] published track sid=TR_AMCR9psuAV2nCr source=SOURCE_MICROPHONE
[bob] track_subscribed alice/mic kind=KIND_AUDIO (now media flows)
[alice] participant_connected bob kind=PARTICIPANT_KIND_STANDARD
[bob] sees alice/mic subscribed=True

-- a second 'alice' joins with the same identity --
[alice] disconnected reason=DUPLICATE_IDENTITY
[alice2] connected=True  [alice] connected=False
[bob] disconnected reason=CLIENT_INITIATED
```

Four things to read here:

1. Bob never printed `track_published` for alice's mic. A track that already exists when you connect comes with the connect itself, as part of the room state. If you only subscribe in a `track_published` handler, you miss it. That is why the docs snippet above also loops over `remote_participants`.
2. Bob got `track_subscribed` without asking. That is auto-subscribe.
3. Alice heard `participant_connected bob` after bob was already receiving her audio. Others are only told about a participant once it is ACTIVE.
4. The second alice took the seat, and the first was disconnected with `DUPLICATE_IDENTITY`. The last line is bob's own `disconnect()` at the end of the script.

:::note Self-hosted vs Cloud
The `CONNECTOR` kind only appears with connectors (WhatsApp, Twilio), which are LiveKit Cloud features. On self-hosted, phone callers arrive as `SIP` participants through the `livekit/sip` service. `kind_details` values such as `CLOUD_AGENT` and `FORWARDED` also come from Cloud features. On self-hosted, a room lives on one node, so a room is limited to what that node can carry ([LiveKit SFU](https://docs.livekit.io/reference/internals/livekit-sfu)).
:::

:::tip CLI
- `lk room create --empty-timeout 120 --departure-timeout 10 demo`
- `lk room list`
- `lk room join --identity bot_user --publish-demo test_room`
- `lk room participants list ROOM_NAME`
- `lk room participants get --room NAME IDENTITY`
- `lk room update-subscriptions --room NAME --identity ID [--subscribe | --unsubscribe] TRACK_SID [TRACK_SID ...]`
- `lk room mute-track --room NAME --identity ID [--mute | --unmute] TRACK_SID`

From the [CLI reference](https://docs.livekit.io/reference/developer-tools/livekit-cli/rooms). Note that `lk room join` defaults `--auto-subscribe` to `false`, unlike the SDKs.
:::

:::try
In `two_participants.py`, connect bob with `rtc.RoomOptions(auto_subscribe=False)`. Predict the output before you run it: which lines go away, and what does `subscribed=` print? Then add a `track_published` handler that calls `pub.set_subscribed(True)` and check whether bob ever gets alice's mic. (He shouldn't, because her track existed before he joined.)
:::

:::warn Fixed identities kick each other out
Only one participant can hold an identity at a time. If a worker, a test script or a second browser tab connects with a hard-coded identity like `"agent"`, the newest one wins and the other is disconnected with `DUPLICATE_IDENTITY`. Nothing raises an exception. The only trace is the reason code on the `disconnected` event, so log it. Use one identity per real participant. The token docs also say to keep personal data out of identities and room names, because they end up in logs ([tokens & grants](https://docs.livekit.io/frontends/reference/tokens-grants)).
:::

:::note What we did not test
We didn't test hidden participants, `max_participants` enforcement, publisher-side track permissions, `UpdateSubscriptions`, or the room timeouts expiring. The 15-second linger after a crash comes from the docs; we didn't kill a process to time it. The meanings of the four states come from comments in the protocol source, not from the docs.
:::

:::say
A room holds participants, a participant publishes tracks, and you always see the publication but only get the media once you're subscribed.
:::

:::check Your agent subscribes in a `track_published` handler and never hears the caller, who joined first. Why?
The caller's track already existed when the agent connected, so it arrived with the room state and no `track_published` event fired for it. Either keep auto-subscribe on, or also loop over `remote_participants` after connecting and subscribe to existing publications.
:::

:::check What is the difference between a TrackPublication and a Track?
The publication is the server's record that a track exists: sid, source, name, muted, subscribed. Every participant sees it. The Track is the media itself, and it only exists on the publication once you're subscribed.
:::
