---
title: Measure quality before you tune anything
summary: Build a small test set and a few numbers, so each change is a fact and not a feeling.
time: 20 min
stage: 5
---

Here is a common story. Someone changes the prompt, tries three questions, and says "much better". Next week a customer finds five new problems. Nobody knows when they started.

The fix is an **evaluation set**, often called an **eval set**: a list of questions where you already know the right answer. You run it after every change, the same way a programmer runs unit tests.

## Build the set

Start with 20 to 50 questions. That is enough to start and small enough to write by hand in an afternoon.

For each question, record:

- the **question**, in real users' words,
- the **document or fact** that holds the answer,
- (optionally) the **expected answer**.

Look at `code/rag/eval_questions.json`:

```json
{"question": "Will I owe customs fees if I order from Toronto?",
 "source": "shipping.md",
 "must_contain": "import duties"}
```

`must_contain` is a phrase that has to appear in the retrieved chunk. It is a cheap, automatic way to ask: "Did search find the chunk with the answer?"

### Where good questions come from

1. **Real questions.** Support tickets, chat logs, search logs. This beats anything you invent.
2. **Questions written by the document owners.** "What would people get wrong?"
3. **Awkward phrasings.** Typos, short questions, wrong terms, two questions in one.
4. **Questions with no answer.** The bot should decline. Include some on purpose.
5. **Questions that were failures before.** Every bug becomes a permanent test.

:::warn
Do not write all the questions yourself while reading the documents. You will use the documents' own words and make search look better than it is. Borrow other people's phrasing.
:::

## Two things to measure, separately

A RAG system can fail in two places. Measure them apart, or you will not know where to look.

**1. Did search find the right text? (retrieval)**

| Number | Question it answers |
|---|---|
| top-k hit rate | Was the right chunk anywhere in the top k? |
| top-1 | Was it ranked first? |
| MRR | On average, how high was it? (1.0 is perfect.) |

This is what `stage3_eval.py` prints, with no model and no cost. It runs in a blink.

Our test set has one right chunk per question, so these three numbers are enough. When a question has several right chunks, you will see three more numbers:

- **Precision@k**: of the k chunks returned, how many were right.
- **Recall@k**: of all the right chunks, how many made it into the top k.
- **NDCG**: like MRR, but it can credit several right chunks and give "very relevant" more points than "a bit relevant".

**2. Given the right text, was the answer good? (generation)**

| Check | How |
|---|---|
| Correct | Does it state the fact in the reference? |
| Grounded | Does every claim appear in the notes? |
| Cited properly | Do the note numbers exist and match? |
| Declines when it should | On no-answer questions, does it say so? |

Checking these by reading is slow. Teams often use another model as a judge. [Judging answers](lesson:rag/judging-answers) covers the standard answer checks and the tools that run them, and the [Evals track](lesson:evals/why-test-an-agent) goes further. For now, do it by hand for 20 answers once. It is the best education you will get.

## Run it

```bash
cd code/rag
python stage3_eval.py
```

The output on this repo:

```text
20 questions, top 3 chunks each

stage 1 (overlap)      top-1  70%   top-3  90%   MRR 0.78
overlap + new chunks   top-1  60%   top-3  95%   MRR 0.76
bm25                   top-1  75%   top-3  95%   MRR 0.83
vector (toy)           top-1  85%   top-3  95%   MRR 0.90
hybrid                 top-1  75%   top-3 100%   MRR 0.85

Questions bm25 missed:
  - Will I owe customs fees if I order from Toronto?
```

The last block is the most useful part. It lists the failures. Every number is a reason to look at a failing question, and a failing question is where improvement starts.

## How to use the numbers

- **Change one thing, then run.** Chunk size, a prompt line, a new search method. One at a time.
- **Keep a log.** A text file with the date, the change, and the numbers. It becomes the history of your system.
- **Look at the failures, not just the average.** Read each missed question and ask why.
- **Do not chase the last point.** With 20 questions, one question is 5 points. Small changes are noise. Grow the set before you trust small differences.
- **Guard against fooling yourself.** If you tune until your 20 questions pass, you may only have taught the system those 20. Keep a few questions aside that you never tune on.

:::tip
Put the eval in your CI (the automatic checks that run when you push code). If hit rate drops below a line you set, the build fails. Now nobody can break search by accident.
:::

## When quality is not one number

"Overall 90 percent" can hide that every question about warranty fails. Tag questions by topic or type and report each group. Averages hide the pockets where users get hurt.

:::try
Add five new questions to `eval_questions.json` that you think will be hard. Use words that do not appear in the documents. Run the eval. Which methods fail? What would fix it?
:::

:::check Why measure retrieval and the final answer as separate things?
If the answer is wrong you need to know whether search missed the right text or the model misused it. They have different fixes.
:::

:::check Your hit rate went from 90% to 95% on 20 questions. Should you celebrate?
Not yet. That is one more question out of twenty. Grow the set and look at which question changed before deciding the change helped.
:::
