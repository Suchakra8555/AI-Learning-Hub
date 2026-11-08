---
title: Tuning turns as pure functions
summary: Each assistant needs its own turn-taking settings, and none of them may leak into the next call. See how the platform turns config into plain dicts it can unit-test, and how it stops the agent's voice on the phone line when the caller cuts in.
time: 25 min
---

A booking line wants the agent to reply the moment the caller stops. A line for elderly callers wants it to wait through long pauses. Both run on the same worker processes. If the turn settings live inside the worker's call setup, tangled with SDK objects, you can only test them by placing a call. And if one call's settings stay on a shared object, the next caller gets them.

This lesson builds on [knowing when to speak](lesson:voice/knowing-when-to-speak), which covers VAD, turn detectors and endpointing.

## Config in, plain dicts out

A **pure function** returns the same output for the same input and changes nothing else. The platform keeps all turn tuning in one module of pure functions. They take the assistant's behavior config (a dict from the database) and the STT's capabilities, and return plain dicts: options for the session, options for Silero VAD, extra STT parameters. The module doesn't import LiveKit. Tests call it with a dict and check the dict that comes back.

An empty config returns exactly what the worker built before the module existed. So a new setting can be switched on for a few assistants, compared, and removed again without a deploy.

## One knob picks the strategy

A **latency profile** (`fast`, `balanced` or `accurate`) is the one setting most assistants need. The module looks at what the STT can do and picks one of three end-of-turn strategies. LiveKit's docs list these modes, including STT endpointing for providers "such as AssemblyAI or Deepgram Flux", VAD only, and the turn detector model ([LiveKit turns](https://docs.livekit.io/agents/build/turns/)).

| Strategy | Used when | Who decides the turn ended | Endpointing min / max, s (fast · balanced · accurate) |
|---|---|---|---|
| Native end-of-turn | The STT reports its own end of turn (Deepgram Flux, AssemblyAI) | The STT | 0 / 1.5 · 0 / 2.5 · 0 / 3.0, fixed |
| Streaming | Streaming STT with no end-of-turn signal | The turn model, with dynamic endpointing | 0.25 / 2.0 · 0.3 / 2.5 · 0.5 / 3.0 |
| Batch | No streaming mode | Silero VAD alone | 0.3 / 2.0 · 0.4 / 2.5 · 0.55 / 3.0, fixed |

**Dynamic endpointing** "adapts the delay within that range based on session pause statistics", per the same page, which marks it Python only. Any explicit key in the config, such as a minimum delay, still beats the profile.

## Interruption sensitivity as a formula

Operators set one number from 0 to 1. The module turns it into LiveKit's minimum speech duration before the caller counts as interrupting. The formula is linear (a fresh copy, not the platform's code):

```python
def min_interruption_seconds(sensitivity=0.5):
    return 1.0 - 0.8 * sensitivity     # 0 -> 1.0 s, 0.5 -> 0.6 s, 1 -> 0.2 s
```

Two more knobs sit beside it. A minimum word count stops a cough or "mm-hm" from cutting the agent off. A **false interruption** is a cut-in that turns out to be noise. LiveKit can wait a set silence after it and then resume "from where it left off".

:::note The same knobs in livekit-agents 1.8
The platform is on 1.6.8 and passes these as flat `AgentSession` arguments. In 1.8 they still work but are deprecated, and they move under `turn_handling=TurnHandlingOptions(...)`. This is the mapping the library itself applies (`_migrate_turn_handling` in 1.8.11):

