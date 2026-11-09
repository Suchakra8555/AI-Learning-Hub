---
title: What a language model does
summary: A model reads text and guesses the next piece of text, over and over. Everything else in this course builds on that one fact.
time: 10 min
---

A **language model** is a program that takes text in and gives text back. Under the hood it does one small thing: given the text so far, it guesses what comes next. It adds that guess to the text and guesses again. A whole answer is many small guesses chained together.

Think of your phone's keyboard suggesting the next word. A language model is the same idea, trained on far more text and able to look at far more context.

## What that means in practice

| Fact | What it means for you |
|---|---|
| It guesses, it does not look things up | It can sound sure and be wrong. This is called a **hallucination**. |
| It only knows its training text | It has never seen your company's documents. RAG exists to fix this. |
| It forgets everything between calls | Each call starts from nothing. You send the history every time. |
| The same question can give different answers | A setting called **temperature** controls how much it varies. Low is steady. High is creative. |

## Three words you will see everywhere

- **Prompt**: the text you send in. Instructions, examples, and your question all go in the prompt.
- **Completion** (or response): the text that comes back.
- **Context window**: how much text the model can read in one call. [The next lesson](lesson:foundations/tokens-and-context) covers it.

:::say
A model is a text guesser with no memory and no access to your data. Your job as an engineer is to put the right text in front of it, and to check what comes out.
:::

:::check Why does a model sometimes state something false with full confidence?
It is guessing the most likely next text, not checking facts. Likely-sounding and true are different things.
:::
