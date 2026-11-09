---
title: Where the milliseconds go
summary: In a conversation, delay is the product. Measure each step on its own, then decide what to fix.
time: 20 min
---

On a phone call, a one-second pause feels long. After the caller stops talking, the agent must do four things before any sound comes out:

1. Decide the caller has finished speaking.
2. Finish the transcript.
3. Wait for the model's first words.
4. Wait for the first bit of audio.

The delays add up. A **latency budget** is a plan for how many milliseconds each step may use. You cannot plan without measuring, and the total hides which step is slow.

## What the sources say about numbers

- Vapi's docs claim "sub-600ms response times with natural turn-taking". That is a product claim, not a way to measure.
- LiveKit's pages we read give no latency numbers.
- Some papers and blogs give per-step ranges. We saw those only in search summaries, not the papers, so this course does not repeat them. Look up a source and read its method before you trust a number.

## Measure it yourself

`code/voice/latency_timer.py` times each stage of a turn and reports the median and the worst case over 20 runs. The three stages are **simulated** with random sleeps, so you can run it with no keys:

```bash
cd code/voice
python latency_timer.py
```

```text
stage   median ms  worst ms
stt           223       286
llm           530       697
tts           143       195
total         903      1077
```

These numbers come from the fake sleeps, not from any real service. Do not quote them. What carries over is the method: put a timer around each step, repeat many times, and look at both the median and the worst case. A caller remembers the slow turns.

To use it on a real system, replace the bodies of the three functions with real calls.

## Fixing the slowest step

Look at the biggest row first. Often it is the model. Then you can use a smaller model, send a shorter prompt, or cut the reply length. The ideas from the [fast, cheap, and safe](lesson:rag/fast-cheap-safe) lesson apply here too.

:::try
Make the LLM sleep 1.5 seconds. Which row changes? Now keep the LLM fast but make `tts` slow. Notice that the total hides which one you changed. That is why you time every step.
:::

:::check Why report the worst case and not only the median?
Callers notice the slow turns. A good median can hide a bad experience on one call in ten.
:::
