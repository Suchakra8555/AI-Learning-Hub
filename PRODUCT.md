# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static site, no framework. Markdown lessons plus a small zero-dependency Node build script. Chosen by the user. Output is plain HTML, CSS and JS that opens from a folder or any static host.

## Users

Engineers at a company (the author's peers) who know how to code but are new to building AI systems. They work through lessons at their desk, with a terminal open next to the page, and copy code to run it. Some are brand new to AI words; the content must not assume jargon. (Inferred from the brief.)

## Product Purpose

A learning guide that takes an engineer from a working RAG proof of concept to a production system, in plain human language. It then grows into a wider AI engineering course (agents, harness engineering, evals, shipping). Success: a peer finishes a lesson, runs the code, and can explain the idea to someone else.

## Positioning

Plain-language first. Every lesson pairs a short explanation with code that runs, and walks the POC-to-production ladder in the order real projects hit problems. RAG and Harness Engineering are two separate tracks. The Harness track teaches the ideas using DeepSeek Harness as a worked example; it does not build on top of it.

## Operating Context

Peers clone the repo, run `npm run dev`, read lessons in the browser, and run Python from `code/` in a terminal. Contributors write lessons in Markdown under `content/`.

## Capabilities and Constraints

- Lessons are Markdown files with simple frontmatter; the build script turns them into pages.
- Progress is stored in the browser (localStorage), no accounts.
- Search works offline (index embedded as a script).
- Code samples: stage 1 to 3 run with only the Python standard library; later stages list their extra installs.
- DeepSeek Harness is a developer preview with breaking changes expected. Lessons must say so and cite the official repo, not guess at details.
- Writing rules live in CONTRIBUTING.md (plain words, no jargon without a one-line explanation, humanizer pass before merging).
- Undecided: hosting target, whether a quiz/exercise checker is added later.

## Brand Commitments

Voice: plain, direct, friendly. Short sentences. Explain a term the first time it appears. Final text goes through the humanizer skill.

## Evidence on Hand

No testimonials, benchmarks, or usage numbers exist. Do not invent any. External fact bases: the DeepSeek Harness repo (github.com/deepseek-ai/deepseek-harness), and the RAGFlow repo (github.com/infiniflow/ragflow) at commit eabad0c74, read for the case-study track, and Dograh (github.com/dograh-hq/dograh, commit 5dfa84c18) with its Pipecat fork (github.com/dograh-hq/pipecat, commit 9ac08e90b), read for the Pipecat and Dograh track. Other outside facts are linked in the lessons.

## Product Principles

1. Say it the way you would say it to a coworker at their desk.
2. Show the smallest thing that works, then show what breaks, then fix it.
3. Every term is explained once, in one line, where it first shows up.
4. Facts about outside tools come from their own docs, with a link.
5. The course map can grow (RAG to agents to harness) without redesigning the site.

## Accessibility & Inclusion

Readable on a phone and a laptop. Contrast at least 4.5:1 for text. Full keyboard use. Light and dark themes. Plain language also serves readers whose first language is not English.
