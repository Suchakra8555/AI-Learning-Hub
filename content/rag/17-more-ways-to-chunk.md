---
title: More ways to chunk, measured side by side
summary: Semantic splits, sentence windows, parent and child chunks, late chunking, and cuts that follow the document's own shape. Five run on the same questions.
time: 20 min
---

The [chunking lesson](lesson:rag/chunking) cut by headings and moved on. This lesson tries the other methods you will read about, on the same 20 questions, so you can see what each one buys.

Every method trades two things. A chunk should hold **one whole idea**, so it makes sense alone. It should also be **small and focused**, so a search for that idea finds it and not its neighbours.

## Five methods

**Fixed size.** Every 40 words, whatever they say. The simplest cut, and the baseline.

**By headings.** What `chunking.py` already does: one section per chunk, with `Title > Section` on top.

**Semantic.** Compare each sentence with the next. If they look alike, keep them together. If similarity drops, the topic probably changed, so cut there. Pinecone's chunking guide describes a smoother version that compares small groups of neighbouring sentences instead of single pairs ([source](https://www.pinecone.io/learn/chunking-strategies/)). Our script compares single pairs. Either way, it needs an embedding for every sentence.

**Sentence window.** Search single sentences, since a single sentence matches a question sharply. When one is found, hand the model that sentence plus one or two neighbours on each side. LlamaIndex ships this as a node parser ([docs](https://developers.llamaindex.ai/python/framework-api-reference/node_parsers/sentence_window/)).

**Parent and child.** The same idea, one size up. Search small "child" pieces, and hand the model the whole "parent" section each one came from ([docs](https://developers.llamaindex.ai/python/framework-api-reference/node_parsers/hierarchical/)).

## Run them

```bash
cd code/rag
python chunk_strategies.py
```

All five use the same BM25 search, so only the cutting changes. Output from our run:

```text
fixed words            top-1  55%   top-3  85%   MRR 0.68
by headings            top-1  75%   top-3  95%   MRR 0.83
semantic               top-1  55%   top-3  80%   MRR 0.66
sentence window        top-1  65%   top-3  90%   MRR 0.76
parent / child         top-1  70%   top-3  95%   MRR 0.82

pieces stored, and words sent to the model per question (top 3):
  fixed words         11 pieces    92 words
  by headings         11 pieces    93 words
  semantic            25 pieces    40 words
  sentence window     29 pieces    82 words
  parent / child      29 pieces    94 words
```

What to take from it:

- **Fixed size lost to headings** by a wide margin, with the same number of pieces. Our documents have clean headings, and cutting by them is free.
- **Semantic did worst.** It made 25 pieces from 29 sentences, so almost every sentence stood alone and lost its context.
- **Parent and child nearly matched headings.** That makes sense: on our files a "parent" is exactly a heading section. The child search adds precision you only see on long sections, and ours are short.

The semantic result depends almost entirely on one number, the similarity cut-off:

```text
semantic: the cut-off decides everything
  threshold 0.10 (12 pc) top-1  75%   top-3  95%   MRR 0.83
  threshold 0.15 (16 pc) top-1  65%   top-3  90%   MRR 0.76
  threshold 0.20 (22 pc) top-1  55%   top-3  80%   MRR 0.67
  threshold 0.25 (25 pc) top-1  55%   top-3  80%   MRR 0.66
```

At 0.10 it rebuilt roughly the heading sections and scored the same. So semantic splitting found the structure the headings already gave us, at the cost of one embedding per sentence. It earns its keep on text with no headings: transcripts, chat logs, long essays.

:::warn Our toy vectors, our tiny files
The semantic run uses the toy character-piece vectors from `retrievers.py`, not a real embedding model. Twenty questions on four short files means one question is 5 points. Trust the shape of the result, then run it on your own documents.
:::

## Late chunking

Normal order: cut first, then embed each chunk alone. The chunk "It grew 3% that quarter" is embedded without knowing what "it" is.

**Late chunking** flips the order. Run the whole document through a long-context embedding model once, then average the per-token outputs for each chunk's span. Each chunk's vector was computed while the model could see the whole document, so "it" carries some of its meaning. Jina AI proposed it ([source](https://jina.ai/news/late-chunking-in-long-context-embedding-models/)). It needs a model that exposes per-token outputs and a document that fits in its window. We did not run it. Our toy vectors have no per-token outputs to pool.

It solves the same problem as [contextual chunks](lesson:rag/contextual-chunks), without a model call per chunk.

## Cut by the document's own shape

Some documents tell you how to cut them. Use that before anything clever:

| Document | Cut | Why |
|---|---|---|
| FAQ | One question and its answer per chunk | The unit people search for |
| Spreadsheet | One row per chunk, written as `field: value` lines | Keeps column names with each value |
| Slides | One slide per chunk | Each slide is already one idea |
| Book or manual | Follow the heading tree, and put all parent headings on each chunk | A deep section stays self-describing |
| Law or contract | Chapter and article | Matches how people cite them |
| Photo, short audio | The whole file is one chunk | Too small to split |

The [RAGFlow case study](lesson:ragflow/ingestion) shows a product that ships each of these as a ready-made template.

:::check Semantic splitting scored worst at one cut-off and tied headings at another. What does that tell you?
The method has a setting that matters a lot, and its best value depends on your text. You have to tune it on a test set. On text with good headings, it may only rebuild what the headings already give you.
:::

:::check What do sentence window and parent and child have in common?
Both search small pieces for precision, then hand the model a bigger piece for context. They differ only in how big the bigger piece is.
:::
