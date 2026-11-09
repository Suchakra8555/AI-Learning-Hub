---
title: The whole picture, on one page
summary: Every RAG system has the same parts. Learn their names once and the rest of the course gets much easier.
time: 10 min
---

Here is a RAG system from above. Look at it for a minute before reading on.

<figure>
<svg viewBox="0 0 890 300" role="img" aria-labelledby="t1 d1">
  <title id="t1">How a RAG system works</title>
  <desc id="d1">Top row: documents are cleaned, cut into chunks, and stored in a search index. Bottom row: a question is searched against the index, the top chunks go into a prompt, the model writes the answer.</desc>
  <defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="16" y="26" font-size="15" font-weight="700">1. Prepare. Once, and again whenever documents change.</text>
  <g font-size="15" text-anchor="middle">
    <rect class="box" x="16" y="40" width="118" height="56" rx="10"/><text x="75" y="73">Documents</text>
    <rect class="box" x="164" y="40" width="118" height="56" rx="10"/><text x="223" y="73">Clean text</text>
    <rect class="box" x="312" y="40" width="118" height="56" rx="10"/><text x="371" y="73">Chunks</text>
    <rect class="box hot" x="460" y="40" width="118" height="56" rx="10"/><text x="519" y="73">Search index</text>
  </g>
  <path class="arrow" d="M134 68 H160" marker-end="url(#ah)"/>
  <path class="arrow" d="M282 68 H308" marker-end="url(#ah)"/>
  <path class="arrow" d="M430 68 H456" marker-end="url(#ah)"/>
  <text x="600" y="168" font-size="15" font-weight="700">2. Answer. Every time someone asks.</text>
  <g font-size="15" text-anchor="middle">
    <rect class="box" x="16" y="186" width="118" height="56" rx="10"/><text x="75" y="219">Question</text>
    <rect class="box hot" x="164" y="186" width="118" height="56" rx="10"/><text x="223" y="219">Search</text>
    <rect class="box" x="312" y="186" width="118" height="56" rx="10"/><text x="371" y="219">Top chunks</text>
    <rect class="box" x="460" y="186" width="118" height="56" rx="10"/><text x="519" y="219">Prompt</text>
    <rect class="box" x="608" y="186" width="118" height="56" rx="10"/><text x="667" y="219">Model</text>
    <rect class="box" x="756" y="186" width="118" height="56" rx="10"/><text x="815" y="219">Answer</text>
  </g>
  <path class="arrow" d="M134 214 H160" marker-end="url(#ah)"/>
  <path class="arrow" d="M282 214 H308" marker-end="url(#ah)"/>
  <path class="arrow" d="M430 214 H456" marker-end="url(#ah)"/>
  <path class="arrow" d="M578 214 H604" marker-end="url(#ah)"/>
  <path class="arrow" d="M726 214 H752" marker-end="url(#ah)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M519 96 C519 140 223 140 223 182" marker-end="url(#ah)"/>
  <text x="371" y="262" font-size="13" class="small" text-anchor="middle">The search looks inside the index you built in step 1.</text>
</svg>
<figcaption>The two halves of RAG. The top half runs ahead of time. The bottom half runs for every question.</figcaption>
</figure>

## The parts, in plain words

**Documents.** Whatever you want answers from: PDFs, web pages, tickets, wiki pages, spreadsheets. They arrive messy.

**Clean text.** Computers cannot search a PDF's page layout. You pull out the text and remove junk like page numbers, menus, and repeated footers. ([Lesson 4](lesson:rag/reading-documents))

**Chunks.** A chunk is one piece of a document, a few sentences to a few paragraphs long. You search over chunks, not whole documents, because a model can only read so much at once and a small relevant piece beats a big one with a needle in it. ([Lesson 5](lesson:rag/chunking))

**Search index.** The place chunks are stored so they can be found fast. It can be as simple as a Python list, or a dedicated database. Many indexes store each chunk as a list of numbers called an **embedding**, which captures what the chunk is about. ([Lesson 6](lesson:rag/embeddings-and-vectors))

**Search (retrieval).** Given a question, return the few chunks most likely to hold the answer. This is the part that decides whether your system is good. ([Lesson 7](lesson:rag/retrieval-that-works))

**Prompt.** The message you send to the model. It holds the instructions, the chunks, and the question. ([Lesson 8](lesson:rag/prompt-and-citations))

**Model.** The language model, such as Claude. It reads the prompt and writes the answer.

**Answer.** Ideally short, correct, and pointing to the sources it used.

## Where problems hide

When an answer is wrong, one of these went wrong. In order of how often:

1. **Right text was never in the system.** The document was missing, or the text came out garbled.
2. **Right text was cut badly.** The answer was split across two chunks, or a chunk lost its context.
3. **Search missed it.** The right chunk existed but did not make the top results.
4. **The prompt let the model wander.** The chunk was there, and the model ignored it or invented extras.
5. **The model made a plain mistake.** The least common cause by a wide margin.

Most people jump straight to number 5 and try a bigger model. Look at 1 to 3 first. [Lesson 10](lesson:rag/when-answers-go-wrong) turns this list into a debugging routine.

:::tip
Keep this page open as a map. Every later lesson names which box on the diagram it improves.
:::

:::check If an answer is wrong, why look at the retrieved chunks before changing the model?
Because most wrong answers come from the model never being shown the right text. If the right chunk is not in the prompt, no model can answer correctly.
:::
