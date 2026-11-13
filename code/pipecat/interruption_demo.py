"""Why an interruption is a SystemFrame: it jumps the queue and drops pending data.

A slow processor (0.3 s per word) is "speaking" five words. At 0.75 s we push an
InterruptionFrame, like a caller talking over the bot.

Run: python interruption_demo.py
"""
import asyncio
import time
import warnings

from loguru import logger

from pipecat.frames.frames import (
    ControlFrame, EndFrame, InterruptionFrame, SystemFrame, TextFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.frame_processor import FrameProcessor

warnings.filterwarnings("ignore")
logger.remove()
T0 = time.monotonic()


def kind(f):
    return "system" if isinstance(f, SystemFrame) else "control" if isinstance(f, ControlFrame) else "data"


class SlowSpeaker(FrameProcessor):
    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, TextFrame):
            await asyncio.sleep(0.3)  # pretend each word takes 0.3 s to say
        await self.push_frame(frame, direction)


class Sink(FrameProcessor):
    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        print(f"{time.monotonic() - T0:5.2f}s  {kind(frame):7} {frame}")
        await self.push_frame(frame, direction)


async def main():
    task = PipelineTask(Pipeline([SlowSpeaker(), Sink()]))

    async def feed():
        await task.queue_frames([TextFrame(f"word{i}") for i in range(5)])
        await asyncio.sleep(0.75)
        await task.queue_frame(InterruptionFrame())  # the caller talks over the bot
        await asyncio.sleep(0.2)
        await task.queue_frames([TextFrame("after"), EndFrame()])

    await asyncio.gather(PipelineRunner(handle_sigint=False).run(task), feed())


asyncio.run(main())
