---
title: A RAG script in about 50 lines
summary: Build the whole idea with nothing but Python. No database, no framework, no vectors yet.
time: 20 min
stage: 1
---

A **POC** (proof of concept) is a quick build that answers one question: can this work at all? Ours answers, "Can a script answer questions from four policy files?"

You need Python 3.9 or newer. Nothing to install.

## Get the code

The code lives in `code/rag/`. Open a terminal there:

```bash
cd code/rag
python stage1_poc.py "How long do I have to return a tent?"
```

You will see three chunks it found, then a prompt. If you set an API key, you will see a real answer instead (more on that below).

## What the script does

It has three small jobs. Here they are one at a time.

### Job 1: cut the documents into pieces

The simplest cut is one piece per paragraph.

```python
def split_into_paragraphs(docs):
    pieces = []
    for doc in docs:
        for para in doc["text"].split("\n\n"):
            if para.strip():
                pieces.append({"source": doc["source"], "text": para.strip()})
    return pieces
```

Each piece remembers which file it came from. You will want that later for sources.

### Job 2: find the pieces that match the question

We count how many meaningful words the question and the piece share. Meaningful means we skip words like "the", "is", and "do".

```python
def retrieve(question, pieces, k=3):
    q_words = set(content_words(question))
    scored = []
    for p in pieces:
        overlap = len(q_words & set(content_words(p["text"])))
        scored.append((overlap, p))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [p for score, p in scored[:k] if score > 0]
```

`k=3` means "give me the best three". This crude word counting is called **keyword search**. It has real weaknesses, and you will see them soon.

### Job 3: build the prompt and ask

```python
def build_prompt(question, chunks):
    context = "\n\n".join(f"[{i + 1}] (source: {c['source']})\n{c['text']}" for i, c in enumerate(chunks))
    return (
        "You answer questions for a store's customers using ONLY the notes below.\n"
        "If the notes do not contain the answer, say: \"I don't have that information.\"\n"
        "After each fact, add the note number in square brackets, like [1].\n\n"
        f"NOTES:\n{context}\n\n"
        f"QUESTION: {question}\n"
        "ANSWER:"
    )
```

Read that prompt slowly. It is the heart of RAG. It tells the model three things: use only these notes, admit when the notes do not help, and show which note each fact came from.

## Run it with a real model

Without a key, the script prints the prompt, so you can see exactly what a model would receive. To get an actual answer, set a key for Anthropic's API:

```bash
# macOS / Linux
export ANTHROPIC_API_KEY="your-key-here"

# Windows PowerShell
$env:ANTHROPIC_API_KEY = "your-key-here"
```

Then run the script again. The helper in `common.py` sends the prompt over plain HTTP, so there is still nothing to install.

:::warn Keep keys out of code
Never paste a key into a file you might share. Use environment variables, as above. A leaked key can be used by strangers on your bill.
:::

## Now try to break it

A POC is only useful if you learn where it fails. Try these questions and look at which pieces come back:

```bash
python stage1_poc.py "Can I send back a fuel canister?"
python stage1_poc.py "Will I owe customs fees if I order from Toronto?"
python stage1_poc.py "What is the cheapest delivery option?"
```

:::try
For each question, ask yourself: did the right paragraph make the top three? If not, which word was missing from the question that was in the document?
:::

You will find things like this:

- The word "Toronto" appears in no document, and the document says "Canada" and "import duties", not "customs fees". Keyword search only sees shared words. It has no idea these mean the same thing.
- A paragraph about repairs can outrank the right paragraph about returns because both mention "tent".
- Paragraphs lose their headings. The text "You can return most items within 30 days" does not say it is about a return window unless the heading came with it.

These are not bugs in your code. They are the gaps the rest of the course closes, one by one.

## What you have, and what you do not

You have a working loop: question in, relevant text found, answer out. That is a POC, and it is already useful for a demo.

You do not have: good document reading, smart cutting, meaning-based search, a way to measure quality, protection against wrong answers, speed, or a service anyone else can call.

:::say
A POC proves the idea. Production proves the idea survives bad input, scale, and time.
:::

:::check Why does the prompt tell the model to say "I don't have that information"?
Without that instruction, a model tends to fill gaps with a plausible guess. Giving it a safe way out reduces made-up answers.
:::

:::check The question says "customs fees" and the document says "import duties". What happens with keyword search, and why?
It finds no shared words, so the right paragraph scores low or zero. Keyword search matches spelling, not meaning.
:::
