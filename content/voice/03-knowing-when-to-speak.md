---
title: Knowing when to speak
summary: The agent has to guess when you have finished, and stop when you cut in. Learn the settings that control both.
time: 15 min
---

A person pausing to think is not the same as a person who has finished. If the agent jumps in too early, it talks over the caller. If it waits too long, it feels slow. This guess is called **turn detection**.

## The tools

- **Voice activity detection (VAD).** A small model that says "someone is speaking" or "silence". A simple setup waits for a pause of a set length. LiveKit bundles Silero VAD for this.
- **A turn-detector model.** Reads the words and the sound to predict whether the sentence is done. "I'd like to book a table for..." is clearly not finished, even after a pause.
- **Endpointing.** The delay between speech stopping and the system deciding the turn ended.

LiveKit's docs list these modes: a turn detector model (the default), server-side detection by a realtime model, VAD only, STT endpointing, and manual control. Per the page, VAD only has the lowest delay, since it just waits for silence ([source](https://docs.livekit.io/agents/build/turns/)).

## Interruptions

When the caller talks over the agent, the agent should stop. It should also remember only the part the caller actually heard. LiveKit describes two interruption modes: `adaptive`, which tries to tell a real interruption from "mm-hmm", and `vad`. It also has a `false_interruption_timeout`, listed as 2.0 seconds in Python, for resuming after a noise that was not a real interruption. Defaults can change, so check the page for your version.

## Trade-offs to remember

| Setting | If too fast | If too slow |
|---|---|---|
| Endpointing delay | Cuts people off mid-thought | Feels laggy |
| Interruption sensitivity | Stops for coughs | Talks over the caller |

There is no right value. Tune with real recordings, and measure with the [timer from the last lesson](lesson:voice/where-the-milliseconds-go).

:::note What we did not test
We did not run Silero VAD or any LiveKit code here. For a hands-on exercise, follow the Silero repository's own README on a short recording with pauses, and print when it says speech started and stopped.
:::

:::check A caller says "I need to change my... um... booking". The agent replies after "my". What setting do you adjust?
The endpointing delay, or use a turn-detector model that reads meaning, so a mid-sentence pause is not treated as the end of the turn.
:::
