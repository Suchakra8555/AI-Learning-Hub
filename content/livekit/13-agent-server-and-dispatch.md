---
title: Agent server and dispatch
summary: How an agent gets into a room. The 1.8 AgentServer API and its 1.6 names, the four startup modes, registration and load reporting, explicit and token dispatch on the lab with real timings, JobContext, and the server options with their real defaults.
time: 25 min
---

The agent runs. The log says it started. But nobody hears it, because it never joined the room. Or it joins every room, including the ones meant for a human. Or two copies join the same call. All three are dispatch problems, and dispatch is mostly config you never looked at. This lesson walks one agent from `start` to "joined", on the lab, with timings. Versions: `livekit-agents` 1.8.11, livekit-server v1.13.11, `lk` v2.19.3.

## The 1.8 API in 20 lines

`code/livekit/echo_agent.py` is the smallest real agent. It has no models. It plays back what it hears after a delay taken from the job's metadata:

```python
server = AgentServer()                    # reads LIVEKIT_URL / _API_KEY / _API_SECRET
def setup(proc: JobProcess):              # runs once per process, before any job: load models here
    proc.userdata["started"] = True
server.setup_fnc = setup
@server.rtc_session(agent_name="echo")    # a name turns OFF automatic dispatch to every room
async def entry(ctx: JobContext):
    delay = json.loads(ctx.job.metadata or "{}").get("delay_ms", 300) / 1000
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    out = rtc.AudioSource(48000, 1)
    await ctx.room.local_participant.publish_track(rtc.LocalAudioTrack.create_audio_track("echo", out))
    ...
    async def on_shutdown():               # must be async: the job awaits it
        log.info("job for %s is ending", ctx.room.name)

    ctx.add_shutdown_callback(on_shutdown)
if __name__ == "__main__":
    cli.run_app(server)
```

The **entrypoint** is the function under `@server.rtc_session`. It runs once per job, inside the job's own process ([Job lifecycle](https://docs.livekit.io/agents/server/job)). If your project pinned 1.6.x, you wrote the same thing with `WorkerOptions`. In 1.8.11 `WorkerOptions` is a plain alias of `ServerOptions`, and `AgentServer.from_server_options()` maps the old fields onto the new API. The docs no longer show it. The mapping, from that function's source (log messages still say "worker"):

| 1.6 (`WorkerOptions`) | 1.8 (`AgentServer`) |
| --- | --- |
| `entrypoint_fnc=entry` | `@server.rtc_session()` on `entry` |
| `prewarm_fnc=prewarm` | `server.setup_fnc = prewarm` |
| `agent_name="echo"` | `@server.rtc_session(agent_name="echo")` |
| `request_fnc=...` | `@server.rtc_session(on_request=...)` |
| `worker_type=WorkerType.ROOM` | `@server.rtc_session(type=...)` (`WorkerType` is now an alias of `ServerType`) |
| `load_threshold`, `num_idle_processes`, ... | the same names as `AgentServer(...)` keyword arguments |
| `cli.run_app(WorkerOptions(...))` | `cli.run_app(server)` (still accepts `WorkerOptions`) |

## Four startup modes

