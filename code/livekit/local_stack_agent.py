"""A voice agent with no cloud services at all: every model runs on your machines.

Needs, all local:
  Ollama          ollama serve && ollama pull llama3.1                 (LLM, OpenAI-compatible API on :11434)
  Speaches        an OpenAI-compatible Whisper server on :8000          (STT)  # shortcut: any OpenAI-compatible STT works
  Kokoro-FastAPI  docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu   (TTS)
Run:  source lab.env && python local_stack_agent.py start
Then: lk dispatch create --room local-1 --agent-name local

Silero VAD and the v1-mini turn detector run inside this process on CPU.
"""
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, JobProcess, cli, inference
from livekit.plugins import openai, silero

server = AgentServer()


def setup(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()        # load once per process, not per call


server.setup_fnc = setup


@server.rtc_session(agent_name="local")
async def entry(ctx: JobContext):
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
    await session.start(Agent(instructions="You are a helpful voice assistant. Answer in one or two short sentences, plain text only."),
                        room=ctx.room)
    await session.say("Hi, I am running entirely on local models. What can I do for you?")


if __name__ == "__main__":
    cli.run_app(server)
