---
title: Self-consistency: ask several times, take the majority
summary: One chain of thought can go wrong. Run it several times and keep the answer most runs agree on.
time: 10 min
---

You use chain of thought on a maths question and get 18. You run it again and get 20. Run it a third time and get 20. Which do you trust?

**Self-consistency** answers that. Sample several reasoning chains for the same question, pull out each final answer, and pick the one that appears most.

## How it works

1. Use a chain-of-thought prompt.
2. Set the **temperature** above zero (for example 0.7) so each run takes a different path. Temperature controls how random the model's word choices are.
3. Run it five to ten times.
4. Extract the final answer from each run.
5. Majority vote.

```text
Run 1 -> 20
Run 2 -> 18
Run 3 -> 20
Run 4 -> 20
Run 5 -> 18
Vote: 20 wins, 3 of 5.
```

The idea is that wrong chains tend to disagree with each other, while right chains tend to land on the same number.

Wang and co-authors proposed this and reported large gains over a single chain on maths and commonsense benchmarks, including +17.9% on GSM8K. See the [abstract](https://arxiv.org/abs/2203.11171).

## A small sketch

This code is a sketch. I did not run it, since it needs an API key, and it is not in the repo.

```python
from collections import Counter
from llm import ask  # code/foundations/llm.py

PROMPT = "{q}\nWork step by step. End with a line 'Answer: <value>'."

def answer_of(text):
    for line in reversed(text.splitlines()):
        if line.startswith("Answer:"):
            return line.removeprefix("Answer:").strip()

def self_consistent(q, n=5):
    votes = [answer_of(ask(PROMPT.format(q=q))) for _ in range(n)]
    votes = [v for v in votes if v]
    return Counter(votes).most_common(1)[0] if votes else None
```

Note that `ask()` in this repo does not set a temperature. For real use you would add one, or the runs may be too alike.

## Costs and limits

- **n times the cost and delay.** Five runs cost about five times as much. Run them in parallel to save time.
- **Needs a short, comparable answer.** A number or a label can be voted on. A free-text essay cannot, at least not directly.
- **Ties and splits.** If votes split evenly, the method gives you no winner. Treat that as a low-confidence signal.
- **Shared mistakes.** If the model is wrong in the same way each time, voting keeps the wrong answer.

Use it when a wrong answer is expensive and a slow answer is fine.

:::say
When one run is unreliable, sample a few and trust the agreement.
:::

:::check Why does self-consistency need a temperature above zero?
At zero the model usually repeats the same chain, so every vote is identical and nothing is gained.
:::

## Sources

Based on GeeksforGeeks, [Self-consistency prompting](https://www.geeksforgeeks.org/artificial-intelligence/self-consistency-prompting/), which loaded fine. Paper: Wang et al., [Self-Consistency Improves Chain of Thought Reasoning in Language Models](https://arxiv.org/abs/2203.11171) (2022), abstract read and confirmed.