`cli.run_app` gives the script four subcommands ([Startup modes](https://docs.livekit.io/agents/server/startup-modes)):

| Mode | What it does | Useful flags |
| --- | --- | --- |
| `start` | Production: `info` logs as JSON, drains jobs on `SIGTERM`/`SIGINT`, prewarms idle processes, load threshold on. | `--log-level` |
| `dev` | Development: `debug` logs, auto-reload, no drain, no idle processes, no load limit. | `--log-level`, `--no-reload` |
| `console` | One session in your terminal, no LiveKit server needed. | `--text`, `--list-devices`, `--input-device`, `--output-device`, `--record` |
| `connect` | One session joined straight to a named room. | `--room` (required), `--participant-identity` |

`lk agent dev`, `lk agent start` and `lk agent console` wrap the same modes. The 1.8.11 source marks the `python agent.py <mode>` CLI as deprecated in favor of `lk agent ...`. It still works, and the lab uses it.

## What the server does before any call

On `start`, the server opens one **outbound** WebSocket to the LiveKit server and registers. It needs no inbound port for jobs. The only port it listens on is the health check ([Server lifecycle](https://docs.livekit.io/agents/server/lifecycle)). On the lab, `python echo_agent.py start` started 12 idle processes, one per CPU core on that machine, then logged (trimmed to the useful fields):

```text
{"message": "registered worker", "level": "INFO", "name": "livekit.agents", "agent_name": "echo", "deployment": "", "id": "AW_RA6kQ49cffM8", "url": "ws://127.0.0.1:7880", "region": "", "protocol": 18, ...}
```

From then on the server reports its **load**, a number from 0 to 1. The default is average CPU over 5 seconds. Above `load_threshold` it marks itself unavailable and gets no new jobs ([Server options](https://docs.livekit.io/agents/server/options)). While the lab's load test ran on the same machine, the same log printed `worker is at full capacity, marking as unavailable` at load 0.7025 against a threshold of 0.7, and `marking as available` 1.5 s later at 0.682.

On `SIGTERM` the server enters **draining**: it takes no new jobs and waits for running ones, up to `drain_timeout` (default 3600 s). If a job process dies mid-call, the docs say LiveKit notices within about 15 seconds and dispatches a new agent to the room.

## Dispatch: getting a job into a room

**Dispatch** is LiveKit assigning an agent to a room ([Agent dispatch](https://docs.livekit.io/agents/server/agent-dispatch)). There are two kinds:

- **Automatic**: no `agent_name`. Every new room gets the agent. The docs advise against it beyond prototypes.
- **Explicit**: an `agent_name`, and the agent joins only when asked. You ask in one of four ways: the `AgentDispatchService` API, `lk dispatch create`, a `RoomConfiguration` inside the user's token, or `room_config.agents` on a SIP dispatch rule. Each dispatch can carry **job metadata**, a free-form string up to 512 KiB that the entrypoint reads as `ctx.job.metadata`.

<figure>
<svg viewBox="0 0 780 440" role="img" aria-labelledby="t-disp d-disp">
  <title id="t-disp">The dispatch lifecycle</title>
  <desc id="d-disp">Four lifelines: your app, LiveKit server, AgentServer and job process. The AgentServer registers. Your app creates a dispatch. LiveKit sends a job request to a server under its load threshold. The server hands the job to an idle process. The job process joins the room over WebRTC and runs the entrypoint and session. When the room closes or the job shuts down, shutdown callbacks run and the process exits.</desc>
  <defs><marker id="ah-disp" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="15" y="16" width="150" height="40" rx="10"/><text x="90" y="41">Your app</text><rect class="box hot" x="215" y="16" width="150" height="40" rx="10"/><text x="290" y="41">LiveKit server</text>
    <rect class="box" x="415" y="16" width="150" height="40" rx="10"/><text x="490" y="41">AgentServer</text><rect class="box" x="615" y="16" width="150" height="40" rx="10"/><text x="690" y="41">Job process</text>
  </g>
  <g class="arrow" stroke-dasharray="3 5"><path d="M90 56 V428"/><path d="M290 56 V428"/><path d="M490 56 V428"/><path d="M690 56 V428"/></g>
  <g font-size="12" class="small" text-anchor="middle">
    <path class="arrow" d="M490 92 H294" marker-end="url(#ah-disp)"/><text x="390" y="86">register: agent_name=echo</text>
    <path class="arrow" d="M290 122 H486" marker-end="url(#ah-disp)"/><text x="390" y="116">registered, id AW_…</text>
    <path class="arrow" d="M90 168 H286" marker-end="url(#ah-disp)"/><text x="190" y="162">create dispatch + metadata</text>
    <text x="290" y="194">room created if missing</text>
    <path class="arrow" d="M290 226 H486" marker-end="url(#ah-disp)"/><text x="390" y="220">job request (load &lt; 0.7)</text>
    <path class="arrow" d="M490 262 H686" marker-end="url(#ah-disp)"/><text x="590" y="256">hand job to idle process</text>
    <path class="arrow" d="M690 298 H294" marker-end="url(#ah-disp)"/><text x="490" y="292">ctx.connect(): joins as agent-AJ_…, over WebRTC</text>
  </g>
  <rect class="box hot" x="605" y="314" width="170" height="36" rx="8"/><text x="690" y="337" font-size="13" text-anchor="middle">entrypoint + session</text>
  <g font-size="12" class="small" text-anchor="middle">
    <path class="arrow" d="M290 380 H686" marker-end="url(#ah-disp)"/><text x="490" y="374">room closes, or shutdown requested</text>
    <path class="arrow" d="M690 414 H494" marker-end="url(#ah-disp)"/><text x="590" y="408">callbacks run, exit</text>
  </g>
</svg>
<figcaption>Registration happens once. Every call then repeats the rest. If the job process dies, LiveKit notices within about 15 seconds and dispatches again.</figcaption>
</figure>

On the lab, with the echo server running, we ran three commands:

```bash
lk dispatch create --room echo-test --agent-name echo --metadata '{"delay_ms": 500}'
lk room participants list echo-test
lk dispatch list echo-test
```

```text
Using url, api-key, api-secret from environment
Dispatch created: id:"AD_4Eey2FYqpLC4"  agent_name:"echo"  room:"echo-test"  metadata:"{\"delay_ms\": 500}"  state:{created_at:1794130387324163671}
Using url, api-key, api-secret from environment
agent-AJ_poh7C3cMd4Lq (ACTIVE)	 tracks: 1
Using url, api-key, api-secret from environment
┌─────────────────┬───────────┬───────────┬────────────┬───────────────────┐
│ DispatchID      │ Room      │ AgentName │ Deployment │ Metadata          │
├─────────────────┼───────────┼───────────┼────────────┼───────────────────┤
│ AD_4tjQ6aDcRtzm │ echo-test │           │            │                   │
│ AD_4Eey2FYqpLC4 │ echo-test │ echo      │            │ {"delay_ms": 500} │
└─────────────────┴───────────┴───────────┴────────────┴───────────────────┘
```

The first row is a dispatch with no agent name, which the server created for the room on its own. We saw it but did not find out why it exists.

`created_at` is 09:33:07.324 UTC. The agent server logged "received job request" at 07.526 and "joined echo-test" at 07.633. So about 200 ms from dispatch to job request, and about 310 ms until the agent was in the room. The docs claim a maximum dispatch time under 150 ms. Our lab ran everything on one machine with 12 idle processes, so treat 200 ms as one sample, not a benchmark. Then `code/livekit/echo_check.py` joined and timed the echo:

```text
in the room: agent-AJ_poh7C3cMd4Lq kind=PARTICIPANT_KIND_AGENT
subscribed to agent-AJ_poh7C3cMd4Lq's track
heard my own tone back after 0.63 s
```

That's the 500 ms from the metadata plus about 130 ms for everything else: two network hops, Opus encoding and decoding, and the check script's own startup.

### Dispatch from a token

A browser user usually creates the room by joining it. Then the token can request the agent. `code/livekit/token_endpoint.py`:

```python
jwt = (api.AccessToken()
       .with_identity(identity)
       .with_name(req.get("participant_name", identity))
       .with_ttl(__import__("datetime").timedelta(minutes=15))   # short: self-hosted has no revocation
       .with_grants(api.VideoGrants(room_join=True, room=room, can_publish=True, can_subscribe=True))
       .with_room_config(api.RoomConfiguration(agents=[api.RoomAgentDispatch(agent_name="echo")]))
       .to_jwt())
```

Real output, claims trimmed:

```text
...
 "roomConfig": {
  "agents": [
...
joined web-1 as u1 | others: [('agent-AJ_ymXHYAYbbQDP', 'PARTICIPANT_KIND_AGENT')]
```

The docs say the token's dispatch applies **only when the room is created** by that join. If the room already exists, it is ignored. The same echo server also took jobs for rooms named `call-_+15550001111_…`, sent by the SIP dispatch rule in the telephony lab.

## JobContext: what the entrypoint gets

| Member | Use |
| --- | --- |
| `ctx.connect(auto_subscribe=...)` | Join the room. `AgentSession.start()` does it for you; call it yourself when there is no session. |
| `ctx.wait_for_participant(identity=..., kind=...)` | Wait for a specific participant, for example the SIP callee on an outbound call. |
| `ctx.proc.userdata` | A dict filled by `setup_fnc` once per process, such as a loaded VAD. |
| `ctx.add_shutdown_callback(fn)` | Cleanup after the job ends. Must be an `async` function. |
| `ctx.delete_room()` | End the room for everyone. |
| `ctx.shutdown(reason)` | End this job. |

## Server options and their real defaults

From the `AgentServer.__init__` signature in 1.8.11:

| Option | Default | Notes |
| --- | --- | --- |
| `load_threshold` | dev: `inf`, prod: `0.7` | Above it, no new jobs. Not changeable on LiveKit Cloud. |
| `num_idle_processes` | dev: `0`, prod: `ceil(cpu_count)` | 12 on the lab. Reads cgroup limits in containers. |
| `setup_fnc` | none | Replaces `prewarm_fnc`. Bounded by `initialize_process_timeout` (10.0 s). |
| `drain_timeout` | `3600` s | How long `SIGTERM` waits for live jobs. |
| `shutdown_process_timeout` | `10.0` s | Time for shutdown callbacks before the process is killed. |
| `session_end_timeout` | `300.0` s | Time allowed for `on_session_end`. |
| `job_memory_warn_mb` / `job_memory_limit_mb` | `1000` / `0` (off) | Warn, or kill, a job above this size. |
| `port` / `host` | dev: `0` (random), prod: `8081` / all interfaces | Health check: `200` when connected, `503` when not. |
| `multiprocessing_context` | `"forkserver"` on Linux, else `"spawn"` | How job processes are created. |

The lab log showed `HTTP server listening on :8081`. Point your container's liveness probe at `/` on that port. Also there: `max_retry` (16 reconnects) and `permissions`.

:::note Self-hosted vs Cloud
`lk agent create`, `lk agent deploy` and the rest of managed hosting are Cloud-only. Self-hosted, you run agent servers yourself in Docker or Kubernetes, and `lk agent start` isn't in the image. The container can run `python agent.py start`, or the non-deprecated `python -m livekit.agents start agent.py` that ships in livekit-agents 1.8.11 (we checked its `--help`, not a full run). Cloud sets `LIVEKIT_AGENT_DEPLOYMENT` to route dispatches to a deployment. Self-hosted, you get the same effect with distinct agent names per environment.
:::

:::tip CLI
`lk dispatch create --agent-name NAME --room NAME --metadata '{...}'`, `lk dispatch list ROOM_NAME`, `lk dispatch get ROOM_NAME DISPATCH_ID`, `lk dispatch delete ROOM_NAME DISPATCH_ID` ([CLI reference](https://docs.livekit.io/reference/developer-tools/livekit-cli/rooms)). `lk token create --identity ID --room NAME --agent AGENT --join` puts a dispatch in a token. `lk agent dev`, `lk agent start` and `lk agent console` run the server.
:::

:::try
Run the echo server with `start`, then dispatch it twice into the same room with different `delay_ms` values. How many agents join, and do they hear each other? Then stop the server with Ctrl+C while a job runs and read what the log says about draining.
:::

:::warn Shutdown callbacks must be coroutines
The first version of `echo_agent.py` passed a plain `lambda` to `add_shutdown_callback`. The lambda ran (the log showed "job for echo-test is ending"), and then the framework tried to `await` its `None` return. Every job exit on the lab logged `error while shutting down the job` with `TypeError: object NoneType can't be used in 'await' expression`. The script now uses `async def on_shutdown()`, and a rerun logged no shutdown errors. A cleanup that saves the call record would fail in the same place.
:::

:::note What we did not test
We ran one agent server, so we never saw a job rejected and passed to another server, or a crash and redispatch. We did not time `SIGTERM` draining. The 150 ms dispatch figure is from the docs. We don't know why the empty-name dispatch appeared.
:::

:::say
The agent server registers out to LiveKit and waits. A dispatch with its agent name hands a job to an idle process, and only then does the entrypoint run.
:::

:::check A user rejoins an existing room with a fresh token that names the agent, but the agent doesn't come back. Why?
Token dispatch applies only when that join creates the room. The room still existed, so the token's dispatch was ignored. Create an explicit dispatch with the API instead.
:::
