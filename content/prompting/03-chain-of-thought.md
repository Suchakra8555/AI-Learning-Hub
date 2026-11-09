---
title: Chain of thought: asking for the steps
summary: Models often get multi-step problems wrong when they jump to the answer. Asking for the steps first fixes many of those.
time: 12 min
---

You ask a model "39 times 21?" and it answers 809. It was close and wrong. A person would not do this in their head either. They would split it up.

**Chain of thought** (CoT) means getting the model to write its intermediate steps before the final answer. The steps become part of the text the model reads as it continues, so each step has something to build on.

## Same question, two prompts

| Prompt | Likely reply |
|---|---|
| "What is 39 x 21? Answer with just the number." | A number, sometimes wrong. |
| "What is 39 x 21? Work it out step by step, then give the answer on a last line starting with 'Answer:'." | 30 x 21 = 630. 9 x 21 = 189. 630 + 189 = 819. Answer: 819 |

The second prompt does two things. It asks for steps. It also fixes where the answer goes, so your code can read it.

## Two ways to ask

1. **Say it.** Add "think step by step" or "work it out before answering".
2. **Show it.** Put a worked example in the prompt, with the steps written out. This is [few-shot](lesson:prompting/zero-one-few-shot) prompting where each example includes its reasoning.

The original paper used the second way. Wei and co-authors reported that a few examples with written steps lifted a very large model past earlier results on a grade-school maths benchmark, and that the effect appeared mainly in big models. Check the [abstract](https://arxiv.org/abs/2201.11903) for the exact claims.

## When it helps

- Maths and word problems.
- Logic puzzles.
- Decisions with several conditions ("refund if under 30 days and unused, unless...").
- Anything where a person would use scratch paper.

It does little for lookups ("capital of France?") or style tasks. There it only adds cost.

## Costs and limits

- **More tokens.** Steps are output tokens. You pay for them and wait for them.
- **Steps can be wrong.** A tidy chain can still reach a wrong answer. The written steps look convincing either way.
- **Steps are not always the real reason.** Treat them as working text, not a faithful log of how the model decided.
- **Some models reason on their own.** Newer reasoning models do this internally, and an extra "step by step" may add little. Test on your model.

## Keep the answer easy to find

If you parse the reply, ask for a marker.

```text
Think through the problem first. Then write the final answer on its own line
in the form:  Answer: <value>
```

Then take the text after the last `Answer:`.

:::say
Let the model write its scratch work before it commits to an answer.
:::

:::check CoT made your answers slower and no more accurate on a simple lookup task. Why?
The task needs no multi-step reasoning. The extra steps only add tokens and delay.
:::

## Sources

Based on GeeksforGeeks, [What is chain-of-thought prompting](https://www.geeksforgeeks.org/artificial-intelligence/what-is-chain-of-thought-prompting/). The page loaded. Paper: Wei et al., [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903) (2022), abstract read and confirmed.
