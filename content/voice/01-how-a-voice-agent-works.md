---
title: How a voice agent works
summary: Three steps, speech to text, a language model, text to speech, joined by streaming. Know the parts before you tune any of them.
time: 15 min
---

A voice agent hears you, thinks, and talks back. Under the hood it is a chain of three programs.

1. **Speech to text (STT).** Turns the caller's audio into words.
2. **The language model (LLM).** Reads those words and writes a reply.
3. **Text to speech (TTS).** Turns the reply back into audio.

This is called a **cascaded pipeline**, because each step feeds the next. Each step can be swapped for another provider. Vapi's docs describe the same three parts and let you pick each one ([source](https://docs.vapi.ai/quickstart/introduction)). LiveKit's Agents framework names the same pipeline as its core ([source](https://docs.livekit.io/agents/)).

## Streaming is what makes it feel live

If each step waited for the one before to finish completely, the caller would sit in silence. Instead, each step passes small pieces along as soon as it has them: the STT sends partial words, the LLM sends its first few words, and the TTS starts speaking before the sentence is finished.

## Two ways to build it

| Way | What you do | Trade-off |
|---|---|---|
| Hosted platform (for example Vapi) | Choose a transcriber, a model, and a voice. The platform runs the rest and the phone line. | Fast to start, less control |
| Build on a framework (for example LiveKit Agents) | Run an agent program that joins a call as a participant. You own each choice. | More work, more control |

We read both vendors' intro pages only. We did not compare cost or control, so this table is a general shape, not a measured result.

:::say
A voice agent is three programs in a row, kept fast by streaming. Most of your tuning work is about the gaps between them.
:::

:::check Why does the TTS start speaking before the model has finished writing?
Waiting for the full reply would add silence. Streaming lets the caller hear the start while the rest is still being written.
:::
