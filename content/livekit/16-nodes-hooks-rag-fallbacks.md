---
title: Nodes, hooks, RAG and fallbacks
summary: Where your own code can step into a voice turn. Lifecycle hooks, pipeline nodes, RAG before the reply, chat context operations, say and generate_reply, pronunciation, background audio, provider fallbacks, and how to prompt for speech.
time: 25 min
---

Your agent works, but it reads "SQL" letter by letter, makes up store hours that are in your FAQ, and goes silent for the whole call when the LLM provider has a bad minute. None of that is about tools. The fixes are small pieces of code at fixed points in each turn. LiveKit calls those points **hooks** (methods called at moments in an agent's life) and **nodes** (methods each stage of the pipeline runs through, which you can override) ([Pipeline nodes and hooks](https://docs.livekit.io/agents/logic/nodes)).

Versions: `livekit-agents` 1.8.11, Python, with the openai and silero plugins.

## One turn, and where your code goes

<figure>
<svg viewBox="0 0 820 300" role="img" aria-labelledby="t-nh d-nh">
  <title id="t-nh">Hooks and nodes in one user turn</title>
  <desc id="d-nh">User audio goes into stt_node. When the turn ends, on_user_turn_completed runs, then llm_node, then tts_node, which produces agent audio. The LLM text also passes through transcription_node to the frontend transcript. on_user_turn_exceeded fires if the user talks past a limit. on_enter runs when the agent becomes active and on_exit before it hands off. A realtime model replaces the middle with realtime_audio_output_node.</desc>
  <defs><marker id="ah-nh" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="10" y="110" width="100" height="50" rx="10"/><text x="60" y="140">User audio</text>
    <rect class="box" x="140" y="110" width="110" height="50" rx="10"/><text x="195" y="140">stt_node</text>
    <rect class="box hot" x="280" y="104" width="190" height="62" rx="10"/><text x="375" y="130">on_user_turn_</text><text x="375" y="150">completed</text>
    <rect class="box" x="500" y="110" width="100" height="50" rx="10"/><text x="550" y="140">llm_node</text>
    <rect class="box" x="630" y="110" width="80" height="50" rx="10"/><text x="670" y="140">tts_node</text>
    <rect class="box" x="736" y="110" width="76" height="50" rx="10"/><text x="774" y="140">Audio</text>
    <rect class="box" x="500" y="220" width="170" height="50" rx="10"/><text x="585" y="250">transcription_node</text>
    <rect class="box hot" x="110" y="20" width="200" height="44" rx="10"/><text x="210" y="47">on_user_turn_exceeded</text>
    <rect class="box hot" x="520" y="20" width="110" height="44" rx="10"/><text x="575" y="47">on_enter</text>
    <rect class="box hot" x="660" y="20" width="110" height="44" rx="10"/><text x="715" y="47">on_exit</text>
  </g>
  <path class="arrow" d="M110 135 H136" marker-end="url(#ah-nh)"/>
  <path class="arrow" d="M250 135 H276" marker-end="url(#ah-nh)"/>
  <path class="arrow" d="M470 135 H496" marker-end="url(#ah-nh)"/>
  <path class="arrow" d="M600 135 H626" marker-end="url(#ah-nh)"/>
  <path class="arrow" d="M710 135 H732" marker-end="url(#ah-nh)"/>
  <path class="arrow" d="M550 160 V216" marker-end="url(#ah-nh)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M195 110 V68" marker-end="url(#ah-nh)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="375" y="190">RAG goes here; raise StopResponse to skip</text>
    <text x="204" y="92" text-anchor="start">user talks too long</text>
    <text x="645" y="84">agent active / before handoff</text>
    <text x="740" y="250">to the transcript</text>
    <text x="260" y="250">realtime models: realtime_audio_output_node</text>
  </g>
</svg>
<figcaption>Hooks (highlighted) fire at moments. Nodes are stages the turn's data streams through. Override either in your Agent subclass, and call Agent.default.&lt;node&gt; to keep the built-in behavior.</figcaption>
</figure>

The four **lifecycle hooks**:

- `on_enter` runs when the agent becomes active. Greet here.
- `on_exit` runs before it hands off. Save state here.
- `on_user_turn_completed(turn_ctx, new_message)` runs after the user's turn ends and before the reply.
- `on_user_turn_exceeded(ev)` runs when the user passes a configured `max_words` or `max_duration`. By default it replies briefly, and that reply can't be interrupted.

The **pipeline nodes** are `stt_node`, `llm_node` and `tts_node`, plus `transcription_node` for the text sent to the frontend. Realtime models get `realtime_audio_output_node` instead. Each node is an async stream in and an async stream out. Override it and wrap `Agent.default.<node>(self, ...)` to keep the default ([nodes](https://docs.livekit.io/agents/logic/nodes)).

## RAG and outside data

There are two ways to bring in data. **Before the call**: the dispatcher puts it in **job metadata**, a string attached to the dispatch that the agent reads as `ctx.job.metadata` ([External data and RAG](https://docs.livekit.io/agents/logic/external-data)). The lab's echo agent does exactly this, in `code/livekit/echo_agent.py`:

```python
@server.rtc_session(agent_name="echo")    # a name turns OFF automatic dispatch to every room
async def entry(ctx: JobContext):
    delay = json.loads(ctx.job.metadata or "{}").get("delay_ms", 300) / 1000
```

Real output from `lk dispatch create --room echo-test --agent-name echo --metadata '{"delay_ms": 500}'` (`out/dispatch.txt`, trimmed):

```text
Dispatch created: id:"AD_4Eey2FYqpLC4"  agent_name:"echo"  room:"echo-test"  metadata:"{\"delay_ms\": 500}"  state:{created_at:1794130387324163671}
...
agent-AJ_poh7C3cMd4Lq (ACTIVE)	 tracks: 1
```

The echo came back after 0.63 s, which is the 500 ms from the metadata plus about 130 ms. For a real agent, put the caller's name and account in metadata, and add them to the initial `ChatContext` or the instructions. Don't fetch them after the agent has joined.

**During the call**: look things up in `on_user_turn_completed`. That saves the extra LLM round trip a search tool would cost. This sketch was checked to import and construct with 1.8.11, but it was not run against a model:

```python
class Support(Agent):
    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        facts = await lookup(new_message.text_content or "")   # your vector search
        if facts:                                    # this turn only; call update_chat_ctx to keep it
            turn_ctx.add_message(role="assistant", content=f"Relevant facts: {facts}")

    async def tts_node(self, text: AsyncIterable[str], model_settings: ModelSettings):
        async def fix(chunks):
            async for c in chunks:
                yield c.replace("LiveKit", "Live Kit")
        return Agent.default.tts_node(self, fix(text), model_settings)
```

Messages added to `turn_ctx` last for this turn only. To keep them, call `await self.update_chat_ctx(turn_ctx)`. Raise `StopResponse` (from `livekit.agents`) to skip the reply entirely.

## Chat context, in four operations

`ChatContext` is the list of items sent to the LLM: messages, `function_call`, `function_call_output`, `agent_handoff` and `agent_config_update` ([Chat context](https://docs.livekit.io/agents/logic/chat-context)). Each agent and task has its own `agent.chat_ctx`. `session.history` holds the whole conversation across all agents, so use it for logs and transcripts.

- `copy(exclude_instructions=True, exclude_function_call=True, ...)` makes a filtered snapshot, usually to pass at a handoff.
- `truncate(max_items=6)` keeps the last items. It keeps the system instructions and drops function-call items that would be left without their call.
- `merge(other)` combines contexts, deduplicating by item id.
- `await agent.update_chat_ctx(ctx)` replaces the agent's context.

## Making it speak

`session.say(text)` speaks fixed text through the TTS. It can also play `audio=` you synthesized earlier. `session.generate_reply(instructions=...)` asks the LLM. Those instructions are *added* to the agent's own; they don't replace them. Both return a **`SpeechHandle`** (import it from `livekit.agents.voice`). `await handle` waits until playout finishes, which you need before hanging up ([Agent speech](https://docs.livekit.io/agents/multimodality/audio)).

Text heading to TTS goes through `tts_text_transforms`. When you don't set it, the installed source applies all the built-in filters (`"filter_markdown"`, `"filter_emoji"`). Add `text_transforms.replace({"SQL": "sequel"})` for pronunciation. Use a custom `tts_node` for anything a plain replace can't do ([Audio customization](https://docs.livekit.io/agents/multimodality/audio/customization)). `BackgroundAudioPlayer` puts ambient sound and "thinking" sounds (such as `BuiltinAudioClip.KEYBOARD_TYPING`) on a separate track. Start it with `await player.start(room=ctx.room, agent_session=session)` after the session starts ([Background audio](https://docs.livekit.io/agents/multimodality/audio/background-audio)).

The prompting guide recommends instructions in Markdown sections: identity, output rules, tools, goals, guardrails and user information ([Prompting guide](https://docs.livekit.io/agents/start/prompting)). Its output rules for voice:

```markdown
- Respond in plain text only. Never use JSON, markdown, lists, tables, code, emojis, or other complex formatting.
- Keep replies brief by default: one to three sentences. Ask one question at a time.
- Spell out numbers, phone numbers, or email addresses.
- Omit `https://` and other formatting if listing a web URL.
```

## Fallbacks

`stt.FallbackAdapter`, `llm.FallbackAdapter` and `tts.FallbackAdapter` take a list of providers. They try them in order, mark a failed one unhealthy, probe it in the background, and switch back when it recovers ([Fallback strategies](https://docs.livekit.io/agents/logic/fallback-strategies)). Defaults from the installed source:

| Adapter | Defaults |
|---|---|
| `llm.FallbackAdapter` | `attempt_timeout=5.0`, `max_retry_per_llm=0`, `retry_on_chunk_sent=False`, `sticky=False` |
| `stt.FallbackAdapter` | `attempt_timeout=10.0`, `max_retry_per_stt=1`, `retry_interval=5` |
| `tts.FallbackAdapter` | `max_retry_per_tts=2` |

The adapters guard partial output. Once TTS audio has started playing, the TTS adapter won't switch mid-sentence. Once LLM text has streamed, the LLM adapter raises the error instead of restarting, unless you set `retry_on_chunk_sent=True`. With `sticky=True` the LLM adapter stays on the backup after the primary recovers. Each adapter emits `llm_availability_changed` (and the STT and TTS versions) so you can log the switch.

:::note Self-hosted vs Cloud
Hooks, nodes, chat context, `say`, text transforms, background audio and the three `FallbackAdapter` classes all run in your agent process, so they work self-hosted with your own plugin keys or local models. The **Inference fallback** (the `fallback=[...]` argument on `inference.STT` and `inference.TTS`) runs inside LiveKit Inference, so it is Cloud-only. Docs examples that build a fast filler model with `inference.LLM(...)` are Cloud-only too; use a small plugin model instead. "Expressive mode", mentioned in the prompting guide, is a LiveKit Inference feature.
:::

:::tip CLI
- `lk dispatch create --room echo-test --agent-name echo --metadata '{"delay_ms": 500}'` (job metadata, as in the lab)
- `lk agent console --text` (try prompt and RAG changes without audio)
- `lk agent debugger say --logs "What are your hours?"` (the turn's log lines under each step)
- `lk agent debugger chat-history` (what actually ended up in the context)
:::

:::try
Run `echo_agent.py start` and dispatch it twice, with `{"delay_ms": 200}` and `{"delay_ms": 1500}`. Then run `echo_check.py` for each. Does the echo delay follow the metadata? Then send `--metadata 'not json'` and predict what `json.loads` does to the job before you look at the agent log.
:::

:::warn RAG messages vanish after one turn
A message added to `turn_ctx` in `on_user_turn_completed` is gone on the next turn, so a follow-up question ("and on Sundays?") loses the facts. Call `update_chat_ctx` if you want them to stay, and then watch the context grow. Long contexts slow every later turn.
:::

:::note What we did not test
We ran the echo agent's metadata path (`out/dispatch.txt`, `out/echo_check.txt`). The RAG and `tts_node` snippet and a `FallbackAdapter` over two OpenAI-compatible endpoints were only constructed, never run against a model. We didn't test background audio, `on_user_turn_exceeded`, `say` with pre-synthesized audio, or a real provider failure. The adapter defaults come from the 1.8.11 source; the switching behavior comes from the docs.
:::

:::say
Hooks fire at moments in a turn and nodes are the streams the turn passes through. Put RAG in `on_user_turn_completed`, pronunciation in text transforms or `tts_node`, and outages in a `FallbackAdapter`.
:::

:::check You inject RAG facts in `on_user_turn_completed`, and the agent uses them once and then forgets. Why?
Messages added to `turn_ctx` last for that turn only. Call `await self.update_chat_ctx(turn_ctx)` to keep them in the agent's context.
:::

:::check You copy a docs example that uses `fallback=[...]` on `inference.TTS` into a self-hosted agent. Why won't that work, and what do you use instead?
That fallback runs inside LiveKit Inference, which is Cloud-only. Use `tts.FallbackAdapter([primary_plugin, backup_plugin])`, which runs in your agent process.
:::
