"""The Dograh live-feed pattern, rebuilt small: an observer that turns Pipecat frames
into JSON events a browser could draw. Dograh's real one is RealtimeFeedbackObserver
(api/services/pipecat/realtime_feedback_observer.py). This is our sketch, not their code.

Run: python frames_to_events.py
"""
import asyncio
import json
import warnings

from loguru import logger

from pipecat.frames.frames import (
    BotStartedSpeakingFrame, BotStoppedSpeakingFrame, EndFrame, TranscriptionFrame,
    TTSTextFrame,
)
from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.frame_processor import FrameProcessor

warnings.filterwarnings("ignore")
logger.remove()

EVENTS = []  # a real system sends these over a WebSocket and stores them


class FeedObserver(BaseObserver):
    def __init__(self):
        super().__init__()
        self._seen = set()  # every hop re-reports the same frame; count each frame once

    async def on_push_frame(self, data: FramePushed):
        f = data.frame
        if f.id in self._seen:
            return
        self._seen.add(f.id)
        if isinstance(f, TranscriptionFrame):
            EVENTS.append({"type": "rtf-user-transcription", "payload": {"text": f.text}})
        elif isinstance(f, TTSTextFrame):
            EVENTS.append({"type": "rtf-bot-text", "payload": {"text": f.text}})
        elif isinstance(f, BotStartedSpeakingFrame):
            EVENTS.append({"type": "rtf-bot-started-speaking", "payload": {}})
        elif isinstance(f, BotStoppedSpeakingFrame):
            EVENTS.append({"type": "rtf-bot-stopped-speaking", "payload": {}})


class Passthrough(FrameProcessor):
    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)


async def main():
    task = PipelineTask(Pipeline([Passthrough()]), observers=[FeedObserver()])
    await task.queue_frames([
        TranscriptionFrame(text="I want to book a table", user_id="caller", timestamp="t0"),
        BotStartedSpeakingFrame(),
        TTSTextFrame(text="Sure.", aggregated_by="sentence"),
        TTSTextFrame(text="For how many people?", aggregated_by="sentence"),
        BotStoppedSpeakingFrame(),
        EndFrame(),
    ])
    await PipelineRunner(handle_sigint=False).run(task)
    for e in EVENTS:
        print(json.dumps(e))


asyncio.run(main())
