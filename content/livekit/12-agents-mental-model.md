---
title: The agents mental model
summary: Agent server, job, session, agent. What each layer owns, how audio flows through a cascaded or realtime pipeline, what RoomIO does for you, and which states, events and close reasons tell you what the agent is doing.
time: 25 min
---

You have a voice agent that works. It joins a room, listens and answers. Then a call hangs in silence, and the log shows `close` with `reason=error`, and you can't tell whether the problem was the room, the process, the session or the model. Most of that confusion comes from not knowing which of four layers owns what. This lesson names the layers and shows where each one starts and stops.

Versions used here: `livekit-agents` 1.8.11 against a self-hosted livekit-server v1.13.11.

## Four layers

The [Agents framework](https://docs.livekit.io/agents) runs your Python code as a participant in a LiveKit room. It is built from four nested pieces:

- **Agent server**: the long-running process you start with `python agent.py start`. It registers with the LiveKit server and waits for work. In 1.8 the class is `AgentServer`. Older code and the logs still call it a "worker".
- **Job**: one unit of work, normally "be the agent in room X". The server runs each job in its own child process, so one crashing call doesn't take down the others ([Server lifecycle](https://docs.livekit.io/agents/server/lifecycle)).
- **AgentSession**: the orchestrator inside a job. It collects user input, runs the voice pipeline, calls the LLM, sends output back and emits events ([Agent sessions](https://docs.livekit.io/agents/logic/sessions)).
- **Agent**: the logic itself: instructions, tools and per-agent model overrides. A session runs one agent at a time and can hand control to another ([Workflows](https://docs.livekit.io/agents/logic/workflows)).

<figure>
<svg viewBox="0 0 760 300" role="img" aria-labelledby="t-mm-layers d-mm-layers">
  <title id="t-mm-layers">The four layers of a LiveKit agent</title>
  <desc id="d-mm-layers">A LiveKit server on the left. To its right, one agent server process holds job processes. One job runs in room echo-test and contains an AgentSession, which holds RoomIO, the current Agent, and the models. A second job runs in another room, and a third process sits idle and prewarmed.</desc>
  <defs><marker id="ah-mm-layers" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="16" y="112" width="130" height="56" rx="10"/><text x="81" y="145">LiveKit server</text>
    <rect class="box" x="200" y="16" width="544" height="270" rx="12"/><text x="472" y="38" font-weight="700">AgentServer (one OS process)</text>
    <rect class="box" x="216" y="52" width="258" height="222" rx="10"/><text x="345" y="72" font-size="13">Job process: room echo-test</text>
    <rect class="box" x="232" y="84" width="226" height="178" rx="10"/><text x="345" y="104" font-size="13">AgentSession</text>
    <rect class="box" x="248" y="116" width="194" height="38" rx="8"/><text x="345" y="140" font-size="12">RoomIO (tracks in and out)</text>
    <rect class="box hot" x="248" y="164" width="194" height="38" rx="8"/><text x="345" y="188" font-size="12">Agent (prompt + tools)</text>
    <rect class="box" x="248" y="212" width="194" height="38" rx="8"/><text x="345" y="236" font-size="12">VAD, STT, LLM, TTS</text>
    <rect class="box" x="490" y="52" width="238" height="100" rx="10"/><text x="609" y="96" font-size="13">Job process: room web-1</text><text x="609" y="118" font-size="12" class="small">its own session and agent</text>
    <rect class="box" x="490" y="168" width="238" height="106" rx="10"/><text x="609" y="214" font-size="13">Idle process</text><text x="609" y="236" font-size="12" class="small">prewarmed, waiting for a job</text>
  </g>
  <path class="arrow" d="M146 140 H196" marker-end="url(#ah-mm-layers)"/>
  <text x="81" y="192" font-size="12" class="small" text-anchor="middle">register + jobs over</text>
  <text x="81" y="208" font-size="12" class="small" text-anchor="middle">one outbound WebSocket</text>
</svg>
<figcaption>The server process only takes jobs. Each job is a separate process that joins one room, and the session inside it does the talking.</figcaption>
</figure>

You can see the job layer on the lab without any AI at all. `code/livekit/echo_agent.py` is a job with no session (the docs call this a **programmatic participant**, any code that joins a room as a participant). When it was dispatched, `code/livekit/echo_check.py` saw it like this:

```text
in the room: agent-AJ_poh7C3cMd4Lq kind=PARTICIPANT_KIND_AGENT
subscribed to agent-AJ_poh7C3cMd4Lq's track
heard my own tone back after 0.63 s
```

The identity is `agent-` plus the job id. One job, one participant, one room. The next lesson covers how that job got there.

## Three ways to build the pipeline

The **pipeline** is the chain that turns user audio into agent audio. The docs list three types ([Pipeline types](https://docs.livekit.io/agents/models/pipelines)):

- **Cascaded**: three models in a row, STT then LLM then TTS. The docs call it the right default for most production agents.
- **Turn-based realtime**: one speech-to-speech model that waits for the user to finish, then answers (the OpenAI Realtime API works this way).
- **Full-duplex realtime**: one model that listens and speaks at the same time and decides turns itself.

| Dimension | Cascaded pipeline | Turn-based realtime | Full-duplex realtime |
| --- | --- | --- | --- |
| End-to-end latency | Moderate | Fastest | Fastest |
| Listens while speaking | No | No | Yes |
| Turn detection | Configurable | Configurable | Model-controlled |
| Tool calling | Mature | Less mature | Less mature |
| Realtime transcription | Yes | Delayed | Delayed |
| Scripted speech (`say()`) | Yes | No | No |
| Prosody-aware comprehension | No | Yes | Yes |
| Expressive speech output | Depends on TTS | Built-in | Built-in |
| Auditability | Full text trail | Limited | Limited |

A **hybrid** pairs a realtime model with a separate TTS, so you keep the model's listening and get `say()` back ([Separate TTS](https://docs.livekit.io/agents/models/realtime#separate-tts)).

<figure>
<svg viewBox="0 0 820 215" role="img" aria-labelledby="t-mm-pipe d-mm-pipe">
  <title id="t-mm-pipe">The cascaded pipeline, stage by stage</title>
  <desc id="d-mm-pipe">Six stages left to right: room audio, VAD, STT, LLM, TTS, and the room track. Under each stage, what goes in and what comes out. Below STT and LLM, a turn detector decides when the user's turn is over and the transcript is committed to the LLM.</desc>
  <defs><marker id="ah-mm-pipe" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="25" y="30" width="110" height="50" rx="10"/><text x="80" y="60">Room audio</text>
    <rect class="box" x="157" y="30" width="110" height="50" rx="10"/><text x="212" y="60">VAD</text>
    <rect class="box" x="289" y="30" width="110" height="50" rx="10"/><text x="344" y="60">STT</text>
    <rect class="box hot" x="421" y="30" width="110" height="50" rx="10"/><text x="476" y="60">LLM</text>
    <rect class="box" x="553" y="30" width="110" height="50" rx="10"/><text x="608" y="60">TTS</text>
    <rect class="box" x="685" y="30" width="110" height="50" rx="10"/><text x="740" y="60">Room track</text>
  </g>
  <g class="arrow">
    <path d="M135 55 H153" marker-end="url(#ah-mm-pipe)"/><path d="M267 55 H285" marker-end="url(#ah-mm-pipe)"/>
    <path d="M399 55 H417" marker-end="url(#ah-mm-pipe)"/><path d="M531 55 H549" marker-end="url(#ah-mm-pipe)"/>
    <path d="M663 55 H681" marker-end="url(#ah-mm-pipe)"/>
  </g>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="80" y="102">Opus from user</text><text x="80" y="118">to PCM frames</text><text x="80" y="134">(RoomIO)</text>
    <text x="212" y="102">frames in</text><text x="212" y="118">speech start/end</text><text x="212" y="134">events out</text>
    <text x="344" y="102">frames in</text><text x="344" y="118">interim + final</text><text x="344" y="134">text out</text>
    <text x="476" y="102">chat context in</text><text x="476" y="118">text and tool</text><text x="476" y="134">calls out</text>
    <text x="608" y="102">text in</text><text x="608" y="118">audio frames</text><text x="608" y="134">out, streamed</text>
    <text x="740" y="102">frames to Opus</text><text x="740" y="118">published to</text><text x="740" y="134">the room</text>
  </g>
  <rect class="box hot" x="300" y="160" width="220" height="40" rx="8"/>
  <text x="410" y="185" font-size="12" text-anchor="middle">turn detector: turn over?</text>
  <path class="arrow" stroke-dasharray="5 5" d="M410 160 V84" marker-end="url(#ah-mm-pipe)"/>
</svg>
<figcaption>Each stage has a clean text or audio interface, which is why you can swap any one of them. The turn detector decides when the STT text goes to the LLM.</figcaption>
</figure>

On the lab, `code/livekit/local_stack_agent.py` builds this chain from local parts only: Silero VAD, a Whisper server behind an OpenAI-compatible API, Ollama, Kokoro TTS and the `v1-mini` turn detector:

```python
session = AgentSession(
    vad=ctx.proc.userdata["vad"],
    stt=openai.STT(base_url="http://127.0.0.1:8000/v1", api_key="local", model="Systran/faster-whisper-small"),
    llm=openai.LLM.with_ollama(model="llama3.1", base_url="http://127.0.0.1:11434/v1"),
    tts=openai.TTS(base_url="http://127.0.0.1:8880/v1", api_key="local", model="kokoro", voice="af_heart"),
    turn_handling={
        "turn_detection": inference.TurnDetector(version="v1-mini"),   # local; "v1" would call LiveKit Inference
        "interruption": {"mode": "vad"},                               # "adaptive" needs LiveKit Cloud keys
    },
)
await session.start(Agent(instructions="You are a helpful voice assistant. ..."), room=ctx.room)
```

We did not run this one against live models. The test machine had no Ollama.

:::note Self-hosted vs Cloud
Most docs examples pass strings such as `"assemblyai/universal-3-6-pro:en"` or `inference.STT(...)`. Those go to **LiveKit Inference**, LiveKit Cloud's hosted model gateway, and need Cloud credentials ([Models](https://docs.livekit.io/agents/models)). Self-hosted, use the provider plugins with your own keys, or point an OpenAI-compatible plugin at a local `base_url` as above. The `noise_cancellation.BVC()` in the session example is Cloud-only too ([Noise cancellation](https://docs.livekit.io/transport/media/noise-cancellation)). Self-hosted, use WebRTC's own echo cancellation and noise suppression, or ai-coustics with your own license key.
:::

## RoomIO: how the session reaches the room

**RoomIO** is the bridge between the session and the room. The session creates one for you. It subscribes to audio, feeds frames into the pipeline, publishes the agent's audio track and sends transcriptions ([RoomIO](https://docs.livekit.io/agents/logic/sessions#roomio)). You shape it with `room_options` on `session.start()`. Defaults from the 1.8.11 source (`voice/room_io/types.py`):

| `RoomOptions` field | Default | What it does |
| --- | --- | --- |
| `audio_input` | on | Takes `AudioInputOptions` (noise cancellation, pre-connect audio). |
| `text_input` | on | Text from the user interrupts the agent and gets a reply. |
| `video_input` | off | Turn on to give the model video frames. |
| `audio_output` | on | 24000 Hz mono track by default (`AudioOutputOptions`). |
| `text_output` | on | Transcriptions; `TextOutputOptions(sync_transcription=False)` sends text as soon as it exists, not in step with audio. |
| `participant_kinds` | CONNECTOR, SIP, STANDARD | Which kinds may be linked. The docs' signature line lists only SIP and STANDARD; the source has three. |
| `participant_identity` | none | Link to this identity instead of the first one to join. |
| `close_on_disconnect` | `True` | Close the session when the linked participant leaves with `CLIENT_INITIATED`, `ROOM_DELETED` or `USER_REJECTED`. |
| `delete_room_on_close` | `False` | Delete the room as the session ends, not after `departure_timeout`. |

The **linked participant** is the one person the agent listens and answers to. By default it's the first standard, SIP or connector participant to join. Agents never count, because `PARTICIPANT_KIND_AGENT` isn't in the list. Change it with `participant_identity` or `session.room_io.set_participant()`.

## States, events and how a session ends

The session reports two state machines, and both arrive as events ([Events](https://docs.livekit.io/reference/agents/events)):

- **Agent state**: `initializing`, `idle`, `listening`, `thinking`, `speaking`. It is also mirrored to the agent's `lk.agent.state` participant attribute, so a frontend can show it without extra code.
- **User state**: `speaking` and `listening` come from VAD. `away` comes after `user_away_timeout` (default 15.0 s) of silence from both sides.

Other events you will use: `user_input_transcribed`, `conversation_item_added`, `speech_created`, `agent_false_interruption`, `error` and `close`. The `close` event carries a `CloseReason`: `error`, `job_shutdown`, `participant_disconnected`, `user_initiated` or `task_completed`.

Errors carry a `recoverable` flag. `True` means the session is already retrying, and the event is only information. `False` means the session will close unless you step in. The docs say LLM and TTS errors are safe to mark recoverable, since those are rebuilt for each reply. STT needs a reset, because its stream lives for the whole session ([Handling errors](https://docs.livekit.io/reference/agents/events#handling-errors)):

```python
@session.on("error")
def on_error(ev: ErrorEvent):
    if ev.error.recoverable:
        return
    if isinstance(ev.source, (tts.TTS, llm.LLM, multimodal.RealtimeModel)):
        ev.error.recoverable = True          # next reply gets a fresh instance
        return
    if isinstance(ev.source, stt.STT):
        session.update_agent(session.current_agent)   # restart the STT stream
        ev.error.recoverable = True
```

:::warn Copying the quickstart onto a self-hosted server
The quickstart and most examples use Inference model strings. On a self-hosted server with self-hosted keys, those calls go to LiveKit Cloud, not to your server, so they can't work there. Pick plugins on day one and keep the model choice in your own config.
:::

:::tip CLI
`lk agent dev`, `lk agent start` and `lk agent console` run your agent in the matching mode ([Startup modes](https://docs.livekit.io/agents/server/startup-modes)). `lk room participants list <ROOM_NAME>` shows the agent as a participant. `lk agent debugger start` and `lk agent debugger say "..."` drive it one turn at a time in text mode.
:::

:::try
Start `code/livekit/echo_agent.py start`, dispatch it with `lk dispatch create --room echo-test --agent-name echo`, then run `lk room participants list echo-test`. Find the job id in the agent identity, then find the same id in the agent server's "received job request" log line. Which layer printed each of the two?
:::

:::note What we did not test
No `AgentSession` with live models ran on the lab. `local_stack_agent.py` is untested against real STT, LLM and TTS servers. State names, close reasons and the error-recovery pattern come from the docs and the 1.8.11 source, not from a recorded session.
:::

:::say
A server takes jobs, each job is a process in one room, the session inside runs the pipeline, and the agent is the prompt and tools it runs.
:::

:::check The agent stops answering when a supervisor joins the room after the caller and the caller hangs up. Why?
The session was linked to the caller, the first participant to join. When the caller left with `CLIENT_INITIATED`, `close_on_disconnect` (default `True`) closed the session, even though the supervisor was still in the room.
:::

:::check Your TTS provider returns a 500 once. Does the call end?
Usually not. The session retries, and the `error` event arrives with `recoverable=True`. Only when retries run out does `recoverable` become `False`. Then the session closes with reason `error` unless your handler marks it recoverable.
:::

Next: [Agent server and dispatch](lesson:livekit/agent-server-and-dispatch)
