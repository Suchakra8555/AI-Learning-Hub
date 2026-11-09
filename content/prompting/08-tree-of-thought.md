---
title: Tree of thought: explore, score, back up
summary: For problems where the first step decides everything, let the model try several branches and drop the dead ones.
time: 12 min
---

Some problems punish an early wrong turn. In a puzzle, a bad first move can make the rest impossible. Chain of thought commits to one path. If step one is wrong, every later step is wasted.

**Tree of thought** (ToT) lets the model try several first steps, judge them, and keep only the promising ones.

## The three moves

1. **Propose.** From the current state, ask the model for a few possible next steps. Each step is a "thought", and each one becomes a branch.
2. **Evaluate.** Ask the model to rate each branch, for instance "sure, maybe, impossible". Or score it 1 to 10.
3. **Continue or back up.** Expand the best branches. If all of a branch's children look bad, go back and try a sibling.

```text
Goal: use 4, 9, 10, 13 once each to make 24.

Level 1 proposals:
  13 - 9 = 4   -> state: 4, 4, 10   -> rate: maybe
  10 - 4 = 6   -> state: 6, 9, 13   -> rate: maybe
  4 + 9 = 13   -> state: 13, 10, 13 -> rate: sure
Keep the best. Expand them again. Drop any rated impossible.
```

This is the Game of 24 task from the paper. Yao and co-authors report that GPT-4 with chain of thought solved 4% of Game of 24 tasks, and ToT solved 74%. Read the [abstract](https://arxiv.org/abs/2305.10601). Those numbers are for that paper's setup, not a promise for your task.

## It is a program around the model

ToT is not one prompt. It is a loop in your code that calls the model many times: one call to propose, one to rate each branch, and a search routine that decides what to expand. The model does the thinking, and your code does the bookkeeping.

## When to use it

- Puzzles and planning, where early choices matter.
- Writing with a hard constraint, where you want to try several outlines first.
- Problems you can score partway through.

Do not use it for simple questions. The cost is far higher than chain of thought.

## Compare

| Technique | Paths | Cost | Use when |
|---|---|---|---|
| Chain of thought | one | low | steps are enough |
| [Self-consistency](lesson:prompting/self-consistency) | several, independent, then vote | medium | answers are short and comparable |
| Tree of thought | several, scored, pruned | high | you can judge partial progress |

## Limits

- **Many calls.** Branching multiplies model calls fast. Cap breadth and depth.
- **Bad ratings.** If the model scores branches poorly, it prunes good ones.
- **Redundant branches.** Without care, the model proposes near-copies of the same idea.

:::say
Try several next steps, rate them, and give up on the bad ones early.
:::

:::check What is the main difference between self-consistency and tree of thought?
Self-consistency runs full chains independently and votes at the end. Tree of thought scores partial paths along the way and prunes or backs up.
:::

## Sources

Based on GeeksforGeeks, [Tree of Thought prompting](https://www.geeksforgeeks.org/artificial-intelligence/tree-of-thought-tot-prompting/), which loaded fine. Paper: Yao et al., [Tree of Thoughts: Deliberate Problem Solving with Large Language Models](https://arxiv.org/abs/2305.10601) (2023), abstract read and confirmed.
