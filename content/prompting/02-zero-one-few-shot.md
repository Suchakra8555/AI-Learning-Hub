---
title: Zero-, one- and few-shot prompting
summary: How many examples to put in a prompt, and how to tell when one more example is worth the tokens.
time: 12 min
---

You ask a model to label customer messages and the labels come back in five different styles. You could write a longer description. Or you could show it what you want.

The word "shot" means an example. The only question is how many you include.

## Zero-shot: no examples

You describe the task and nothing else.

```text
Label this review as positive, negative or neutral.
Review: "The battery lasts two days, but the screen scratches easily."
```

This works for common tasks like translation, summaries and sentiment, because the model has seen plenty of them in training. It costs the fewest tokens. It struggles when your format or rules are unusual, because the model has to guess them.

## One-shot: a single example

You add one worked case.

```text
Label each review as positive, negative or neutral.

Review: "Arrived broken and support never replied."
Label: negative

Review: "The battery lasts two days, but the screen scratches easily."
Label:
```

One example fixes the format. It cannot show edge cases. If the model's answer looks like your example in a way you did not intend (say, it always answers "negative"), the single example is leaking too much.

## Few-shot: a handful of examples

You add three to six, covering the cases that matter. Include at least one awkward case.

```text
Review: "Arrived broken and support never replied."  -> negative
Review: "Does what it says."                          -> neutral
Review: "Love it, would buy again."                   -> positive
Review: "Great screen, terrible battery."             -> neutral
Review: "The battery lasts two days, but the screen scratches easily." ->
```

The fourth example tells the model that mixed reviews are neutral. No description of that rule was needed.

The tip on picking examples is in [prompts that work](lesson:foundations/prompts-that-work#show-examples). This lesson adds the trade-offs.

## Choosing

| | Zero-shot | One-shot | Few-shot |
|---|---|---|---|
| Tokens | fewest | few | most |
| Fixes output format | sometimes | yes | yes |
| Covers edge cases | no | no | partly |
| Start here when | the task is common | format is the only problem | rules are unusual |

Start at zero. Move up only when a real failure shows you need to.

## What can go wrong

- **Biased examples.** If four of your five examples are "positive", the model leans positive.
- **Copying.** The model may repeat surface features of your examples, such as length or wording.
- **Order.** Changing the order of examples can change the answer. Test it.
- **Complex tasks.** Examples help with format and pattern. They do not make a hard reasoning task easy. The next lesson covers that.

:::try
Take ten real inputs from your own work. Run them zero-shot, then few-shot with three examples. Count how many outputs have the format you wanted. I did not run this for you, so the numbers are yours to find.
:::

:::say
Show the model the answer you want, and add examples only until the failures stop.
:::

:::check Your one-shot prompt keeps returning the same label as the example. What do you do?
Add two or three more examples with different labels, so the model sees a pattern and not a single answer to copy.
:::

## Sources

Based on GeeksforGeeks pages on [zero-shot](https://www.geeksforgeeks.org/nlp/zero-shot-prompting/), [one-shot](https://www.geeksforgeeks.org/artificial-intelligence/one-shot-prompting/) and [few-shot](https://www.geeksforgeeks.org/artificial-intelligence/few-shot-prompting/) prompting. All three loaded fine. The review examples are written for this course.
