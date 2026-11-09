---
title: Role and context
summary: Tell the model who it is speaking as and what situation it is in, and keep both short enough to stay useful.
time: 10 min
---

You ask for an explanation of algebra and get a university-level answer. Your reader is ten. The model did not know that, so it picked a default.

Two small additions fix most of this: a role and some context.

## Role prompting

A **role** is a line that sets the voice and viewpoint.

| Weak | Better |
|---|---|
| "Explain algebra." | "You are a maths tutor for a 10-year-old. Explain algebra with one everyday example. No jargon." |
| "Review this code." | "You are a senior engineer doing a code review. List bugs first, style notes last. Be brief." |

A role works best with a task and a limit attached. "You are a doctor" alone invites long, hedged essays. "You are a triage nurse. Say whether this needs urgent care. One sentence." gives the model a job.

Roles shift tone and word choice. They do not add knowledge the model lacks. A "world expert" role will not make a wrong fact right.

## Context prompting

**Context** is the background the model cannot know: who the reader is, what happened before, what the answer is for.

```text
Summarize "Pride and Prejudice" for a book-club newsletter.
Tone: warm and a little witty.
Cover: the main characters and the central misunderstanding.
Length: 80 words.
```

Four things are in there: the scene, the tone, the focus and the length. Add the ones you care about.

## Balance

- **Too little** and the model guesses.
- **Too much** and the useful lines drown. Long, rambling background can pull the answer off course.
- **Stale or wrong** context is worse than none, because the model trusts it.

A fair test: could a new colleague do the task from your prompt alone? If they would ask two questions, answer those two questions in the prompt.

## Put them together

```text
You are a support agent for a camping store.            <- role
The customer bought a tent 12 days ago and it leaks.    <- context
Policy: tents can be returned within 60 days.           <- context
Write a reply in two short paragraphs. Offer a refund.  <- task and limits
```

## Watch for

- **Stereotypes.** A role like "a typical teenager" brings caricatures with it. Describe the behavior you want instead.
- **Tight roles.** "You only talk about tents" makes the bot refuse a fair question about sleeping bags. Say what to do for off-topic questions.
- **Several roles at once.** Pick one voice per prompt.

:::say
A role sets the voice. Context sets the situation. Both should be short.
:::

:::check Your "world-class lawyer" role prompt still gets a fact wrong. Why?
A role changes tone and framing. It does not add facts. Give the model the source text, or check the answer against one.
:::

## Sources

Based on GeeksforGeeks, [role-based prompting](https://www.geeksforgeeks.org/artificial-intelligence/role-based-prompting/) and [contextual prompting](https://www.geeksforgeeks.org/artificial-intelligence/contextual-prompting/). Both loaded fine. The tent example is written for this course.
