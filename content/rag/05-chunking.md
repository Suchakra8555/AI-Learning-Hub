---
title: Chunking: cutting text into pieces worth finding
summary: How you cut the text decides what search can find. Learn the trade-offs and a simple method that works.
time: 15 min
stage: 2
---

A **chunk** is one piece of a document that you store and search on its own. Chunking is just the cutting step. It sounds minor. It is one of the biggest levers you have.

## Why we cut at all

You could hand the model every document for every question. Three reasons not to:

1. **Size.** A model can only read so much text at once (its **context window**). Your documents are bigger.
2. **Cost and speed.** You pay for every word you send, and long prompts are slower.
3. **Focus.** A model given 50 pages to find one fact does worse than one given the right three paragraphs.

So you cut, search for the best pieces, and send only those.

## The two ways chunks go wrong

**Too big.** The chunk holds the answer plus a lot of other stuff. Search sees a blurry mix of topics and may not rank it first. You also waste prompt space.

**Too small.** The chunk holds half an idea. "Tents and sleeping bags can be returned within 60 days" gets separated from "if they have not been slept in", and the model gives the wrong answer with full confidence.

A chunk should be about **one idea that makes sense on its own**.

## A starting recipe

Do not agonize. Start here, measure (lesson 9), and adjust:

- Cut along the document's own structure first: headings, then paragraphs.
- Aim for roughly 100 to 300 words per chunk.
- Let neighbors **overlap** a little, around 10 to 20 percent, so an idea that straddles a boundary shows up whole in at least one chunk.
- Put the **title and heading into every chunk**.

That last point matters most, and people forget it.

## Why headings travel with the chunk

Compare these two chunks from the same file.

Stage 1 gave us:

```text
You can return most items within 30 days of delivery. The item must be unused...
```

Stage 2 gives us:

```text
Returns and refunds > Return window
You can return most items within 30 days of delivery. The item must be unused...
```

The second one tells search, and the model, what the text is about. A question about "return window" now matches the heading words too.

## The code

`code/rag/chunking.py` splits each Markdown file on `##` headings, builds a label like `Title > Section`, and splits long sections by word count with overlap.

```python
def chunk_by_headings(doc, max_words=120, overlap_words=20):
    text = doc["text"]
    title_match = re.match(r"#\s+(.*)", text)
    title = title_match.group(1).strip() if title_match else doc["source"]
    sections = re.split(r"\n(?=## )", text)
    chunks = []
    for section in sections:
        lines = section.strip().splitlines()
        if not lines:
            continue
        heading = lines[0].lstrip("# ").strip()
        body = " ".join(l.strip() for l in lines[1:] if l.strip())
        if not body:
            continue
        label = f"{title} > {heading}"
        words = body.split()
        start = 0
        while start < len(words):
            piece = words[start : start + max_words]
            chunks.append({"source": doc["source"], "text": f"{label}\n{' '.join(piece)}"})
            if start + max_words >= len(words):
                break
            start += max_words - overlap_words
    return chunks
```

Run it and look at what comes out:

```bash
cd code/rag
python -c "from common import load_documents; from chunking import chunk_all; [print(c['text'], '\n---') for c in chunk_all(load_documents())[:4]]"
```

:::try
Print five chunks from your own documents. Read each one alone, as if it were all you knew. Could you answer a question from it? If a chunk feels like the middle of a conversation, it is cut wrong.
:::

## Other ways to cut

| Method | How it works | Good for | Watch out |
|---|---|---|---|
| Fixed size | Every N words, no matter what | Quick starts, messy text | Cuts sentences in half |
| By structure | Headings, then paragraphs | Manuals, policies, docs | Needs clean structure |
| By meaning | Start a new chunk when the topic shifts | Long essays and transcripts | Slower, harder to debug |
| Parent and child | Search small chunks, send the bigger section around them | Long sections where context matters | More moving parts |

**Parent and child** is worth knowing. You search small, precise chunks, because small chunks match questions sharply. Then you swap each hit for the larger section it came from, so the model gets full context. Try it once basic chunking is solid.

The [more ways to chunk](lesson:rag/more-ways-to-chunk) lesson runs five of these methods on the same questions and compares them.

## What the numbers say

Chunking advice online is full of magic numbers. Treat all of them as guesses until you test on your own questions. In the next lessons you will build a test set, and then you can try 100 words against 250 words and know which is better.

:::tip
Store the chunk size and overlap you used next to the index. When quality changes later, you will want to know which setting produced it.
:::

:::check What problem does overlap solve?
An idea that falls across a cut. With overlap, at least one chunk holds the idea whole.
:::

:::check Why include the heading in every chunk?
It tells both search and the model what the chunk is about, and it lets a short chunk make sense on its own.
:::
