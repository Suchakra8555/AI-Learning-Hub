"""Turn handling for a fully self-hosted agent, and how the old flat settings map to it.

Run:  python turn_config.py      (no server needed)

livekit-agents 1.8 groups every turn setting under TurnHandlingOptions. Some
defaults call LiveKit Cloud (the v1 turn detector, adaptive interruption).
A self-hosted agent pins the local choices explicitly.
"""
import json
import warnings

from livekit.agents import TurnHandlingOptions, inference
from livekit.agents.voice import turn
from livekit.plugins import silero

warnings.filterwarnings("ignore")

SELF_HOSTED: TurnHandlingOptions = {
    "turn_detection": inference.TurnDetector(version="v1-mini"),   # runs on local CPU; "v1" runs on LiveKit Inference
    "endpointing": {"mode": "fixed", "min_delay": 0.3, "max_delay": 2.5},
    "interruption": {"mode": "vad", "min_duration": 0.5, "false_interruption_timeout": 2.0},  # "adaptive" needs Cloud keys
    "preemptive_generation": {"enabled": True, "preemptive_tts": False},
}

if __name__ == "__main__":
    vad = silero.VAD.load()          # local ONNX model, about 2 MB
    print("Silero VAD options:", {k: v for k, v in vars(vad._opts).items()})
    print("\nbuilt-in defaults (no turn detector):")
    print("  endpointing :", turn._ENDPOINTING_DEFAULTS)
    print("  interruption:", turn._INTERRUPTION_DEFAULTS)
    print("\nself-hosted turn handling:")
    for k, v in SELF_HOSTED.items():
        print(f"  {k:22} {v if isinstance(v, dict) else type(v).__name__ + '(version=v1-mini)'}")

    # The 1.6-era flat keyword arguments still work in 1.8 but are deprecated.
    # This is the mapping the library applies (from livekit/agents/voice/turn.py):
    old = dict(min_endpointing_delay=0.4, max_endpointing_delay=3.0, allow_interruptions=True,
               min_interruption_duration=0.6, min_interruption_words=2, false_interruption_timeout=1.5,
               resume_false_interruption=True, preemptive_generation=True)
    print("\nold flat kwargs :", json.dumps(old))
    print("new nested form :", json.dumps(turn._migrate_turn_handling(**old)))