| Flat argument (1.6) | `TurnHandlingOptions` key (1.8) |
|---|---|
| `min_endpointing_delay`, `max_endpointing_delay` | `endpointing.min_delay`, `endpointing.max_delay` |
| `min_interruption_duration` (the sensitivity formula's output) | `interruption.min_duration` |
| `min_interruption_words` | `interruption.min_words` |
| `false_interruption_timeout`, `resume_false_interruption` | `interruption.false_interruption_timeout`, `interruption.resume_false_interruption` |
| `allow_interruptions=False` | `interruption.enabled: false` (`True` is the default and maps to nothing) |
| `preemptive_generation=True` | `preemptive_generation: {"enabled": true}` |
| `turn_detection` | `turn_detection` |

A self-hosted agent should also pin `TurnDetector(version="v1-mini")` and `interruption={"mode": "vad"}`. The 1.8 defaults can reach for LiveKit Inference, a Cloud service. [Turns and interruptions](lesson:livekit/turns-and-interruptions) runs both on the lab.
:::

## Reset shared state on every job

The worker loads Silero and the turn model once per process in a **prewarm** step, so idle processes stay warm. A process runs one call at a time, then takes the next. The VAD object is shared across those calls.

If a call only applies its own overrides, the next call on that process inherits them. The platform resets Silero to its load defaults first, then applies the call's settings. The defaults it uses are activation 0.5, deactivation 0.35, minimum silence 0.55 s and minimum speech 0.05 s. The platform read those values from its installed plugin version.

There is also a guard rail. The platform found that the session refuses to start with the turn model if Silero's minimum silence is under 0.25 s, so the module raises any lower value to 0.25 s.

## The greeting nobody can interrupt

The first message is played with `session.say`, which sends text to TTS. LiveKit's docs describe `say()` as TTS playback and `generate_reply()` as the call that prompts the LLM, so a fixed greeting skips an LLM round trip ([LiveKit audio](https://docs.livekit.io/agents/build/audio/)). `allow_interruptions` defaults to true. The platform sets it to false for the greeting, because people say "hello" as they pick up. That "hello" used to cut the greeting off, then the agent answered it about 3 s later.

:::warn Gotcha from the platform
The SDK's default turn-taking waits for the user to speak first. On outbound calls the callee picked up, heard nothing, waited for the agent, and the silence timeout hung up. Only real calls found it. The fix: when the agent places the call, it speaks the first message itself.
:::

## Barge-in on the phone leg

**Barge-in** is the caller talking over the agent. Inside the room, LiveKit stops the agent's speech. But the carrier has already received some agent audio and keeps playing it from its own buffer. The caller hears the agent carry on.

So the bridge watches two things. It keeps the **RMS** (root mean square, a measure of loudness) of each caller frame. It also watches the agent's state. When the agent leaves "speaking" and a caller frame reached RMS 600 within the last 0.6 s, the bridge drops the audio it holds and sends the carrier's clear command: `clearAudio` on Vobiz, `clear` on Twilio, which "empties all buffered audio" ([Twilio docs](https://www.twilio.com/docs/voice/media-streams/websocket-messages)). An RMS of 600 on 16-bit audio is about −35 dBFS, which the platform picked to sit above line noise and below normal speech.

<figure>
<svg viewBox="0 0 760 330" role="img" aria-labelledby="t-barge d-barge">
  <title id="t-barge">Barge-in on the phone leg</title>
  <desc id="d-barge">Four lanes over time. The agent is speaking, then switches to listening. The caller starts talking loudly a little before that. At the switch the bridge checks whether the caller was loud in the last 0.6 seconds. It was, so the bridge drops its buffered audio and sends the clear command, and the carrier empties its playback buffer.</desc>
  <defs><marker id="ah-barge" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="15" font-weight="700">
    <text x="16" y="55">Agent</text><text x="16" y="115">Caller</text><text x="16" y="200">Bridge</text><text x="16" y="275">Carrier</text>
  </g>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="120" y="30" width="360" height="40" rx="8"/><text x="300" y="55">speaking</text>
    <rect class="box" x="480" y="30" width="260" height="40" rx="8"/><text x="610" y="55">listening</text>
    <rect class="box" x="120" y="90" width="260" height="40" rx="8"/><text x="250" y="115">silent or line hiss</text>
    <rect class="box hot" x="380" y="90" width="360" height="40" rx="8"/><text x="560" y="115">talking, RMS 600 or more</text>
    <rect class="box hot" x="490" y="160" width="250" height="40" rx="8"/><text x="615" y="185">loud in the last 0.6 s? yes</text>
    <rect class="box" x="490" y="212" width="250" height="34" rx="8"/><text x="615" y="234">drop buffer, send clear</text>
    <rect class="box" x="120" y="256" width="400" height="34" rx="8"/><text x="320" y="278">plays agent audio it already has</text>
    <rect class="box hot" x="530" y="256" width="210" height="34" rx="8"/><text x="635" y="278">buffer emptied</text>
  </g>
  <path class="arrow" stroke-dasharray="4 4" d="M480 20 V300"/>
  <path class="arrow" d="M380 146 H478" marker-start="url(#ah-barge)" marker-end="url(#ah-barge)"/>
  <text x="380" y="166" font-size="12" class="small">0.6 s window</text>
  <path class="arrow" d="M615 200 V210" marker-end="url(#ah-barge)"/>
  <path class="arrow" d="M635 246 V254" marker-end="url(#ah-barge)"/>
  <text x="480" y="320" font-size="12" class="small" text-anchor="middle">the agent leaves "speaking"</text>
</svg>
<figcaption>The RMS check separates a real barge-in from the agent simply finishing a sentence. Only the first should flush the carrier's buffer.</figcaption>
</figure>

Why check loudness at all? The agent also leaves "speaking" when it just finishes a sentence. Then the carrier's buffer still holds the end of that sentence, and clearing it would chop it off.

`code/voice-prod/barge_in.py` models this with three callers:

```python
def agent_stopped_speaking(self, t):
    if self.loud_at and t - self.loud_at[-1] <= WINDOW_S:
        dropped, self.queued_to_phone = self.queued_to_phone, 0
        return f"clear: dropped {dropped} queued frames, sent carrier clear command"
    return "no clear: agent just finished its sentence"
```

```text
caller silent rms=    35 -> no clear: agent just finished its sentence
line hiss     rms=   212 -> no clear: agent just finished its sentence
caller talks  rms=  2122 -> clear: dropped 25 queued frames, sent carrier clear command
```

The script queues 25 frames on the bridge side. In the platform, the bridge holds less than one frame (the part its frame chunker hasn't sent yet). Most of the backlog sits at the carrier, which is why the clear command matters.

:::try
Change `THRESHOLD` from 600 to 200 and predict the `line hiss` row. Then think about a real call: if line hiss always crosses the threshold, what happens every time the agent finishes a sentence normally?
:::

:::note What we did not test
We did not run LiveKit or place a call. The Silero defaults and the 0.25 s floor come from the platform's notes on livekit-agents 1.6.8, not from LiveKit's docs. The RMS threshold of 600 is one fixed number. We did not check it against different carriers or quiet callers.
:::

## The rule

Keep tuning in pure functions you can test without a call. Reset anything shared before each job. Clamp values the SDK will reject. On the phone leg, stop the agent and also flush the carrier's buffer.

:::say
Turn settings are data: compute them in plain functions, reset them every call, and flush the carrier when the caller cuts in.
:::

:::check Why doesn't the bridge send the clear command every time the agent stops speaking?
The agent also stops when it finishes a sentence. The carrier would then throw away the end of that sentence. The RMS check only clears when the caller was actually talking.
:::

:::check An operator sets interruption sensitivity to 0.25. How long must the caller speak to interrupt?
1.0 − 0.8 × 0.25 = 0.8 s.
:::

Next: [Events that don't lie](lesson:voice-prod/events-that-dont-lie)
