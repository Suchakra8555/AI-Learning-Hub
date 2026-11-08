---
title: Models without the cloud
summary: Choosing STT, LLM, TTS, realtime and avatar models when you run LiveKit yourself. Plugins versus LiveKit Inference, a fully local stack on Ollama, a Whisper server and Kokoro, non-streaming STT and StreamAdapter, text-only sessions, and what realtime models can't do.
time: 25 min
---

You copy the quickstart into your self-hosted agent: `stt="deepgram/flux-general"`, `llm="google/gemma-4-31b-it"`. Nothing works. Those strings are **LiveKit Inference** model names. LiveKit Inference is a model gateway that is included with LiveKit Cloud and billed through your Cloud project ([LiveKit Inference](https://docs.livekit.io/agents/models/inference)). Your own server has no gateway. This lesson covers what to use instead, all the way to a stack where no audio leaves your machines.

Versions: `livekit-agents` 1.8.11 with the `openai` and `silero` plugins (both 1.8.11).

## Plugins versus Inference

A **plugin** is an open-source package that talks to one provider directly with *your* API key, for example `livekit-agents[openai]` ([Models overview](https://docs.livekit.io/agents/models)). Plugins work anywhere. Inference uses Cloud credentials, which means a LiveKit Cloud project. In code the difference is the import: `inference.STT(...)` or a `"provider/model"` string is Inference, and `openai.STT(...)` or `deepgram.STT(...)` is a plugin.

Many providers copy the OpenAI API, so the OpenAI plugin doubles as a generic client. Give it a `base_url` and it talks to any OpenAI-compatible server, such as Ollama, vLLM, a Whisper server or Kokoro-FastAPI ([OpenAI-compatible LLMs](https://docs.livekit.io/agents/models/llm/openai-compatible-llms)). Use `openai.LLM` (Chat Completions) for these. `openai.responses.LLM` is for OpenAI itself.

| Category | What it does | Docs index (pages, incl. overviews) | Local options in the docs |
|---|---|---|---|
| LLM | Text in, text or tool calls out | about 25 | Ollama via `openai.LLM.with_ollama`, any OpenAI-compatible server |
| STT | Audio in, transcript out | about 35 | Whisper-style servers through `openai.STT(base_url=...)` |
| TTS | Text in, audio out | about 44 | Kokoro through `openai.TTS(base_url=...)` |
| Realtime | Speech in, speech out, one model | about 11 | none listed as local |
| Avatar | Agent audio in, synced video out | about 17 | none listed as local |

The counts come from the docs index (`agents` section). Each includes an overview page and a few how-to pages, so treat them as rough. Turn detection and VAD are models too. **Silero VAD** and the **`v1-mini`** turn detector run on CPU inside the agent process. The full `v1` turn detector is served by LiveKit Inference ([Turn detector](https://docs.livekit.io/agents/logic/turns/turn-detector)).

## A fully local stack

<figure>
<svg viewBox="0 0 780 340" role="img" aria-labelledby="t-ls d-ls">
  <title id="t-ls">A voice agent with every model on your own machines</title>
  <desc id="d-ls">A caller connects to livekit-server on 127.0.0.1:7880 for signaling, with media on UDP 50000 to 50200. The agent process joins the same room. Inside the agent process run Silero VAD and the v1-mini turn detector. The agent calls three local HTTP servers: a Whisper server on 127.0.0.1:8000 for STT, Ollama on 127.0.0.1:11434 for the LLM, and Kokoro-FastAPI on 127.0.0.1:8880 for TTS.</desc>
  <defs><marker id="ah-ls" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="16" y="40" width="150" height="60" rx="10"/><text x="91" y="66">Caller</text><text x="91" y="86" font-size="12" class="small">browser or SIP</text>
    <rect class="box" x="226" y="40" width="200" height="60" rx="10"/><text x="326" y="66">livekit-server</text><text x="326" y="86" font-size="12" class="small">127.0.0.1:7880</text>
    <rect class="box hot" x="486" y="20" width="280" height="110" rx="10"/><text x="626" y="44">Agent process</text>
    <rect class="box" x="500" y="56" width="120" height="58" rx="8"/><text x="560" y="82" font-size="13">Silero VAD</text><text x="560" y="100" font-size="12" class="small">in process</text>
    <rect class="box" x="632" y="56" width="120" height="58" rx="8"/><text x="692" y="82" font-size="13">v1-mini</text><text x="692" y="100" font-size="12" class="small">in process, CPU</text>
    <rect class="box" x="300" y="230" width="150" height="70" rx="10"/><text x="375" y="256">Whisper (STT)</text><text x="375" y="278" font-size="12" class="small">127.0.0.1:8000/v1</text>
    <rect class="box" x="470" y="230" width="150" height="70" rx="10"/><text x="545" y="256">Ollama (LLM)</text><text x="545" y="278" font-size="12" class="small">127.0.0.1:11434/v1</text>
    <rect class="box" x="640" y="230" width="130" height="70" rx="10"/><text x="705" y="256">Kokoro (TTS)</text><text x="705" y="278" font-size="12" class="small">127.0.0.1:8880/v1</text>
  </g>
  <path class="arrow" d="M166 70 H222" marker-start="url(#ah-ls)" marker-end="url(#ah-ls)"/>
  <path class="arrow" d="M426 70 H482" marker-start="url(#ah-ls)" marker-end="url(#ah-ls)"/>
  <path class="arrow" d="M560 130 L380 226" marker-end="url(#ah-ls)"/>
  <path class="arrow" d="M590 130 L548 226" marker-end="url(#ah-ls)"/>
  <path class="arrow" d="M680 130 L700 226" marker-end="url(#ah-ls)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="194" y="122">WebRTC, UDP 50000–50200</text>
    <text x="454" y="122">same room</text>
    <text x="210" y="200">HTTP, all on localhost: no audio leaves the box</text>
  </g>
</svg>
<figcaption>The lab's local stack. Three model servers speak the OpenAI API on fixed ports. VAD and turn detection run inside the agent process.</figcaption>
</figure>

`code/livekit/local_stack_agent.py` wires it up. **It was not run against live models.** The test machine had no Ollama, Whisper server or Kokoro. What we did verify with `livekit-agents` 1.8.11: the file imports, and the objects its entrypoint builds (`openai.STT`, `openai.LLM.with_ollama`, `openai.TTS`, `inference.TurnDetector(version="v1-mini")`, Silero) construct without errors. The key lines:

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
```

The Ollama page documents `with_ollama` with defaults `model="llama3.1"` and `base_url="http://localhost:11434/v1"` ([Ollama](https://docs.livekit.io/agents/models/llm/ollama)). The Kokoro page runs Kokoro-FastAPI on port 8880 and points `openai.TTS` at it. It also says `api_key` must be a non-empty placeholder, because the OpenAI client rejects an empty one ([Kokoro](https://docs.livekit.io/agents/models/tts/kokoro)). Note that `inference.TurnDetector` lives in the `inference` module but runs locally when you pick `v1-mini`. The module name alone doesn't tell you whether something calls the Cloud.

## Non-streaming STT and StreamAdapter

Whisper takes a finished clip, not a live stream. Something has to decide where an utterance ends. That is VAD's job, and **`StreamAdapter`** buffers audio until VAD reports the end of speech, then sends the clip ([STT models](https://docs.livekit.io/agents/models/stt)). The installed `openai.STT` sets `streaming` to `True` only for its realtime-only models, so a custom Whisper model name is non-streaming. We checked:

```python
s = openai.STT(base_url="http://127.0.0.1:8000/v1", api_key="local", model="Systran/faster-whisper-small")
print("streaming:", s.capabilities.streaming, "interim:", s.capabilities.interim_results)
t = openai.TTS(base_url="http://127.0.0.1:8880/v1", api_key="local", model="kokoro", voice="af_heart")
print("tts streaming:", t.capabilities.streaming)
a = lk_stt.StreamAdapter(stt=s, vad=silero.VAD.load())
print("adapter streaming:", a.capabilities.streaming)
```

```text
streaming: False interim: False
tts streaming: False
adapter streaming: True
```

Inside an `AgentSession` you don't wrap it yourself. When the STT can't stream, the session wraps it with the session's VAD, and when the TTS can't stream, it splits the text into sentences ([nodes](https://docs.livekit.io/agents/logic/nodes)). The cost: no interim transcripts, and each sentence waits for the whole clip to be transcribed.

## Text-only sessions, realtime models, avatars

For a chat box or a test, skip audio: `session.start(..., room_options=room_io.RoomOptions(audio_input=False, audio_output=False))`, with `room_io` imported from `livekit.agents`. Then the session needs no STT or TTS at all ([Text and transcriptions](https://docs.livekit.io/agents/multimodality/text#text-only-sessions)).

A **realtime model** takes speech in and gives speech out, so you pass it as `llm=` and skip STT and TTS. The docs list the limits ([Realtime models](https://docs.livekit.io/agents/models/realtime#considerations-and-limitations)). User transcripts are delayed, with no interim results, and often arrive after the reply. There is no scripted `say()`, because `generate_reply(instructions=...)` is not guaranteed to follow a script. Turn detection is best left to the model. History can only be loaded as text. A plugin realtime model such as `openai.realtime.RealtimeModel()` works self-hosted with your own key; `inference.RealtimeModel` is Cloud-only. You can pair a realtime model with your own TTS to get `say()` back ([Pipeline types](https://docs.livekit.io/agents/models/pipelines)).

An **avatar** plugin adds a separate participant, the avatar worker, to the room. The session sends its audio there instead of to the room, and the worker publishes ordinary synced audio and video tracks ([Virtual avatars](https://docs.livekit.io/agents/models/avatar)). To your SFU and your frontend it is just another participant with tracks. All the listed avatar providers are hosted services with their own keys.

## Cost and latency, in words

- Local models remove per-minute API bills and keep audio on your network. You pay for the GPUs or CPUs and for running them. On modest hardware, a local LLM's time to first token and a non-streaming STT both add delay you will hear.
- Hosted plugins cost per use and add a network hop. You can pick each stage on its own merits, and streaming STT gives interim transcripts that help turn detection.
- Realtime models have the lowest baseline latency in LiveKit's comparison. You give up the text trail, scripted speech, and swapping one stage at a time.

Measure on your own calls before you choose (see [Measuring latency on real calls](lesson:voice-prod/measuring-latency-on-real-calls)).

:::note Self-hosted vs Cloud
Cloud-only: LiveKit Inference (`inference.STT/LLM/TTS/RealtimeModel` and `"provider/model"` strings), the `v1` turn detector, adaptive interruption and Inference fallbacks. Self-hosted: every plugin with your own keys, local models through `base_url`, `TurnDetector(version="v1-mini")`, `interruption={"mode": "vad"}`, Silero VAD and `stt/llm/tts.FallbackAdapter`.
:::

:::tip CLI
- `python local_stack_agent.py start` (after `source lab.env`), then `lk dispatch create --room local-1 --agent-name local`
- `lk room participants list local-1` (the agent, and an avatar worker if you add one, show up as participants)
- `lk agent console --text` (a text-only check of the LLM without STT or TTS)
:::

:::try
No models needed: run the check above with the lab venv and confirm `streaming: False`. Then change the model name to `gpt-realtime-whisper` and print the capabilities again. Read `_is_realtime_only` in `livekit/plugins/openai/stt.py` to see why the answer changes, and what that model would try to connect to.
:::

:::warn Whisper needs a VAD
A Whisper-style STT can't stream, so the session can't transcribe without a VAD to cut the clips. The docs say a session with a non-streaming STT and no VAD raises an error ([Gemini STT](https://docs.livekit.io/agents/models/stt/gemini)). Keep `vad=` on the session. The `min_silence_duration` you tune there also decides when each clip goes to the Whisper server.
:::

:::note What we did not test
`local_stack_agent.py` was never run against Ollama, a Whisper server or Kokoro. We only checked that it imports and builds its objects, and the capability flags above. We don't know whether Kokoro-FastAPI accepts the plugin's default `response_format`; the docs example sets `response_format="wav"` and voice `af_alloy`, while the lab file uses `af_heart` with no format. We ran no realtime model or avatar, and we have no latency or cost numbers for any of these.
:::

:::say
Self-hosted means plugins, not Inference strings: point the OpenAI plugin at local servers, run VAD and `v1-mini` in the agent process, and let VAD feed a non-streaming Whisper.
:::

:::check Why does `stt="deepgram/flux-general"` fail on a self-hosted setup while `deepgram.STT()` works?
The string is a LiveKit Inference model name, served through LiveKit Cloud. `deepgram.STT()` is a plugin that calls Deepgram directly with your own key.
:::

:::check Your local Whisper STT gives no interim transcripts. Is something broken?
No. A Whisper server transcribes finished clips, so `openai.STT` reports `streaming=False` and the session wraps it with VAD. You get one final transcript per utterance.
:::

Next: [Frontends and sessions](lesson:livekit/frontends-and-sessions)
