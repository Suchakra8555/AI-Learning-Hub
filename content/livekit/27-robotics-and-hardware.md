---
title: Robotics and hardware
summary: What LiveKit offers when the participant is a robot. Data tracks, RPC and attributes as control channels, low playout delay, hardware encoders, LiveKit Portal and Portal for ROS. From the docs only; nothing here was run on the lab.
time: 15 min
---

A robot arm is in one city and its operator in another. The operator needs to see what the camera sees now, not half a second ago. A command that arrives late is worse than one that never arrives. A voice room is tuned for smooth playback, which is the wrong default here. **Nothing in this lesson was run on the lab.** It is a map of the docs, so you know what exists before you build on it.

## Four channels between robot and operator

LiveKit's robotics docs split robot traffic by what each kind of data needs ([Publishing data](https://docs.livekit.io/robotics/media/data)):

- **Data tracks**: named publish/subscribe channels for binary frames, set up like audio tracks. Delivery is in order but lossy. Frames are never resent, so under pressure old frames are dropped, not delayed. Each frame can carry a 64-bit user timestamp. Use them for IMU, LiDAR, telemetry and control input. Publishing needs `canPublishData` ([Data tracks](https://docs.livekit.io/robotics/media/data/data-tracks)). The Python SDK has `room.local_participant.publish_data_track(name=...)`.
- **RPC**: call a method on the other side and await the reply, for example "home" or "run this policy" ([RPC for robots](https://docs.livekit.io/robotics/media/data/rpc)).
- **Participant attributes**: coarse state such as idle, navigating or charging, plus roles. Delivery is reliable, late joiners get the current values, and the limit is 64 KiB per participant. The docs say to update them no more than once every few seconds ([Attributes](https://docs.livekit.io/robotics/media/data/participant-attributes)).
- **Video tracks** for cameras, plus reliable byte streams for maps, logs and files.

<figure>
<svg viewBox="0 0 800 250" role="img" aria-labelledby="t-rob-ch d-rob-ch">
  <title id="t-rob-ch">Channels between an operator and a robot through LiveKit</title>
  <desc id="d-rob-ch">An operator on the left and a robot on the right, both connected to a LiveKit server in the middle. From robot to operator flow a video track from the camera and a data track with sensors and state. From operator to robot flow a data track with control commands. RPC goes both ways as request and reply, and participant attributes with status and role are synced both ways.</desc>
  <defs><marker id="ah-rob" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="20" y="40" width="130" height="190" rx="10"/><text x="85" y="130">Operator</text><text x="85" y="150" font-size="12" class="small">human or policy</text>
    <rect class="box hot" x="335" y="40" width="130" height="190" rx="10"/><text x="400" y="130">LiveKit</text><text x="400" y="150" font-size="12" class="small">SFU forwards</text>
    <rect class="box" x="650" y="40" width="130" height="190" rx="10"/><text x="715" y="130">Robot</text><text x="715" y="150" font-size="12" class="small">camera, motors</text>
  </g>
  <text x="400" y="24" font-size="12" class="small" text-anchor="middle">each line runs operator ↔ server ↔ robot</text>
  <g font-size="12" class="small" text-anchor="middle">
    <path class="arrow" d="M335 72 H154" marker-end="url(#ah-rob)"/><path class="arrow" d="M650 72 H469" marker-end="url(#ah-rob)"/><text x="242" y="66">video track (camera)</text>
    <path class="arrow" d="M335 110 H154" marker-end="url(#ah-rob)"/><path class="arrow" d="M650 110 H469" marker-end="url(#ah-rob)"/><text x="242" y="104">data track: sensors, state</text>
    <path class="arrow" stroke-width="3" d="M150 148 H331" marker-end="url(#ah-rob)"/><path class="arrow" stroke-width="3" d="M465 148 H646" marker-end="url(#ah-rob)"/><text x="557" y="142">data track: commands</text>
    <path class="arrow" stroke-dasharray="5 5" d="M154 186 H331" marker-start="url(#ah-rob)" marker-end="url(#ah-rob)"/><path class="arrow" stroke-dasharray="5 5" d="M469 186 H646" marker-start="url(#ah-rob)" marker-end="url(#ah-rob)"/><text x="557" y="180">RPC: request, reply</text>
    <path class="arrow" stroke-dasharray="2 4" d="M154 218 H331" marker-start="url(#ah-rob)" marker-end="url(#ah-rob)"/><path class="arrow" stroke-dasharray="2 4" d="M469 218 H646" marker-start="url(#ah-rob)" marker-end="url(#ah-rob)"/><text x="242" y="212">attributes: status, role</text>
  </g>
</svg>
<figcaption>Lossy data tracks carry anything where only the newest value matters. RPC and attributes are reliable and slower to change.</figcaption>
</figure>

## Where agents fit

The same channels let an AI sit on either side. In **remote inference**, a policy too large for the robot runs in the cloud as the operator. Camera frames and joint state go up, and actions stream back fast enough to close the control loop ([Remote inference](https://docs.livekit.io/robotics/start/use-cases/remote-inference)). In **voice control**, a normal LiveKit agent talks to people near the robot. Its tools trigger robot actions over RPC, and slow actions run as async tools so the agent keeps talking ([Voice for robots](https://docs.livekit.io/robotics/start/use-cases/voice)). That second pattern is the agent from the earlier lessons with one more kind of tool.

## Cutting latency

Every subscriber holds video in a jitter buffer. **Playout delay hints** set a room-wide minimum and maximum for that buffer. For teleoperation the docs recommend 0 and 10 ms ([Playout delay hints](https://docs.livekit.io/robotics/media/performance/low-latency/playout-delay)). They apply to video only, in 10 ms steps, and lip-sync can drift. Audio is not affected. **Zero jitter buffer mode** turns the buffer off entirely, but only in the Rust SDK (`livekit::webrtc::enable_zero_playout_delay()`) ([Zero jitter buffer](https://docs.livekit.io/robotics/media/performance/low-latency/zero-jitter)).

The Rust and Python SDKs use a hardware encoder automatically when one exists. On Nvidia Jetson that is Jetson MMAPI with H.264, H.265 and AV1, and AV1 needs Orin-class hardware ([Hardware encoders](https://docs.livekit.io/robotics/media/video/encoders)). For small devices, see the ESP32 SDK in [Frontends and sessions](lesson:livekit/frontends-and-sessions).

## LiveKit Portal and Portal for ROS

**LiveKit Portal** is a thin layer for robot apps. A `Robot` publishes video and state and receives actions. An `Operator` sends actions and receives **observations**, which are camera frames and state matched by sender timestamp ([Portal concepts](https://docs.livekit.io/robotics/integrations/portal/concepts)). Both sides declare the same schema. Only one operator controls the robot at a time, and actions from anyone else are dropped. The optional LeRobot plugins make a remote arm look like a local LeRobot device. The docs say Portal runs the same on self-hosted servers ([Portal](https://docs.livekit.io/robotics/integrations/portal)).

**LiveKit Portal for ROS** bridges a ROS 2 graph into a room. It supports Humble, Jazzy, Kilted and Lyrical, but not ROS 1. It ships as the `livekit/ros-portal:<distro>` image, which runs with `--network host` so DDS can find the graph. With no config it forwards every topic both ways ([ROS Portal](https://docs.livekit.io/robotics/integrations/ros-portal), [quickstart](https://docs.livekit.io/robotics/integrations/ros-portal/quickstart)).

:::note Self-hosted vs Cloud
The robotics pages don't mark any of these features Cloud-only, and Portal names self-hosted servers outright. The SDK features (data tracks, zero jitter buffer) still need SDK and server versions that support them. We haven't checked livekit-server v1.13.11 against data tracks.
:::

:::tip CLI
Set the low-latency hints when you create the room ([CLI rooms reference](https://docs.livekit.io/reference/developer-tools/livekit-cli/rooms)):

```bash
lk room create --name my-robot --min-playout-delay 0 --max-playout-delay 10
lk token create --join --room my-robot --identity robot-1 --valid-for 1h
```
:::

:::try
On the lab, create `my-robot` with the command above and run `lk room list`. Does the server echo the playout delay back? Then join with `lk room join --publish-demo` and think about what a 10 ms maximum would do to the demo video on a lossy link.
:::

:::warn Mismatches fail silently
Portal drops packets from a peer whose schema doesn't match and logs one warning per mismatch. Unknown fields are ignored. Out-of-range values are clamped, so `9999` sent to an `I8` field becomes `127`. When observations or actions don't arrive, check the schema and field names first. On the robot side, treat every command as untrusted. Clamp it locally and stop when commands stop ([Robot app](https://docs.livekit.io/robotics/teleop/robot)).
:::

:::note What we did not test
None of it. We didn't publish a data track, set playout delay, run Portal, ROS Portal or LeRobot, or touch Jetson or ESP32 hardware. All of this comes from the docs pages linked above. The only check against our install is that the Python SDK (`livekit` 1.2.0) has `publish_data_track`.
:::

:::say
Robots use video tracks for cameras, lossy data tracks for fresh sensor and control data, RPC for actions and attributes for coarse state, with playout delay turned down for freshness.
:::

:::check Why send joystick commands on a data track and not as RPC calls?
Only the newest command matters. An RPC is a request that waits for a reply, so on a bad link a queue of stale commands can arrive late. A data track drops old frames instead of delaying new ones, and RPC stays for discrete actions like "home".
:::

:::check You set playout delay to 0 and 10 ms, and the operator's video gets choppy while audio sounds fine. Why only the video?
Playout delay hints apply to video only. Audio keeps its automatic buffering, so it still smooths out jitter. The video now has almost no buffer, so late frames show as stutter.
:::
