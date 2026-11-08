---
title: Turns and interruptions
summary: How an agent decides the user is done, and when to stop talking. TurnHandlingOptions in 1.8, the turn detector versions, endpointing and interruption defaults read from the source, Silero VAD settings, and how the old flat kwargs map to the new form.
time: 25 min
---

Users say the agent "keeps cutting me off". Others say it "takes forever to answer". A third group says it "stops talking every time I say mm-hm". All three complaints come from the same few settings. In 1.8 those settings live in one nested dict, and some of their defaults change depending on how you start the agent. This lesson lists the settings, gives their real defaults, and shows what to pin on a self-hosted server.

Versions: `livekit-agents` 1.8.11 with the Silero plugin. Defaults below come from `livekit/agents/voice/turn.py` and were printed by `code/livekit/turn_config.py`.

## The shape of TurnHandlingOptions

Everything about turns goes into `AgentSession(turn_handling=...)`, a typed dict with five keys ([TurnHandlingOptions](https://docs.livekit.io/reference/agents/turn-handling-options)):

```python
turn_handling = {
    "turn_detection": inference.TurnDetector(version="v1-mini"),   # or "vad", "stt", "realtime_llm", "manual"
    "endpointing": {"mode": "fixed", "min_delay": 0.3, "max_delay": 2.5},
    "interruption": {"mode": "vad", "min_duration": 0.5, "false_interruption_timeout": 2.0},
    "preemptive_generation": {"enabled": True, "preemptive_tts": False},
    "user_turn_limit": {"max_words": 100, "max_duration": 30.0},
}
```

**Endpointing** is the wait after the user stops talking before the turn counts as over. **Interruption** is the user talking over the agent, also called barge-in.

## Who decides the turn is over

`turn_detection` picks the strategy ([Turns overview](https://docs.livekit.io/agents/logic/turns)):

| Mode | How it decides | When to use it |
| --- | --- | --- |
| `TurnDetector()` | An audio model on top of VAD, which hears both the words and the intonation | The default, and the right choice for most agents |
| `"vad"` | Silence alone | Lowest latency, or a language the detector lacks |
| `"stt"` | The STT provider's own end-of-utterance signal | STT with built-in endpointing, such as AssemblyAI or Deepgram Flux |
| `"realtime_llm"` | The realtime model's server-side detection | Realtime models that keep their own turn-taking |
| `"manual"` | Your code calls `commit_user_turn()` | Push-to-talk |

The **turn detector** comes in two versions ([Turn detector](https://docs.livekit.io/agents/logic/turns/turn-detector)):

- **`v1`**: the full model, served by LiveKit Inference. That's a Cloud service, and self-hosted use beyond a monthly allowance is billed.
- **`v1-mini`**: a smaller model that runs on the agent's own CPU, free anywhere. Each loaded copy takes about 140 to 250 MB of memory. On Linux, Python loads it once in a shared parent process.

Both cover 14 languages. Both need VAD with `min_silence_duration` of at least 0.25 s, or the session raises `ValueError` at start. Silero's default of 0.55 s passes. Pin the version with `inference.TurnDetector(version="v1-mini")`. The old text detector, `MultilingualModel`, is deprecated and slated for removal in 2.0.

For push-to-talk, set `"manual"` and drive the turn from RPC calls the frontend makes:

```python
@ctx.room.local_participant.register_rpc_method("end_turn")
async def end_turn(data: rtc.RpcInvocationData):
    session.input.set_audio_enabled(False)          # stop listening
    transcript = await session.commit_user_turn()   # Python returns the transcript
```

## The timeline of one turn

<figure>
<svg viewBox="0 0 820 350" role="img" aria-labelledby="t-turn d-turn">
  <title id="t-turn">One user turn, an agent reply, and a false interruption</title>
  <desc id="d-turn">A timeline in seconds. The user speaks from 0.2 to 2.4 seconds. VAD marks the end of speech after 0.55 seconds of silence. The endpointing window runs from 0.5 to 3.0 seconds after the last speech. The turn detector says the user is done early in that window, so the reply starts at about 3.3 seconds. At 3.8 seconds the user coughs. After 0.5 seconds of sound the agent pauses. No words arrive, so after the 2.0 second false-interruption timeout the agent resumes where it stopped.</desc>
  <defs><marker id="ah-turn" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="13" text-anchor="end">
    <text x="105" y="64">User</text><text x="105" y="124">VAD</text><text x="105" y="184">Endpointing</text>
    <text x="105" y="234">Turn detector</text><text x="105" y="294">Agent</text>
  </g>
  <g font-size="12" text-anchor="middle">
    <rect class="box" x="139" y="45" width="209" height="30" rx="6"/><text x="243" y="64">user speaks</text>
    <rect class="box" x="481" y="45" width="57" height="30" rx="6"/><text x="509" y="64">cough</text>
    <rect class="box hot" x="396" y="165" width="237" height="30" rx="6"/>
    <rect class="box" x="396" y="215" width="120" height="30" rx="6"/><text x="456" y="234">done? commit</text>
    <rect class="box hot" x="434" y="275" width="94" height="30" rx="6"/><text x="481" y="294">reply</text>
    <rect class="box" stroke-dasharray="5 4" x="528" y="275" width="200" height="30" rx="6"/><text x="628" y="294">paused, waiting 2.0 s</text>
    <rect class="box hot" x="728" y="275" width="72" height="30" rx="6"/><text x="764" y="294">resumes</text>
  </g>
  <text x="404" y="184" font-size="12">0.5 s to 3.0 s</text>
  <path class="arrow" d="M348 120 H396" marker-end="url(#ah-turn)"/>
  <text x="406" y="124" font-size="12" class="small">end of speech after min_silence_duration 0.55 s</text>
  <path class="arrow" d="M434 245 V271" marker-end="url(#ah-turn)"/>
  <path class="arrow" stroke-dasharray="4 4" d="M528 75 V271" marker-end="url(#ah-turn)"/>
  <path class="arrow" d="M120 330 H800"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="120" y="346">0 s</text><text x="215" y="346">1 s</text><text x="310" y="346">2 s</text><text x="405" y="346">3 s</text>
    <text x="500" y="346">4 s</text><text x="595" y="346">5 s</text><text x="690" y="346">6 s</text><text x="785" y="346">7 s</text>
  </g>
</svg>
<figcaption>The endpointing window sets the earliest and latest the turn can close. The detector picks a point inside it. A sound with no words pauses the agent, which resumes after the false-interruption timeout.</figcaption>
</figure>

## Endpointing

`mode="fixed"` uses `min_delay` and `max_delay` as given. `mode="dynamic"` (Python only) learns from the session's own pauses and moves inside that range, with `alpha` as the moving-average weight ([EndpointingOptions](https://docs.livekit.io/reference/agents/turn-handling-options#endpointingoptions)). The defaults are 0.5 s and 3.0 s. With the audio turn detector, any value you leave unset becomes 0.3 s and 2.5 s, because the model gives a confident end-of-turn signal. In VAD mode, `min_delay` works like `max(VAD silence, min_delay)`. In STT mode it adds to the provider's own delay. You can change endpointing mid-call with `session.update_options(endpointing_opts={...})`.

## Interruptions

The interruption defaults, from the source:

```text
{'enabled': True, 'discard_audio_if_uninterruptible': True, 'min_duration': 0.5, 'min_words': 0, 'resume_false_interruption': True, 'false_interruption_timeout': 2.0, 'backchannel_boundary': (1.0, 1.0)}
```

- `min_duration` and `min_words` filter what counts. `min_words` needs STT.
- A **false interruption** is sound that paused the agent but produced no transcript, like a cough. After `false_interruption_timeout` with no words, the agent resumes where it stopped, and `agent_false_interruption` fires.
- `mode="adaptive"` uses a model that tells a real barge-in from **backchannel**, short "uh-huh" or "right" sounds that mean "go on" ([Adaptive interruption handling](https://docs.livekit.io/agents/logic/turns/adaptive-interruption-handling)). It runs on LiveKit Inference. `backchannel_boundary` turns it off for 1 s at the start and end of each agent turn. `mode="vad"` treats any long enough speech as a barge-in.
- Speech sent with `say(..., allow_interruptions=False)` can't be cut off. `handle.interrupt()` then raises `RuntimeError` unless you pass `force=True`.

Two more keys sit in the same dict. `preemptive_generation` (on by default) starts the LLM on the final transcript before the turn is confirmed. `preemptive_tts` (off) starts TTS early too, trading compute for latency. `user_turn_limit` (off by default) lets the agent cut in after `max_words` or `max_duration`, through the `on_user_turn_exceeded` hook.

## Silero VAD

`silero.VAD.load()` defaults, printed on the lab ([Silero VAD](https://docs.livekit.io/agents/logic/turns/vad)):

| Option | Default | Effect |
| --- | --- | --- |
| `min_speech_duration` | 0.05 s | Speech needed to start a chunk |
| `min_silence_duration` | 0.55 s | Silence needed to call speech ended |
| `prefix_padding_duration` | 0.5 s | Audio kept from before speech started |
| `max_buffered_speech` | 60.0 s | Buffer cap |
| `activation_threshold` | 0.5 | Higher misses soft speech, lower hears noise |
| `deactivation_threshold` | 0.35 | When a frame stops counting as speech |
| `sample_rate` | 16000 | 8000 or 16000 only |

Load it once per process in `setup_fnc` and pass `ctx.proc.userdata["vad"]` to the session, as in the previous lesson.

## On the lab: the config, and the 1.6 mapping

`code/livekit/turn_config.py` needs no server. It builds a self-hosted config and runs the library's own migration function on 1.6-style flat kwargs:

```python
SELF_HOSTED: TurnHandlingOptions = {
    "turn_detection": inference.TurnDetector(version="v1-mini"),   # runs on local CPU; "v1" runs on LiveKit Inference
    "endpointing": {"mode": "fixed", "min_delay": 0.3, "max_delay": 2.5},
    "interruption": {"mode": "vad", "min_duration": 0.5, "false_interruption_timeout": 2.0},  # "adaptive" needs Cloud keys
    "preemptive_generation": {"enabled": True, "preemptive_tts": False},
}
...
old = dict(min_endpointing_delay=0.4, max_endpointing_delay=3.0, allow_interruptions=True,
           min_interruption_duration=0.6, min_interruption_words=2, false_interruption_timeout=1.5,
           resume_false_interruption=True, preemptive_generation=True)
print("new nested form :", json.dumps(turn._migrate_turn_handling(**old)))
```

Real output:

```text
Silero VAD options: {'min_speech_duration': 0.05, 'min_silence_duration': 0.55, 'prefix_padding_duration': 0.5, 'max_buffered_speech': 60.0, 'activation_threshold': 0.5, 'deactivation_threshold': 0.35, 'sample_rate': 16000}
built-in defaults (no turn detector):
  endpointing : {'mode': 'fixed', 'min_delay': 0.5, 'max_delay': 3.0, 'alpha': 0.9}
  interruption: {'enabled': True, 'discard_audio_if_uninterruptible': True, 'min_duration': 0.5, 'min_words': 0, 'resume_false_interruption': True, 'false_interruption_timeout': 2.0, 'backchannel_boundary': (1.0, 1.0)}
self-hosted turn handling:
  turn_detection         TurnDetector(version=v1-mini)
  endpointing            {'mode': 'fixed', 'min_delay': 0.3, 'max_delay': 2.5}
  interruption           {'mode': 'vad', 'min_duration': 0.5, 'false_interruption_timeout': 2.0}
  preemptive_generation  {'enabled': True, 'preemptive_tts': False}
old flat kwargs : {"min_endpointing_delay": 0.4, "max_endpointing_delay": 3.0, "allow_interruptions": true, "min_interruption_duration": 0.6, "min_interruption_words": 2, "false_interruption_timeout": 1.5, "resume_false_interruption": true, "preemptive_generation": true}
new nested form : {"endpointing": {"min_delay": 0.4, "max_delay": 3.0}, "interruption": {"min_duration": 0.6, "min_words": 2, "false_interruption_timeout": 1.5, "resume_false_interruption": true}, "preemptive_generation": {"enabled": true}}
```

| 1.6 flat kwarg | 1.8 nested key |
| --- | --- |
| `min_endpointing_delay` / `max_endpointing_delay` | `endpointing.min_delay` / `endpointing.max_delay` |
| `allow_interruptions=False` | `interruption.enabled = False` |
| `min_interruption_duration` / `min_interruption_words` | `interruption.min_duration` / `interruption.min_words` |
| `false_interruption_timeout`, `agent_false_interruption_timeout` | `interruption.false_interruption_timeout` |
| `resume_false_interruption` | `interruption.resume_false_interruption` |
| `discard_audio_if_uninterruptible` | `interruption.discard_audio_if_uninterruptible` |
| `preemptive_generation=True` | `preemptive_generation.enabled = True` |
| `turn_detection` | `turn_detection` |

Note that `allow_interruptions: true` disappears from the output. Only `False` maps to anything, because `True` is already the default. The flat kwargs still work in 1.8 but are deprecated.

:::note Self-hosted vs Cloud
Turn detector `v1` and adaptive interruption both run on LiveKit Inference, a Cloud service. Self-hosted, use `TurnDetector(version="v1-mini")` and `interruption={"mode": "vad"}`, then tune `min_duration` and `min_words` to cope with backchannel. The docs also suggest Cloud observability to check tuning. Self-hosted, log `agent_false_interruption` and state events yourself. For how a production platform turns per-assistant settings into these dicts, see [Tuning turns as pure functions](lesson:voice-prod/tuning-turns-as-pure-functions).
:::

:::warn `dev` and `start` pick different models
With no `version`, 1.8.11 resolves the turn detector as `"v1" if is_hosted() or is_dev_mode() else "v1-mini"` (`inference/eot/detector.py`). Adaptive interruption gets the same test in `voice/agent_activity.py`. So the same code uses Cloud models under `dev` and local ones under `start`. In `dev` it sends your self-hosted API key to LiveKit Inference. The docs say a failed request falls back to `v1-mini` for the rest of the session, but we didn't watch that happen. Always pin `version="v1-mini"` and `"mode": "vad"` so dev and prod behave the same.
:::

:::tip CLI
No `lk` command tunes turns. Test them with `lk agent console` (talk through your microphone, `--text` for typing) and `lk agent dev`. `lk agent debugger` works in text mode and won't exercise VAD.
:::

:::try
Change the `old` dict in `turn_config.py` to `allow_interruptions=False` and add `discard_audio_if_uninterruptible=False`. Predict the nested output, then run it. Next, set Silero's `min_silence_duration=0.2` in a session that uses the turn detector, and note what happens at session start.
:::

:::note What we did not test
No live conversation ran on the lab, so the timeline is drawn from the docs and the defaults, not measured. We didn't run `v1-mini` inference, adaptive interruption, the `v1` fallback or dynamic endpointing. Memory and language figures for the turn detector are from the docs.
:::

:::say
Pin the turn detector to `v1-mini` and interruption to `vad`, then tune endpointing delays and interruption filters, since the defaults change between `dev` and `start`.
:::

:::check The agent replies while users are still mid-sentence after a pause. Which two settings do you look at first?
`turn_detection`: use the turn detector, not `"vad"`, so the decision uses meaning and intonation as well as silence. Then `endpointing.min_delay`: raise it so a short pause doesn't close the turn.
:::

:::check A cough stops the agent, then it goes quiet for two seconds and carries on. Is that a bug?
No. The cough passed `min_duration` and paused the agent. No transcript came, so after `false_interruption_timeout` (2.0 s) the agent resumed, since `resume_false_interruption` is on by default. Lower the timeout to shorten the gap, or raise `min_words` (needs STT) to ignore sounds without words.
:::

Next: [Tools, tasks and workflows](lesson:livekit/tools-tasks-and-workflows)
