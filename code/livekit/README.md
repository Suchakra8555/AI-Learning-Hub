# LiveKit lab

Code for the [LiveKit, self-hosted](../../content/livekit/) track. Every script here was run against this lab. Lessons paste the real output.

## Start the lab (Linux, Docker)

```bash
cd code/livekit/lab
docker compose up -d                       # redis + livekit-server v1.13.11 on 127.0.0.1:7880
docker compose --profile egress up -d      # + recording   (lesson: egress-recording)
docker compose --profile ingress up -d     # + RTMP/WHIP   (lesson: ingress)
docker compose --profile sip up -d         # + SIP on 5060 (lesson: self-hosted-sip). Firewall it.
curl localhost:7880                        # prints OK
```

The containers use host networking, because WebRTC needs real UDP ports. That works on Linux. On macOS, run `livekit-server --dev` natively instead (see lesson 04).

## Python and the CLI

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# lk CLI v2.19.3: brew install livekit-cli, or curl -sSL https://get.livekit.io/cli | bash
source lab.env                             # LIVEKIT_URL / _API_KEY / _API_SECRET for the lab
```

## Scripts, in lesson order

| Script | Lesson | Needs |
|---|---|---|
| `sdp_peek.py`, `jitter_buffer.py`, `sfu_math.py` | webrtc-from-the-wire-up, mesh-mcu-sfu | nothing (stdlib) |
| `cli_tour.sh` | the-lk-cli | lab, `lk` |
| `two_participants.py`, `tokens.py`, `room_admin.py` | rooms, tokens, server API | lab |
| `webhook_receiver.py` | webhooks-and-events | lab (webhook URL is in `lab/livekit.yaml`) |
| `audio_pubsub.py`, `data_rpc.py` | media-in-depth, data-and-state | lab |
| `echo_agent.py`, `echo_check.py` | agent-server-and-dispatch | lab; run `python echo_agent.py start`, then `lk dispatch create --room echo-test --agent-name echo` |
| `turn_config.py` | turns-and-interruptions | nothing |
| `local_stack_agent.py` | models-without-the-cloud | Ollama, a Whisper server, Kokoro. **Not run by us.** |
| `token_endpoint.py` | frontends-and-sessions | lab, echo agent |
| `test_agent.py`, `scripted_llm.py` | testing-and-observability | nothing: `pytest -q test_agent.py` |
| `sip_setup.sh`, `sip_call.py`, `sip_outbound.py` | sip-fundamentals, self-hosted-sip | lab + sip profile + echo agent |
| `record_room.sh` | egress-recording | lab + egress profile, ffmpeg |
| `ingress/rtmp-ingress.json` | ingress | lab + ingress profile, ffmpeg |
| `load_test.sh` | scaling-and-load | lab |

The API key and secret in `lab/` are for this lab only. Never reuse them on a server that faces the internet.
