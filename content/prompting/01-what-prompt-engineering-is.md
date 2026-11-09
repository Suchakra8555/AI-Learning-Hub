---
title: What prompt engineering is
summary: Why the same model gives a great answer to one request and a poor one to another, and the habits that close the gap.
time: 10 min
---

You ask a model for "a post about remote work" and get 600 bland words. A colleague asks for the same thing and gets something they can publish. The model is the same. The prompts are not.

**Prompt engineering** means writing and adjusting the instructions you give a model until its answers are reliable. It is closer to writing a clear ticket than to programming.

## What a prompt can hold

A model only sees the text you send. Anything you do not say, it guesses. A prompt can carry five things:

| Part | What it does | Example |
|---|---|---|
| Role | Sets the point of view | "You are a support agent for a camping store." |
| Task | Says what to do | "Write a reply to this email." |
| Instructions | Sets the rules | "Two short paragraphs. No discounts." |
| Context | Gives background | "The customer bought a tent last week." |
| Input | The thing to work on | The customer's email |

You do not need all five every time. Add the ones whose absence causes a wrong answer.

## Weak vs better

| Weak | Better |
|---|---|
| "Write about remote work." | "Write a 200-word blog post on the biggest mistake new remote managers make. Plain tone, for team leads." |
| "Quiz on World War I." | "Write five multiple-choice questions on the causes of World War I for 15-year-olds. Mark the right answer." |

The better prompts name the length, the reader, and the angle. Each one removes a guess.

## The loop

You rarely get a prompt right on the first try. The working method is:

1. Write a plain version.
2. Run it on a few real inputs.
3. Find the failure. Is the answer too long, off-topic, or wrong in format?
4. Change one thing to fix that failure.
5. Run it again on the same inputs.

Step 4 says one thing for a reason. If you change three things, you do not know which one helped. [Prompts that work](lesson:foundations/prompts-that-work) covers this habit in more detail.

## What this track covers

The next eight lessons each add one technique:

- examples in the prompt (zero-, one- and few-shot)
- asking for steps (chain of thought)
- roles and context
- letting the model use tools (ReAct)
- giving it documents to read
- voting over several answers
- exploring branches
- guardrails around the whole thing

:::say
A prompt is a spec. The model guesses whatever the spec leaves out.
:::

:::check You get a vague answer. What do you change first?
The prompt, by adding the missing detail: length, reader, format, or background. Change one thing, then run it again on the same inputs.
:::

## Sources

Based on GeeksforGeeks, [What is prompt engineering](https://www.geeksforgeeks.org/artificial-intelligence/what-is-an-ai-prompt-engineering/). The page loaded fine. The examples above are written for this course.
