---
title: When answers go wrong: a debugging routine
summary: A five-step routine that finds the cause of a bad answer in minutes, in the order problems usually happen.
time: 15 min
---

Someone sends you a screenshot of a bad answer. What now?

Do not start by editing the prompt. Work down this routine. It goes from the most common cause to the least.

## Step 0: capture the evidence

You cannot debug what you did not save. For each answer, you need to be able to see:

- the question as the user typed it,
- the chunks that were retrieved, in order, with their sources,
- the exact prompt sent to the model,
- the model's answer,
- the model name and settings, and which version of the index.

This is why production systems log every request (lesson 13). In the course code, `stage2_better_retrieval.py` prints the retrieved chunks so you can look at them.

## Step 1: is the fact in the documents at all?

Open the source files and search for the fact yourself.

- **Not there.** Then it is a content gap, not a RAG bug. The right behavior is "I don't have that information". Check that the bot said that.
- **There, but in a file you did not index.** Add the file.
- **There, but extraction garbled it.** Go back to [reading documents](lesson:rag/reading-documents).

## Step 2: did the chunk exist and read well?

Find the chunk that should have answered. Read it alone.

- Is the answer split across two chunks?
- Is the chunk missing its heading, so it makes no sense out of context?
- Is it too large, with the answer buried in other topics?

Fix with [chunking](lesson:rag/chunking): adjust size, overlap, headings.

## Step 3: did search bring it back?

Run the question through search only. Where does the right chunk rank?

| Where it ranked | What it means | What to try |
|---|---|---|
| Not in the top 20 | Search cannot see it | Different words in the question? Add keyword search. Better chunk text. Rewrite the query. |
| In the top 20, not the top 4 | Search sees it but ranks it low | Hybrid search, then a reranker. |
| In the top 4 | Search worked | Go to step 4. |

## Step 4: did the prompt let the model wander?

The right chunk was in the prompt and the answer was still wrong. Compare the answer to the chunk.

- **Ignored the chunk.** The prompt is too loose. Strengthen "use ONLY the notes".
- **Added things not in the chunk.** Ask for citations and check them.
- **Mixed up two chunks.** Chunks conflict or are too similar. Clean the sources.
- **Too many chunks.** More text is not always better. Models can lose details in the middle of a long prompt. Try fewer.

## Step 5: only then, the model

If the chunk was right, the prompt was tight, and the answer is still wrong, you may have a genuine model limit. Options:

- Try a stronger model on the failing cases.
- Break a complex question into smaller steps.
- Add a check step that verifies the answer against the notes.

Most teams reach this step far less often than they expect.

## Keep a failure log

Every time you debug one of these, add the question to your eval set ([lesson 9](lesson:rag/measure-quality)) with the right answer. The set then grows from real use, and the same mistake cannot come back unnoticed.

A useful log entry has four lines:

```text
Question:   "Will I owe customs fees if I order from Toronto?"
Cause:      Search. Document says "import duties"; keyword search found no match.
Fix:        Added vector search and hybrid merge.
Test added: yes (eval_questions.json #14)
```

:::tip
Write the cause in one word from the routine: content, reading, chunking, search, prompt, or model. After a month, count them. The biggest bucket tells you where to invest.
:::

:::try
Pick any question from `eval_questions.json`. Run it through `python stage2_better_retrieval.py "your question" --method overlap` and then `--method vector`. Where does the answer chunk rank in each? Which step of this routine did you just do?
:::

:::check The right chunk was retrieved, yet the model gave a wrong number. Which step is next?
Step 4: the prompt. Compare the answer with the chunk, check whether the model ignored it or added to it, and tighten the instructions or add citation checks.
:::

:::check Why save the exact prompt for each answer?
You can only judge whether the model misused the notes if you can see exactly which notes and instructions it had.
:::
