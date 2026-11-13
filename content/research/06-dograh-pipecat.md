---
title: Dograh and Pipecat, source notes
summary: Which repositories, commits and files back each claim in the Pipecat and Dograh track, what we ran, and what we could not settle.
time: 12 min
---

Research date: 12 to 13 November 2026. The [track](lesson:pipecat/what-pipecat-is) was written from these sources.

## Sources

| What | Where | Version read |
|---|---|---|
| Dograh | https://github.com/dograh-hq/dograh | commit `5dfa84c18` (12 November 2026), version 1.51.0, shallow clone |
| Dograh's Pipecat fork | https://github.com/dograh-hq/pipecat | commit `9ac08e90be4bb83e506f3d10deaa8e6d31588547`, the commit Dograh's `.gitmodules` pins |
| Upstream Pipecat | https://github.com/pipecat-ai/pipecat | tag `v1.15.0` (the base the fork has merged), `v1.16.0` (11 November 2026) seen as a tag, plus the installed package `pipecat-ai` 1.16.0 |

Both Dograh repositories and Pipecat are BSD 2-Clause licensed (Dograh's `LICENSE`, Pipecat's `pyproject.toml`).

## What we ran

Nothing in Dograh. In a fresh virtual environment with `pipecat-ai==1.16.0` we ran the three scripts in `code/pipecat/` (`frames_hello.py`, `interruption_demo.py`, `frames_to_events.py`) and the standard-library `mini_workflow.py`. We also printed `VADParams()` defaults and counted frame classes by introspection (147 in 1.16.0: 60 system, 38 data, 45 control, 4 direct subclasses). The output pasted in lessons is real output from those runs.

## What we read, by lesson

| Lesson | Main files |
|---|---|
| 2, 3 | `src/pipecat/frames/frames.py`, `processors/frame_processor.py`, `utils/frame_queue.py`, `transports/base_output.py` |
| 4 | `audio/vad/vad_analyzer.py`, `audio/vad/silero.py`, `turns/user_turn_strategies.py`, `turns/user_start/`, `turns/user_stop/`, `turns/user_mute/`, `processors/aggregators/llm_response_universal.py` |
| 5 | `services/ai_service.py`, `stt_service.py`, `tts_service.py`, `llm_service.py`, `examples/getting-started/07-function-calling.py` |
| 6 | `transports/*`, `serializers/*`, `transports/base_transport.py` |
| 7 | `observers/*`, `metrics/metrics.py`, `utils/tracing/*`, `processors/frameworks/rtvi/*` |
| 9, 10, 11 | `api/app.py`, `scripts/start_services_docker.sh`, `docker-compose.yaml`, `api/routes/webrtc_signaling.py`, `api/routes/telephony.py`, `api/services/pipecat/run_pipeline.py`, `pipeline_builder.py`, `service_factory.py`, `api/services/workflow/dto.py`, `workflow_graph.py`, `pipecat_engine.py`, `pipecat_engine_context_composer.py` |
| 12, 13 | `ui/src/app/workflow/[workflowId]/RenderWorkflow.tsx`, `stores/workflowStore.ts`, `hooks/useWorkflowState.ts`, `ui/src/components/flow/*`, `api/services/workflow/node_specs/_base.py`, `layout.py`, `realtime_feedback_observer.py`, `useWebSocketRTC.tsx` |
| 14 | `api/services/telephony/base.py`, `registry.py`, `providers/AGENTS.md`, `services/campaign/*` |
| 15, 16 | `git diff v1.15.0 HEAD` in the fork, `git log`, `changelog/*.md`, `.agents/skills/merge-pipecat-upstream/SKILL.md` |
| 18 | `CONTRIBUTING.md`, `docs/contribution/*.mdx`, `.github/workflows/*`, `scripts/*` |

## What we did not settle

- We did not run Dograh, make a call through it, or measure latency or concurrency.
- Dograh's hosted gateway (`services.dograh.com`) is visible only as client code.
- We did not read: the ARI manager internals, the campaign dispatcher's rate limiting, the call-events pipeline under `api/observability/call_events/`, the QA analysis flow, the MiniMax and HuggingFace service bodies, most test file bodies, and the Twilio serializer's audio handling.
- We did not confirm where per-turn latency is stored beyond the run's log buffer.
- Where a lesson says "we infer", the reason for a change is our reading of commit messages and comments, not a statement from the authors.
- The LiveKit column of the translation table in [lesson 8](lesson:pipecat/from-livekit-to-pipecat) is from general knowledge and was not re-checked.
- Our judgement of which fork changes suit upstream is ours, not a maintainer's.
- Contribution ideas in [lesson 18](lesson:pipecat/contribute-to-dograh) are inferences from the code. Check that each is still open.

## One thing that surprised us

The fork's `git merge-base` with upstream is v1.12.0, but its content is v1.15.0, because two syncs were single-parent squash pull requests. A naive diff overstates the fork by about a factor of eight (1,299 files against 167). [Lesson 15](lesson:pipecat/what-dograh-changed) explains it.
