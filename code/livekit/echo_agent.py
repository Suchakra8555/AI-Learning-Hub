"""The smallest real LiveKit agent: no STT, no LLM, no TTS. It repeats what it hears.

Run the agent server (registers with the lab and waits for jobs):
    source lab.env && python echo_agent.py start
Then dispatch it into a room, from another terminal:
    lk dispatch create --room echo-test --agent-name echo --metadata '{"delay_ms": 500}'

This is a "programmatic participant": a job without an AgentSession. It shows the
agent server, dispatch and the job lifecycle with nothing else in the way.
"""
import asyncio
import json
import logging

from livekit import rtc
from livekit.agents import AgentServer, AutoSubscribe, JobContext, JobProcess, cli

log = logging.getLogger("echo")
server = AgentServer()                    # reads LIVEKIT_URL / _API_KEY / _API_SECRET


def setup(proc: JobProcess):              # runs once per process, before any job: load models here
    proc.userdata["started"] = True


server.setup_fnc = setup


@server.rtc_session(agent_name="echo")    # a name turns OFF automatic dispatch to every room
async def entry(ctx: JobContext):
    delay = json.loads(ctx.job.metadata or "{}").get("delay_ms", 300) / 1000
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    log.info("joined %s as %s, echo delay %.1fs", ctx.room.name, ctx.room.local_participant.identity, delay)

    out = rtc.AudioSource(48000, 1)
    await ctx.room.local_participant.publish_track(rtc.LocalAudioTrack.create_audio_track("echo", out))

    async def echo(track: rtc.Track):
        buf = []
        async for ev in rtc.AudioStream(track, sample_rate=48000, num_channels=1):
            buf.append(ev.frame)
            if len(buf) * 0.01 >= delay:   # 10 ms frames
                await out.capture_frame(buf.pop(0))

    ctx.room.on("track_subscribed", lambda t, pub, p: t.kind == rtc.TrackKind.KIND_AUDIO and asyncio.create_task(echo(t)))
    async def on_shutdown():               # must be async: the job awaits it
        log.info("job for %s is ending", ctx.room.name)

    ctx.add_shutdown_callback(on_shutdown)


if __name__ == "__main__":
    cli.run_app(server)
