---
title: Judging answers as well as search
summary: Search can find the right chunk and the answer can still be wrong. The standard checks for answers, a runnable faithfulness check, and the tools that score them for you.
time: 18 min
---

The [measure quality](lesson:rag/measure-quality) lesson scored search: did the right chunk come back? That number says nothing about what the model did with it. It can find the right chunk and then:

- add a detail that is in no chunk (a **hallucination**),
- answer a different question from the one asked,
- ignore the chunk and answer from memory.

You need checks on the answer too.

## The four standard checks

Most tools use some version of these four. Two look at the answer, two look at what search returned.

| Check | Question it asks | Catches |
|---|---|---|
| **Faithfulness** (also called **groundedness**) | Is every claim in the answer backed by the retrieved chunks? | Made-up details |
| **Answer relevance** | Does the answer address the question that was asked? | Correct but off-topic answers |
| **Context precision** | Of the chunks we retrieved, how many were useful? | Noisy search that wastes tokens |
| **Context recall** | Did the retrieved chunks hold everything needed to answer? | Search that missed part of the answer |

Faithfulness does not check whether the answer is *true*. It checks whether the answer sticks to the chunks. If the chunks are wrong, a faithful answer is wrong too. Keeping the two checks apart tells you *which* part failed.

## A faithfulness check you can run

`code/rag/answer_check.py` takes two hand-written answers to "How long do I have to return a tent?" One sticks to the documents. One adds a store-credit rule that appears nowhere. For each sentence, it finds the retrieved chunk that shares the most meaning words, and it fails any sentence whose numbers are not in that chunk.

```bash
cd code/rag
python answer_check.py
```

```text
Question: How long do I have to return a tent?
Retrieved:
  [1] Returns and refunds > Return window
  [2] Repair service > Paid repairs
  [3] Returns and refunds > Refund timing

grounded: faithfulness 100%, chunks actually used 1 of 3
  100%  [1]         Tents can be returned within 60 days if they have not been slept in.
   89%  [1]         Most other items must be returned within 30 days of delivery.

invented: faithfulness 50%, chunks actually used 1 of 3
  100%  [1]         Tents can be returned within 60 days if they have not been slept in.
   25%  UNSUPPORTED Used tents can still be returned for 50 percent store credit.
```

Three things to notice:

- The invented sentence was caught, and faithfulness dropped to 50%.
- "Chunks actually used 1 of 3" is a rough context precision. Two of the three chunks were noise. If that holds across many questions, send fewer chunks.
- The same code adds a citation to each supported sentence. That is the after-the-fact citation idea from [the prompts lesson](lesson:rag/prompt-and-citations).

:::warn Word overlap is a toy judge
It fails a correct sentence that paraphrases ("you get 60 days to send a tent back"), and it passes a wrong sentence that reuses the chunk's words in a new order. Real tools ask a model: "Here is a claim and a passage. Does the passage support the claim?" The structure stays the same: split into claims, check each, count.
:::

## Tools that do this for you

All of these use a language model as the judge for most checks. We read their docs; we have not run them on this repo.

| Tool | Main checks | Source |
|---|---|---|
| RAGAS | Faithfulness, answer relevancy, context precision, context recall | [docs](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/) |
| TruLens "RAG triad" | Context relevance, groundedness, answer relevance | [docs](https://www.trulens.org/getting_started/core_concepts/rag_triad/) |
| DeepEval | Answer relevancy, faithfulness, contextual relevancy, precision and recall | [docs](https://deepeval.com/docs/getting-started-rag) |
| ARES | Trains small judge models, then corrects their scores with a few hundred human labels | [paper](https://arxiv.org/abs/2311.09476) |

ARES makes a point the others assume away: a judge model makes mistakes too. Whatever tool you use, check the judge.

## Trusting a model as judge

1. **Label 30 to 50 answers by hand** as good or bad.
2. Run the judge on the same answers.
3. **Count where they disagree.** If the judge disagrees with you on 1 in 5, its scores move by about that much on their own, so a 3-point change means nothing.
4. Fix the judge prompt, or pick a stronger judge model, until it agrees with you most of the time.
5. Re-check now and then, and whenever you change the judge model.

The [Evals track](lesson:evals/judges-and-refining) covers judges, datasets and experiments in depth.

:::check Faithfulness is 100% but the answer is wrong. How is that possible, and where do you look?
The answer stuck to the chunks, but the chunks were wrong or out of date. Look at search and at your documents, not at the prompt.
:::

:::check Context precision is low on most questions. What change does that suggest?
Send fewer chunks, or add a reranker so the few you send are the useful ones. You are paying for tokens the answer never uses.
:::
