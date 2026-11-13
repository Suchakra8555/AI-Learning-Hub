"""Smallest real Pipecat pipeline: two processors, one frame, a log of every hop.

Install: pip install -r requirements.txt     Run: python frames_hello.py
shortcut: PipelineRunner is deprecated in 1.16 (use WorkerRunner). It still works
and is the shortest way to show the idea; the lesson says so.
"""
import asyncio
import warnings

from loguru import logger

from pipecat.frames.frames import EndFrame, TextFrame
from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.frame_processor import FrameProcessor

warnings.filterwarnings("ignore")
logger.remove()  # silence Pipecat's own debug log so only our lines show


class Upper(FrameProcessor):
    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)  # required: handles Start/Cancel
        if isinstance(frame, TextFrame):
            frame = TextFrame(frame.text.upper())
        await self.push_frame(frame, direction)


class Printer(FrameProcessor):
    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        print("  sink got:", frame)
        await self.push_frame(frame, direction)


class HopLog(BaseObserver):
    async def on_push_frame(self, data: FramePushed):
        print(f"{data.source} -> {data.destination}: {type(data.frame).__name__}")


async def main():
    task = PipelineTask(Pipeline([Upper(), Printer()]), observers=[HopLog()])
    await task.queue_frames([TextFrame("hello"), EndFrame()])
    await PipelineRunner(handle_sigint=False).run(task)


asyncio.run(main())
