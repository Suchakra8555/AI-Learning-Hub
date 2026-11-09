---
title: What RAG is, and why companies keep building it
summary: A language model knows a lot, but it does not know your documents. RAG is the simple trick that fixes that.
time: 8 min
---

You ask a chatbot, "How many days do I have to return a tent to Northwind Outfitters?" It has never seen Northwind's return policy. It will either say it does not know, or it will make something up in a confident voice. The second one is the dangerous one.

RAG fixes this. The name stands for **retrieval-augmented generation**. That is a long name for a short idea:

:::say
Before the model answers, look up the relevant pieces of your own documents and put them in front of it.
:::

That is all of it. Three steps:

1. **Retrieve.** Search your documents for the pieces that look related to the question.
2. **Augment.** Paste those pieces into the message you send to the model, next to the question.
3. **Generate.** The model writes the answer using what you pasted.

If you have ever copied a paragraph from a wiki into a chat window and then asked a question about it, you have done RAG by hand. A RAG system does the copying for you, for every question, in a fraction of a second.

The name comes from a 2020 research paper by Lewis and others at Facebook AI ([paper](https://arxiv.org/abs/2005.11401)). They paired a language model with a searchable index of Wikipedia and let the model read what the search found before it wrote. Today the word covers any system that looks things up first and answers second.

## Why not just train the model on our documents?

People ask this first. Here is the plain comparison.

| | RAG | Training the model on your data |
|---|---|---|
| Documents change on Monday | Update the search index. Done by lunch. | Train again. Days or weeks, and real money. |
| Can it show where an answer came from | Yes. You know which pieces you pasted. | No. The knowledge is mixed into the model. |
| Can you remove a document | Delete it from the index. | Very hard. |
| Different people should see different documents | Filter the search by who is asking. | Not practical. |
| Teaches the model a new *style* or skill | No. | Yes. This is what training is good at. |

For "answer questions using our documents", RAG is almost always the right first choice. Training is for changing how a model behaves, not for handing it facts.

## Why not paste every document into the prompt?

Newer models can read a lot of text in one request. If all your documents fit, why search at all? Sometimes you shouldn't. For a handful of short files, pasting them all works. It stops working as the pile grows:

- **Cost and speed.** You pay for every word the model reads, on every question. Sending 500 pages to answer "do you ship to Canada?" is slow and expensive.
- **Lost in the middle.** A 2023 study found models use facts at the start and end of a long prompt better than facts buried in the middle ([paper](https://arxiv.org/abs/2307.03172)). More text in the prompt can mean worse use of the one line that matters.
- **It still has a ceiling.** The company wiki will outgrow any context window.

The tools combine. RAG finds the few pages that matter, and a long context window lets you send more of them than the classic top 5. The [LLMOps track](lesson:llmops/prompt-rag-or-fine-tune) compares prompting, RAG and fine-tuning in more detail.

## What RAG is good at

- Support bots that answer from a help center or policy pages.
- Internal search over wikis, tickets, and contracts, with answers instead of a list of links.
- Questions over long documents nobody wants to read, such as manuals.

## What RAG is not good at

- Questions that need adding up many rows of a table. ("What was our total revenue last year?") Use a database query for that.
- Questions where the answer is spread across hundreds of pages and no single piece holds it.
- Anything where a wrong answer is worse than no answer, unless you add checks. Lessons 8 to 10 cover those checks.

:::warn A common trap
A RAG demo is easy. A RAG system people can rely on is hard. The demo works on the five questions you tried. The system has to work on the five hundred you did not think of. This course is about that gap.
:::

## What you will build

You will build one small project all the way up: a support bot for a made-up outdoor store called Northwind. The documents are four short policy files in `code/rag/data`. They are small on purpose, so you can read all of them and know exactly what the right answer is. That makes it easy to see when the system is wrong.

You will run the same bot through seven levels of improvement:

1. A script of about 50 lines.
2. Better reading and cutting of text.
3. Better search.
4. Better prompts.
5. Measuring quality.
6. Cost, speed, and safety.
7. A real service with monitoring.

:::check In your own words: what does the "retrieval" part of RAG do?
It searches your own documents for the pieces most related to the question, so those pieces can be shown to the model along with the question. The model never has to know your documents ahead of time.
:::

:::check Your return policy changes next week. Which approach copes better, and why?
RAG. You edit the document and update the search index. A model trained on the old policy would need training again.
:::
