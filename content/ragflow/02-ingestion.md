---
title: How RAGFlow reads, cuts and embeds documents
summary: Local OCR and layout models for PDFs, a dozen chunking templates, model-written extras per chunk, and the small engineering tricks that make indexing survive crashes and rate limits.
time: 18 min
---

This lesson follows one file from upload to stored vectors. It matches the first half of the [map](lesson:ragflow/tour).

:::note Source
Read from RAGFlow's Go code at commit [`eabad0c74`](https://github.com/infiniflow/ragflow/tree/eabad0c74c73bfa74e218c1fb751da68c1914833) (15 October 2026). We read the code; we did not run RAGFlow.
:::

## Reading: one parser per file type

A dispatcher picks a parser by file type: PDF, Word, PowerPoint, Excel, CSV, HTML, Markdown, plain text, EPUB, JSON, email, images (described by a vision model), and audio ([`parser_type.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/parser/parser/parser_type.go)). For Office files it sniffs the first bytes, so a `.doc` that is really a `.docx` still opens.

There is no web crawler in the indexing path. An uploaded `.html` file is parsed like any other file.

## PDFs: the five steps, all local

PDFs get the most work. A setting picks the method: `deepdoc` (the default), `plain_text` (text layer only), or a remote service such as MinerU, Docling or PaddleOCR that RAGFlow sends the file to ([`pdf_parser_common.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/parser/parser/pdf_parser_common.go)).

The default `deepdoc` path is the [five-step reader](lesson:rag/reading-documents#how-a-serious-pdf-reader-works) from the RAG track, built with small ONNX models that run on the CPU:

1. **Text layer.** Pull the characters the PDF already has.
2. **OCR or not, per page.** If the text layer is empty or looks like scan noise, OCR the page. A page with no text found is retried at higher zoom, to catch tiny print.
3. **OCR in two steps.** A detector, ported from PaddleOCR's DB model, finds text lines. A recognizer reads each line resized to 48 pixels high, with a 6,625-character dictionary that covers Chinese and English ([`ocr_rec.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/deepdoc/native/ocr_rec.go)).
4. **Layout.** A YOLOv10 object detector labels regions: title, text, figure, caption, table, equation, and more ([`dla.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/deepdoc/native/dla.go)). Those labels drive reading order and heading detection.
5. **Table structure.** Each table region goes to a second model that finds rows, columns, headers and merged cells. The result is written out as an HTML `<table>`.

Extra clean-up steps handle multiple columns, words split by line-end hyphens, and repeated headers, footers and tables of contents. Each is a switch on the parser.

## Cutting: a dozen templates

Each **chunking template** is a ready-made pipeline graph. The default is `general`; the others follow the [document's own shape](lesson:rag/more-ways-to-chunk#cut-by-the-document-s-own-shape) ([templates folder](https://github.com/infiniflow/ragflow/tree/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/ingestion/pipeline/template)):

| Template | How it cuts |
|---|---|
| general | Split on delimiters, then merge pieces up to a token budget (default 512 tokens, overlap 0%) |
| qa | One question and answer per chunk |
| table | One row per chunk, as `- field: value` lines |
| manual | Re-sorts text into true page order first, so two columns don't interleave, then groups by heading |
| paper | Groups text under shallow headings |
| book | Five-level heading tree; each chunk carries all its parent headings |
| laws | Same tree, two levels (chapter, article), without repeating parent text |
| presentation | One slide per chunk |
| one, picture, audio | The whole file is one chunk |
| email | Token-budget splitting of headers and body |

Headings come from, in order: the PDF's own bookmarks, a regex you can set per level, the layout model's "title" regions, and a numbered-list regex as a last resort.

Setting `children_delimiters` turns on [parent and child chunks](lesson:rag/more-ways-to-chunk): each chunk is split again into small children that are searched, and the parent is what the model reads.

We found no chunker that cuts by embedding similarity (semantic chunking), and none that does late chunking.

## Extras per chunk

The Extractor node can have a model write **keywords, questions and a summary** for each chunk, with many chunks processed at once ([`extractor.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/ingestion/component/extractor.go)). For tables and images, the chunker can attach nearby text above and below (`table_context_size`, `image_context_size`). Both ideas are in [contextual chunks](lesson:rag/contextual-chunks#other-things-a-model-can-add-to-a-chunk).

We did not find an Anthropic-style step where a model writes a "where this chunk sits in the document" note before indexing.

## Embedding without paying twice

The Tokenizer node prepares text for keyword search and calls the embedding model ([`tokenizer.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/ingestion/component/tokenizer.go)). Four engineering details are worth copying:

- **A cache per chunk.** Before embedding, it checks a cache (kvrocks, a Redis-compatible store) keyed on the model and the chunk's text. A crashed task that restarts pays only for chunks it hadn't finished. Entries expire after 7 days as a backstop and are removed once the chunks are safely stored ([`chunkcache.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/ingestion/chunkcache/chunkcache.go)).
- **Shrink and retry.** If the provider rejects a batch as too long, it trims and retries. As a last step it sends inputs one by one, so one bad chunk can't fail the whole document.
- **Shared 429 cooldown.** When one worker gets "too many requests", every worker using the same provider, key and model waits together ([`embedder.go`](https://github.com/infiniflow/ragflow/blob/eabad0c74c73bfa74e218c1fb751da68c1914833/internal/ingestion/task/embedder.go)). That is the pattern from [fast, cheap, safe](lesson:rag/fast-cheap-safe#caching-embeddings-while-you-index).
- **The vector field is named after its length.** A 1,024-number vector is stored as `q_1024_vec`. Switch to a 768-number model and new chunks get `q_768_vec`, while search reads the field that matches the current model. That is the [no-downtime model switch](lesson:rag/vectors-at-scale#changing-the-embedding-model).

At question time, the question is embedded with a `Query: true` flag. Providers with [separate query and document modes](lesson:rag/embeddings-and-vectors#rules-you-must-follow) use it to pick query mode.

:::check RAGFlow's embedding cache key includes the chunk's text, not only its ID. Why does that matter?
If a chunk's text changes but its ID stays the same, an ID-only key would serve the old vector. With the text in the key, changed text misses the cache and gets a fresh vector.
:::

:::check The `laws` template does not repeat parent heading text in each chunk, but `book` does. Why might that be?
In a law, the article number is usually enough context, and legal articles can be long, so repeating chapter text wastes space. A book's deep sub-section often makes no sense without its chapter and section titles.
:::
